# File: src/llm_chat_node/llm_chat_node/__init__.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import requests
import json
from .utils import build_full_prompt, trim_history, call_ollama_with_retry
import time
import traceback
import uuid


class LLMChatNode(Node):
    def __init__(self):
        super().__init__('llm_chat_node')

        # === 模型参数 ===
        self.declare_parameter('model', 'gemma4:e2b')
        self.declare_parameter('ollama_url', 'http://localhost:11434')
        self.declare_parameter('max_tokens', 2048)
        self.declare_parameter('temperature', 0.7)
        self.declare_parameter('timeout', 300)

        # === 视觉参数 ===
        self.declare_parameter('enable_vision', True)
        self.declare_parameter('vision_auto_context', True)
        self.declare_parameter('vision_context_prompt',
            '[Visual Context]\nThe camera currently sees:\n{detection_text}\n'
            'Please incorporate this visual information into your response '
            'if relevant to the user\'s question.'
        )

        # === 对话历史参数 ===
        self.declare_parameter('enable_history', True)
        self.declare_parameter('history_window', 10)  # 保留最近 N 轮对话
        self.declare_parameter('history_max_tokens', 4096)

        # === 错误处理参数 ===
        self.declare_parameter('max_retries', 3)
        self.declare_parameter('retry_base_delay', 1.0)  # 指数退避基数（秒）

        # === 系统提示词参数 ===
        self.declare_parameter('system_prompt', '')
        self.declare_parameter('system_prompt_file', '')

        # === 流式输出参数 ===
        self.declare_parameter('stream_output', True)

        # === 输入校验与限流 ===
        self.declare_parameter('min_input_length', 1)
        self.declare_parameter('max_input_length', 2000)
        self.declare_parameter('request_cooldown_seconds', 0.5)
        self.declare_parameter('requests_per_minute', 60)

        # === 响应裁剪 ===
        self.declare_parameter('max_response_chars', 20000)

        # === 读取参数 ===
        self.model = self.get_parameter('model').get_parameter_value().string_value
        self.ollama_url = self.get_parameter('ollama_url').get_parameter_value().string_value
        self.max_tokens = self.get_parameter('max_tokens').get_parameter_value().integer_value
        self.temperature = self.get_parameter('temperature').get_parameter_value().double_value
        self.timeout = self.get_parameter('timeout').get_parameter_value().integer_value

        self.enable_vision = self.get_parameter('enable_vision').value
        self.vision_auto_context = self.get_parameter('vision_auto_context').value
        self.latest_detection_text = "No visual information available."

        self.enable_history = self.get_parameter('enable_history').value
        self.history_window = self.get_parameter('history_window').value
        self.history_max_tokens = self.get_parameter('history_max_tokens').value

        self.max_retries = self.get_parameter('max_retries').value
        self.retry_base_delay = self.get_parameter('retry_base_delay').value

        self.stream_output = self.get_parameter('stream_output').value

        self.min_input_length = self.get_parameter('min_input_length').value
        self.max_input_length = self.get_parameter('max_input_length').value
        self.request_cooldown_seconds = self.get_parameter('request_cooldown_seconds').value
        self.max_response_chars = self.get_parameter('max_response_chars').value
        self.requests_per_minute = int(self.get_parameter('requests_per_minute').value)

        # per-client sliding window timestamps (client_id -> list of timestamps)
        self._client_requests = {}

        # 上次请求时间（用于简单限流）
        self._last_request_time = 0.0

        # === 加载系统提示词 ===
        self.system_prompt = self._load_system_prompt()

        # === 对话历史缓存 ===
        self.conversation_history = []

        # === ROS 接口 ===
        # 输入/输出话题
        self.sub = self.create_subscription(
            String, 'chat_input', self.handle_input, 10
        )
        self.pub = self.create_publisher(String, 'chat_output', 10)

        # 流式输出话题
        if self.stream_output:
            self.stream_pub = self.create_publisher(String, '/chat_output/stream', 10)

        # 对话历史话题
        self.history_pub = self.create_publisher(String, '/chat/history', 10)

        # 视觉检测订阅
        if self.enable_vision:
            self.vision_sub = self.create_subscription(
                String,
                '/vision/detection_text',
                self.vision_callback,
                10
            )
            self.get_logger().info('Vision integration enabled')

        self.get_logger().info(
            f'LLM chat node ready. Model: {self.model}, '
            f'History: {self.enable_history}, '
            f'Stream: {self.stream_output}'
        )

    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        system_prompt = self.get_parameter('system_prompt').value
        system_prompt_file = self.get_parameter('system_prompt_file').value

        if not system_prompt and system_prompt_file:
            try:
                with open(system_prompt_file, 'r') as f:
                    system_prompt = f.read().strip()
                self.get_logger().info(f'Loaded system prompt from file: {system_prompt_file}')
            except Exception as e:
                self.get_logger().error(f'Failed to load system prompt file: {e}')

        if system_prompt:
            self.get_logger().info('Custom system prompt configured')
            return system_prompt
        else:
            return (
                "You are a helpful AI assistant with vision capabilities. "
                "You can see the camera feed and answer questions about what you see. "
                "Be concise, friendly, and informative."
            )

    def vision_callback(self, msg: String):
        """接收视觉检测结果并缓存"""
        self.latest_detection_text = msg.data
        self.get_logger().debug(f'Vision context updated: {msg.data[:50]}...')

    def _build_history_context(self) -> str:
        """构建历史上下文文本"""
        if not self.conversation_history:
            return ""

        lines = ["Previous conversation:"]
        for turn in self.conversation_history[-self.history_window * 2:]:
            prefix = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {turn['content']}")
        return "\n".join(lines)

    def _trim_history(self):
        """裁剪历史到最大轮次"""
        while len(self.conversation_history) > self.history_window * 2:
            self.conversation_history.pop(0)
        self.conversation_history = trim_history(self.conversation_history, self.history_window)

    def _call_ollama_with_retry(self, payload: dict) -> dict:
        """Wrapper to call utility retry implementation and log errors."""
        try:
            return call_ollama_with_retry(
                self.ollama_url,
                payload,
                max_retries=self.max_retries,
                retry_base_delay=self.retry_base_delay,
                timeout=self.timeout,
            )
        except Exception as e:
            self.get_logger().error(f'Ollama call failed: {e}')
            raise

    def _call_ollama_stream(self, payload: dict) -> str:
        """流式调用 Ollama，逐 token 发布到 /chat_output/stream"""
        full_response = ""
        try:
            resp = requests.post(
                f'{self.ollama_url}/api/generate',
                json={**payload, 'stream': True},
                stream=True,
                timeout=(5, self.timeout)
            )
            resp.raise_for_status()

            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            full_response += chunk['response']
                            # 发布每个 token
                            stream_msg = String()
                            stream_msg.data = chunk['response']
                            self.stream_pub.publish(stream_msg)
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue

            return full_response
        except Exception as e:
            self.get_logger().error(f'Ollama stream request failed: {e}')
            raise

    def handle_input(self, msg: String):
        raw = msg.data
        self.get_logger().info(f'Received prompt: {raw}')

        # 支持 JSON 消息格式: {"client_id": "id", "text": "..."}
        client_id = 'anonymous'
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and 'text' in parsed:
                prompt = str(parsed.get('text', '')).strip()
                client_id = str(parsed.get('client_id', 'anonymous'))
            else:
                prompt = str(raw).strip()
        except Exception:
            prompt = str(raw).strip()

        # === 输入最小/最大长度校验 ===
        if not isinstance(prompt, str) or len(prompt.strip()) < self.min_input_length:
            reply = String()
            reply.data = 'Error: input too short.'
            self.pub.publish(reply)
            return
        if len(prompt) > self.max_input_length:
            reply = String()
            reply.data = f'Error: input too long (max {self.max_input_length} chars).'
            self.pub.publish(reply)
            return

        # === 简单限流：全局单实例冷却 ===
        now = time.time()
        if now - self._last_request_time < float(self.request_cooldown_seconds):
            reply = String()
            reply.data = 'Error: requests are too frequent; please slow down.'
            self.pub.publish(reply)
            return
        self._last_request_time = now

        # === per-client 滑动窗口限流 ===
        window = 60.0
        timestamps = self._client_requests.get(client_id, [])
        # remove old
        timestamps = [t for t in timestamps if now - t < window]
        if len(timestamps) >= self.requests_per_minute:
            reply = String()
            reply.data = 'Error: client rate limit exceeded.'
            self.pub.publish(reply)
            return
        timestamps.append(now)
        self._client_requests[client_id] = timestamps

        # === 构建完整 prompt ===
        parts = []

        # 1. 系统提示词
        parts.append(self.system_prompt)

        # 2. 视觉上下文
        if self.enable_vision and self.vision_auto_context:
            context_template = self.get_parameter('vision_context_prompt').value
            vision_context = context_template.format(
                detection_text=self.latest_detection_text
            )
            parts.append(vision_context)

        # 3. 对话历史
        if self.enable_history and self.conversation_history:
            history_text = self._build_history_context()
            parts.append(history_text)

        # 4. 当前用户问题
        parts.append(f"User: {prompt}")
        parts.append("Assistant:")

        full_prompt = "\n\n".join(parts)

        try:
            self.get_logger().info('Sending request to Ollama...')

            request_id = uuid.uuid4().hex[:8]
            self.get_logger().debug(f'Outgoing Ollama request id={request_id} model={self.model}')

            payload = {
                'model': self.model,
                'prompt': full_prompt,
                'stream': False,
                'options': {
                    'num_predict': self.max_tokens,
                    'temperature': self.temperature,
                }
            }

            if self.stream_output:
                # 流式输出
                response_text = self._call_ollama_stream(payload)
            else:
                # 非流式输出
                result = self._call_ollama_with_retry(payload)
                response_text = result.get('response', '')
                if response_text is None:
                    response_text = ''
                response_text = response_text.strip()

            # === 响应分页：若回复过长则拆分为多个部分发布，每部分长度不超过 max_response_chars ===
            max_chars = int(self.max_response_chars)
            if len(response_text) > max_chars and max_chars > 0:
                # split into chunks
                chunks = [response_text[i:i+max_chars] for i in range(0, len(response_text), max_chars)]
                total = len(chunks)
                for idx, chunk in enumerate(chunks, start=1):
                    page_msg = String()
                    page_msg.data = f'[Page {idx}/{total}]\n' + chunk
                    self.pub.publish(page_msg)
                self.get_logger().info(f'Published response in {total} pages')
            else:
                # 发布完整回复
                reply = String()
                reply.data = response_text
                self.pub.publish(reply)
                self.get_logger().info(f'Published reply ({len(reply.data)} chars)')

            # === 保存到对话历史 ===
            if self.enable_history:
                self.conversation_history.append({"role": "user", "content": prompt, "client_id": client_id})
                self.conversation_history.append({"role": "assistant", "content": response_text})
                self._trim_history()

                # 发布对话历史（最近 10 条）
                history_msg = String()
                history_msg.data = json.dumps(self.conversation_history[-10:])
                self.history_pub.publish(history_msg)

        except Exception as e:
            self.get_logger().error(f'Ollama request failed: {e}')
            self.get_logger().error(traceback.format_exc())
            reply = String()
            reply.data = f'Error: {str(e)}'
            self.pub.publish(reply)


def main(args=None):
    rclpy.init(args=args)
    node = LLMChatNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
