import { useCallback, useRef } from 'react';
import { useAppStore, generateMessageId } from '../store';

/**
 * 聊天交互 Hook
 * 通过 rosbridge 发布消息到 /chat_input，订阅 /chat_output 获取 AI 回复
 */
export function useChat() {
  const {
    messages,
    addMessage,
    isProcessing,
    setProcessing,
    isCameraOn,
    detections,
    modelName,
    rosConnection,
  } = useAppStore();

  // 超时定时器引用
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * 发送消息
   * @param content 消息内容
   * @param publishFn rosbridge 发布函数（由 App.tsx 传入）
   */
  const sendMessage = useCallback(
    async (content: string, publishFn?: (topic: string, type: string, msg: any) => void) => {
      if (!content.trim() || isProcessing) return;

      // 添加用户消息
      const userMsg = {
        id: generateMessageId(),
        role: 'user' as const,
        content: content.trim(),
        timestamp: Date.now(),
      };
      addMessage(userMsg);
      setProcessing(true);

      // 通过 rosbridge 发布到 /chat_input
      if (publishFn && rosConnection === 'connected') {
        publishFn('/chat_input', 'std_msgs/String', { data: content.trim() });
        console.log(`[Chat] Sent message to /chat_input: "${content.trim()}"`);

        // 设置超时提示：30 秒后如果仍未收到回复，提示用户检查后端
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        timeoutRef.current = setTimeout(() => {
          // 检查是否还在处理中（即仍未收到回复）
          const state = useAppStore.getState();
          if (state.isProcessing) {
            const timeoutMsg = {
              id: generateMessageId(),
              role: 'system' as const,
              content: '⏱️ AI 回复超时。请确认 ROS2 后端 LLM 聊天节点是否已启动：\n\n```bash\nros2 launch llm_chat_node llm_chat_launch.py\n```\n\n或启动完整视觉版：\n```bash\nros2 launch llm_chat_node vision_chat_launch.py detector_type:=yolo\n```',
              timestamp: Date.now(),
            };
            state.addMessage(timeoutMsg);
            state.setProcessing(false);
          }
        }, 30000);
      } else if (!publishFn || rosConnection !== 'connected') {
        // 降级：如果没有 publishFn 或 ROS Bridge 未连接，使用提示消息
        const reason = rosConnection !== 'connected'
          ? 'ROS Bridge 未连接'
          : '发布函数不可用';
        console.warn(`[Chat] ${reason}, cannot send message to ROS2 backend`);
        setTimeout(() => {
          const assistantMsg = {
            id: generateMessageId(),
            role: 'assistant' as const,
            content: `⚠️ ${reason}，无法获取 AI 回复。\n\n请确保以下服务已启动：\n\n1️⃣ **rosbridge_server**（WebSocket 桥梁）：\n\`\`\`bash\nros2 run rosbridge_server rosbridge_websocket\n\`\`\`\n\n2️⃣ **ROS2 LLM 聊天节点**（AI 后端）：\n\`\`\`bash\ncd ~/Desktop/ros-chat\nsource install/setup.bash\nsource ~/Desktop/llama-env/bin/activate\nros2 launch llm_chat_node llm_chat_launch.py\n\`\`\``,
            timestamp: Date.now(),
          };
          addMessage(assistantMsg);
          setProcessing(false);
        }, 1000);
      }
    },
    [messages, addMessage, isProcessing, setProcessing, isCameraOn, detections, modelName, rosConnection]
  );

  return {
    messages,
    sendMessage,
    isProcessing,
  };
}
