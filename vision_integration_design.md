# ROS2 视觉识别模块集成设计方案

## 1. 概述

本文档旨在为 `ros-chat` 项目（基于 ROS2 和 Ollama 的 LLM 聊天系统）集成视觉识别模块，使其能够通过摄像头实时捕捉画面，精准识别物体，并将识别结果融入 AI 对话中。

### 1.1 设计目标

- **实时物体检测**：通过摄像头实时捕捉画面，检测并识别画面中的物体
- **多模型支持**：支持 YOLO（本地 GPU 加速）和 Ollama 多模态模型（如 LLaVA）两种识别方案
- **ROS2 原生集成**：识别结果通过 ROS2 话题发布，与现有 LLM 聊天节点无缝对接
- **可扩展架构**：支持多种视觉模型切换，便于后续扩展（如人脸识别、OCR 等）
- **低延迟**：优化推理流程，确保实时性

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ros-chat 系统架构                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    /camera/image_raw    ┌──────────────────┐      │
│  │  摄像头节点    │ ──────────────────────→ │  视觉识别节点      │      │
│  │ (USB摄像头)    │    (sensor_msgs/Image)  │  vision_node      │      │
│  └──────────────┘                          └────────┬─────────┘      │
│                                                      │               │
│                                                      │               │
│                                         /vision/detection             │
│                                         (vision_msgs/Detection2DArray)│
│                                                      │               │
│                                                      ▼               │
│  ┌──────────────┐    /chat_input    ┌──────────────────┐             │
│  │  用户输入      │ ───────────────→ │  LLM 聊天节点     │             │
│  │  (topic pub)   │  (std_msgs/String)│  llm_chat_node   │             │
│  └──────────────┘                    └────────┬─────────┘             │
│                                                │                     │
│                                                ▼                     │
│                                     ┌──────────────────┐             │
│                                     │   Ollama API      │             │
│                                     │  (gemma4 / LLaVA) │             │
│                                     └──────────────────┘             │
│                                                │                     │
│                                                ▼                     │
│  ┌──────────────┐    /chat_output   ┌──────────────────┐             │
│  │  用户接收      │ ←─────────────── │  LLM 聊天节点     │             │
│  │  (topic echo)  │  (std_msgs/String)│                  │             │
│  └──────────────┘                    └──────────────────┘             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 节点通信拓扑

| 话题名称 | 消息类型 | 发布者 | 订阅者 | 说明 |
|---------|---------|--------|--------|------|
| `/camera/image_raw` | `sensor_msgs/Image` | 摄像头驱动 | 视觉识别节点 | 原始图像帧 |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | 摄像头驱动 | 视觉识别节点 | 相机参数 |
| `/vision/detection` | `vision_msgs/Detection2DArray` | 视觉识别节点 | LLM 聊天节点 | 检测结果（含标签、置信度、边界框） |
| `/vision/detection_text` | `std_msgs/String` | 视觉识别节点 | LLM 聊天节点 | 检测结果的文本描述（供 LLM 使用） |
| `/chat_input` | `std_msgs/String` | 用户/其他节点 | LLM 聊天节点 | 用户输入（已有） |
| `/chat_output` | `std_msgs/String` | LLM 聊天节点 | 用户 | AI 回复（已有） |

---

## 3. 视觉识别方案

### 3.1 方案一：YOLOv8/v11 本地推理（推荐）

#### 3.1.1 技术选型

| 组件 | 选择 | 说明 |
|------|------|------|
| 检测模型 | YOLOv8n / YOLOv11n | 轻量级，适合实时检测 |
| 推理框架 | ONNX Runtime / OpenCV DNN | 跨平台，GPU 加速 |
| 预处理 | OpenCV | 图像缩放、归一化 |
| 后处理 | NMS（非极大值抑制） | 去除重复检测框 |

#### 3.1.2 性能指标

| 模型 | 输入尺寸 | 推理时间 (GPU) | 推理时间 (CPU) | mAP@0.5 |
|------|---------|---------------|---------------|---------|
| YOLOv8n | 640×640 | ~5ms | ~30ms | 37.3% |
| YOLOv8s | 640×640 | ~8ms | ~45ms | 44.9% |
| YOLOv11n | 640×640 | ~4ms | ~25ms | 39.5% |

#### 3.1.3 支持的物体类别（COCO 数据集，80 类）

涵盖常见物体：人、车辆、动物、日常用品、电子设备、食物等。

### 3.2 方案二：Ollama 多模态模型（LLaVA / Gemma3 Vision）

#### 3.2.1 技术选型

| 组件 | 选择 | 说明 |
|------|------|------|
| 模型 | LLaVA / Gemma3-Vision | 多模态大模型，支持图文理解 |
| 推理 | Ollama API | 复用现有 Ollama 基础设施 |
| 图像编码 | Base64 | 通过 API 传输图像数据 |

#### 3.2.2 适用场景

- **复杂场景理解**：需要理解图像上下文（如"桌子上有什么？"）
- **OCR 文字识别**：识别图像中的文字
- **属性识别**：识别物体的颜色、材质等属性
- **无需 GPU 加速**：如果已有 Ollama 服务运行在 GPU 上

### 3.3 方案对比

| 特性 | YOLO 本地推理 | Ollama 多模态 |
|------|-------------|--------------|
| 推理速度 | ⚡ 极快（毫秒级） | 🐢 较慢（秒级） |
| 识别精度 | ✅ 标准物体检测 | ✅ 深度场景理解 |
| GPU 需求 | 可选（CPU 也可用） | 推荐 GPU |
| 模型大小 | ~6MB (YOLOv8n) | ~4-7GB (LLaVA) |
| 部署复杂度 | 低 | 中 |
| 扩展性 | 需重新训练 | 零样本学习 |
| 最佳场景 | 实时物体检测 | 复杂视觉问答 |

---

## 4. 详细实现设计

### 4.1 视觉识别节点（vision_node）

#### 4.1.1 节点类设计

```python
# File: src/llm_chat_node/llm_chat_node/vision_node.py

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from cv_bridge import CvBridge
import cv2
import numpy as np

class VisionNode(Node):
    """
    视觉识别节点
    - 订阅摄像头图像话题
    - 运行 YOLO 或 Ollama 多模态模型进行物体检测
    - 发布检测结果到 /vision/detection 和 /vision/detection_text
    """

    def __init__(self):
        super().__init__('vision_node')

        # === 参数声明 ===
        self.declare_parameter('detector_type', 'yolo')       # 'yolo' | 'ollama'
        self.declare_parameter('yolo_model_path', '')         # YOLO 模型路径
        self.declare_parameter('yolo_confidence', 0.5)        # 置信度阈值
        self.declare_parameter('yolo_nms_threshold', 0.45)    # NMS 阈值
        self.declare_parameter('ollama_model', 'llava')       # Ollama 多模态模型
        self.declare_parameter('ollama_url', 'http://localhost:11434')
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('detection_interval', 1.0)     # 检测间隔（秒）
        self.declare_parameter('enable_auto_trigger', True)   # 自动触发检测
        self.declare_parameter('trigger_topic', '/vision/trigger')  # 手动触发话题

        # === 初始化 ===
        self.bridge = CvBridge()
        self.detector_type = self.get_parameter('detector_type').value
        self.latest_image = None

        # === 初始化检测器 ===
        if self.detector_type == 'yolo':
            self._init_yolo_detector()
        elif self.detector_type == 'ollama':
            self._init_ollama_detector()

        # === ROS 接口 ===
        # 订阅摄像头图像
        self.image_sub = self.create_subscription(
            Image,
            self.get_parameter('image_topic').value,
            self.image_callback,
            10
        )

        # 发布检测结果（结构化）
        self.detection_pub = self.create_publisher(
            Detection2DArray,
            '/vision/detection',
            10
        )

        # 发布检测结果（文本描述）
        self.detection_text_pub = self.create_publisher(
            String,
            '/vision/detection_text',
            10
        )

        # 手动触发检测话题
        self.trigger_sub = self.create_subscription(
            String,
            self.get_parameter('trigger_topic').value,
            self.trigger_callback,
            10
        )

        # 定时器：定期检测
        if self.get_parameter('enable_auto_trigger').value:
            self.timer = self.create_timer(
                self.get_parameter('detection_interval').value,
                self.timer_callback
            )

        self.get_logger().info(
            f'Vision node ready. Detector: {self.detector_type}'
        )

    def _init_yolo_detector(self):
        """初始化 YOLO 检测器"""
        model_path = self.get_parameter('yolo_model_path').value
        if not model_path:
            model_path = self._get_default_yolo_model()
        self.net = cv2.dnn.readNetFromONNX(model_path)
        # 启用 GPU 加速（如果可用）
        try:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            self.get_logger().info('YOLO: CUDA acceleration enabled')
        except:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.get_logger().info('YOLO: Using CPU backend')

        # COCO 类别名称（80 类）
        self.classes = self._load_coco_classes()

    def _init_ollama_detector(self):
        """初始化 Ollama 多模态检测器"""
        self.ollama_model = self.get_parameter('ollama_model').value
        self.ollama_url = self.get_parameter('ollama_url').value
        self.get_logger().info(f'Ollama detector: {self.ollama_model}')

    def image_callback(self, msg: Image):
        """图像回调：缓存最新帧"""
        self.latest_image = msg

    def trigger_callback(self, msg: String):
        """手动触发检测"""
        self.get_logger().info(f'Manual detection triggered: {msg.data}')
        self._run_detection()

    def timer_callback(self):
        """定时检测"""
        if self.latest_image is not None:
            self._run_detection()

    def _run_detection(self):
        """执行检测"""
        if self.latest_image is None:
            return

        cv_image = self.bridge.imgmsg_to_cv2(self.latest_image, 'bgr8')

        if self.detector_type == 'yolo':
            detections = self._detect_yolo(cv_image)
        elif self.detector_type == 'ollama':
            detections = self._detect_ollama(cv_image)
        else:
            return

        # 发布结构化检测结果
        detection_msg = self._build_detection_msg(detections)
        self.detection_pub.publish(detection_msg)

        # 发布文本描述
        text_msg = self._build_detection_text(detections)
        self.detection_text_pub.publish(text_msg)

        self.get_logger().info(
            f'Published {len(detections)} detections'
        )

    def _detect_yolo(self, image: np.ndarray) -> list:
        """YOLO 推理"""
        # 预处理
        blob = cv2.dnn.blobFromImage(
            image, 1/255.0, (640, 640),
            swapRB=True, crop=False
        )
        self.net.setInput(blob)

        # 推理
        outputs = self.net.forward()[0]

        # 后处理
        confidence_threshold = self.get_parameter('yolo_confidence').value
        nms_threshold = self.get_parameter('yolo_nms_threshold').value

        boxes, scores, class_ids = [], [], []
        rows = outputs.shape[0]

        for i in range(rows):
            classes_scores = outputs[i][4:]
            max_score = classes_scores.max()
            if max_score >= confidence_threshold:
                class_id = classes_scores.argmax()
                x, y, w, h = outputs[i][:4]
                # 转换为像素坐标
                h_img, w_img = image.shape[:2]
                x1 = int((x - w/2) * w_img)
                y1 = int((y - h/2) * h_img)
                x2 = int((x + w/2) * w_img)
                y2 = int((y + h/2) * h_img)
                boxes.append([x1, y1, x2 - x1, y2 - y1])
                scores.append(float(max_score))
                class_ids.append(int(class_id))

        # NMS
        indices = cv2.dnn.NMSBoxes(boxes, scores, confidence_threshold, nms_threshold)

        results = []
        if len(indices) > 0:
            for i in indices.flatten():
                results.append({
                    'class_id': class_ids[i],
                    'class_name': self.classes[class_ids[i]],
                    'confidence': scores[i],
                    'bbox': boxes[i],  # [x, y, w, h]
                })

        return results

    def _detect_ollama(self, image: np.ndarray) -> list:
        """Ollama 多模态检测"""
        import requests
        import base64

        # 图像编码为 Base64
        _, buffer = cv2.imencode('.jpg', image,
                                 [cv2.IMWRITE_JPEG_QUALITY, 85])
        image_b64 = base64.b64encode(buffer).decode('utf-8')

        # 调用 Ollama API
        prompt = (
            "Please describe all objects you see in this image. "
            "For each object, provide: object name, approximate position "
            "(e.g., center-left, top-right), and confidence level. "
            "Format as a list."
        )

        try:
            resp = requests.post(
                f'{self.ollama_url}/api/generate',
                json={
                    'model': self.ollama_model,
                    'prompt': prompt,
                    'images': [image_b64],
                    'stream': False,
                    'options': {'num_predict': 512}
                },
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            text = result.get('response', '')

            # 解析文本为结构化数据（简化处理）
            return [{
                'class_name': text,
                'confidence': 1.0,
                'bbox': [0, 0, 0, 0],  # Ollama 不提供精确边界框
            }]
        except Exception as e:
            self.get_logger().error(f'Ollama detection failed: {e}')
            return []

    def _build_detection_msg(self, detections: list) -> Detection2DArray:
        """构建 Detection2DArray 消息"""
        msg = Detection2DArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_frame'

        for det in detections:
            d = Detection2D()
            d.bbox.center.x = float(det['bbox'][0] + det['bbox'][2] / 2)
            d.bbox.center.y = float(det['bbox'][1] + det['bbox'][3] / 2)
            d.bbox.size_x = float(det['bbox'][2])
            d.bbox.size_y = float(det['bbox'][3])

            hypothesis = ObjectHypothesisWithPose()
            hypothesis.hypothesis.class_id = det.get('class_name', 'unknown')
            hypothesis.hypothesis.score = det['confidence']
            d.results.append(hypothesis)

            msg.detections.append(d)

        return msg

    def _build_detection_text(self, detections: list) -> String:
        """构建文本描述"""
        if not detections:
            msg = String()
            msg.data = "No objects detected in the current view."
            return msg

        lines = ["Current objects detected in camera view:"]
        for det in detections:
            if det['bbox'][2] > 0:  # 有边界框
                lines.append(
                    f"- {det['class_name']} "
                    f"(confidence: {det['confidence']:.2f}, "
                    f"position: center at ({det['bbox'][0] + det['bbox'][2]/2:.0f}, "
                    f"{det['bbox'][1] + det['bbox'][3]/2:.0f}))"
                )
            else:
                lines.append(f"- {det['class_name']}")

        msg = String()
        msg.data = '\n'.join(lines)
        return msg

    def _get_default_yolo_model(self) -> str:
        """获取默认 YOLO 模型路径"""
        import os
        model_dir = os.path.join(
            os.path.dirname(__file__), '..', 'models'
        )
        os.makedirs(model_dir, exist_ok=True)
        return os.path.join(model_dir, 'yolov8n.onnx')

    def _load_coco_classes(self) -> list:
        """加载 COCO 类别名称"""
        return [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
            'train', 'truck', 'boat', 'traffic light', 'fire hydrant',
            'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog',
            'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe',
            'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
            'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat',
            'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
            'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot',
            'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
            'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven',
            'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase',
            'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]


def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### 4.2 LLM 聊天节点增强

在现有 `LLMChatNode` 中集成视觉上下文，使其能够感知视觉信息并做出响应。

#### 4.2.1 增强后的 LLMChatNode

```python
# File: src/llm_chat_node/llm_chat_node/__init__.py (增强版)

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import requests
import json

class LLMChatNode(Node):
    def __init__(self):
        super().__init__('llm_chat_node')

        # === 原有参数 ===
        self.declare_parameter('model', 'gemma4:e2b')
        self.declare_parameter('ollama_url', 'http://localhost:11434')
        self.declare_parameter('max_tokens', 2048)
        self.declare_parameter('temperature', 0.7)
        self.declare_parameter('timeout', 300)

        # === 新增视觉参数 ===
        self.declare_parameter('enable_vision', True)           # 启用视觉集成
        self.declare_parameter('vision_auto_context', True)     # 自动注入视觉上下文
        self.declare_parameter('vision_context_prompt',         # 视觉上下文注入模板
            '[Visual Context]\nThe camera currently sees:\n{detection_text}\n'
            'Please incorporate this visual information into your response '
            'if relevant to the user\'s question.'
        )

        self.model = self.get_parameter('model').get_parameter_value().string_value
        self.ollama_url = self.get_parameter('ollama_url').get_parameter_value().string_value
        self.max_tokens = self.get_parameter('max_tokens').get_parameter_value().integer_value
        self.temperature = self.get_parameter('temperature').get_parameter_value().double_value
        self.timeout = self.get_parameter('timeout').get_parameter_value().integer_value

        # === 视觉状态 ===
        self.enable_vision = self.get_parameter('enable_vision').value
        self.vision_auto_context = self.get_parameter('vision_auto_context').value
        self.latest_detection_text = "No visual information available."

        # === ROS 接口 ===
        # 原有话题
        self.sub = self.create_subscription(
            String, 'chat_input', self.handle_input, 10
        )
        self.pub = self.create_publisher(String, 'chat_output', 10)

        # 新增：订阅视觉检测结果
        if self.enable_vision:
            self.vision_sub = self.create_subscription(
                String,
                '/vision/detection_text',
                self.vision_callback,
                10
            )
            self.get_logger().info('Vision integration enabled')

        self.get_logger().info(f'LLM chat node ready. Model: {self.model}')

    def vision_callback(self, msg: String):
        """接收视觉检测结果并缓存"""
        self.latest_detection_text = msg.data
        self.get_logger().debug(f'Vision context updated: {msg.data[:50]}...')

    def handle_input(self, msg: String):
        prompt = msg.data
        self.get_logger().info(f'Received prompt: {prompt}')

        # === 增强：注入视觉上下文 ===
        if self.enable_vision and self.vision_auto_context:
            context_template = self.get_parameter('vision_context_prompt').value
            enhanced_prompt = context_template.format(
                detection_text=self.latest_detection_text
            )
            # 将视觉上下文和用户问题组合
            full_prompt = f"{enhanced_prompt}\n\nUser question: {prompt}"
        else:
            full_prompt = prompt

        try:
            self.get_logger().info('Sending request to Ollama...')
            resp = requests.post(
                f'{self.ollama_url}/api/generate',
                json={
                    'model': self.model,
                    'prompt': full_prompt,
                    'stream': False,
                    'options': {
                        'num_predict': self.max_tokens,
                        'temperature': self.temperature,
                    }
                },
                timeout=self.timeout
            )
            resp.raise_for_status()
            result = resp.json()
            reply = String()
            reply.data = result.get('response', '').strip()
            self.pub.publish(reply)
            self.get_logger().info(f'Published reply ({len(reply.data)} chars)')
        except Exception as e:
            self.get_logger().error(f'Ollama request failed: {e}')
            import traceback
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
```

### 4.3 摄像头驱动节点

如果系统没有现成的摄像头驱动，可以创建一个简单的 USB 摄像头节点：

```python
# File: src/llm_chat_node/llm_chat_node/camera_node.py

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class CameraNode(Node):
    """USB 摄像头驱动节点"""

    def __init__(self):
        super().__init__('camera_node')

        self.declare_parameter('camera_id', 0)
        self.declare_parameter('frame_width', 640)
        self.declare_parameter('frame_height', 480)
        self.declare_parameter('fps', 30)

        camera_id = self.get_parameter('camera_id').value
        width = self.get_parameter('frame_width').value
        height = self.get_parameter('frame_height').value
        fps = self.get_parameter('fps').value

        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        if not self.cap.isOpened():
            self.get_logger().error('Failed to open camera')
            raise RuntimeError('Camera not available')

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, '/camera/image_raw', 10)

        # 定时发布图像
        self.timer = self.create_timer(1.0 / fps, self.timer_callback)

        self.get_logger().info(
            f'Camera node ready. Device: {camera_id}, '
            f'Resolution: {width}x{height} @ {fps}fps'
        )

    def timer_callback(self):
        ret, frame = self.cap.read()
        if ret:
            msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'camera_frame'
            self.pub.publish(msg)

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

---

## 5. 启动配置

### 5.1 启动文件

```python
# File: src/llm_chat_node/launch/vision_chat_launch.py

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        # === 参数声明 ===
        DeclareLaunchArgument('detector_type', default_value='yolo',
                              description='Detection type: yolo or ollama'),
        DeclareLaunchArgument('camera_id', default_value='0',
                              description='Camera device ID'),
        DeclareLaunchArgument('enable_vision', default_value='true',
                              description='Enable vision integration'),

        # === 摄像头节点 ===
        Node(
            package='llm_chat_node',
            executable='camera_node',
            name='camera_node',
            output='screen',
            parameters=[{
                'camera_id': LaunchConfiguration('camera_id'),
                'frame_width': 640,
                'frame_height': 480,
                'fps': 30,
            }],
        ),

        # === 视觉识别节点 ===
        Node(
            package='llm_chat_node',
            executable='vision_node',
            name='vision_node',
            output='screen',
            parameters=[{
                'detector_type': LaunchConfiguration('detector_type'),
                'yolo_model_path': '',
                'yolo_confidence': 0.5,
                'yolo_nms_threshold': 0.45,
                'ollama_model': 'llava',
                'ollama_url': 'http://localhost:11434',
                'image_topic': '/camera/image_raw',
                'detection_interval': 1.0,
                'enable_auto_trigger': True,
            }],
        ),

        # === LLM 聊天节点（增强版） ===
        Node(
            package='llm_chat_node',
            executable='llm_chat_node',
            name='llm_chat_node',
            output='screen',
            parameters=[{
                'model': 'gemma4:e2b',
                'ollama_url': 'http://localhost:11434',
                'max_tokens': 2048,
                'temperature': 0.7,
                'timeout': 300,
                'enable_vision': LaunchConfiguration('enable_vision'),
                'vision_auto_context': True,
            }],
        ),
    ])
```

### 5.2 入口点配置

在 `setup.py` 中添加新的入口点：

```python
entry_points={
    'console_scripts': [
        'llm_chat_node = llm_chat_node:main',
        'vision_node = llm_chat_node.vision_node:main',
        'camera_node = llm_chat_node.camera_node:main',
    ],
},
```

---

## 6. 依赖管理

### 6.1 package.xml 新增依赖

```xml
<!-- 新增依赖 -->
<exec_depend>sensor_msgs</exec_depend>
<exec_depend>vision_msgs</exec_depend>
<exec_depend>cv_bridge</exec_depend>
<exec_depend>python3-opencv</exec_depend>
<exec_depend>python3-requests</exec_depend>
```

### 6.2 Python 依赖

```bash
# requirements.txt
opencv-python>=4.8.0
opencv-contrib-python>=4.8.0
numpy>=1.24.0
requests>=2.28.0
# 可选：用于 YOLO 模型下载
wget
```

---

## 7. 模型部署

### 7.1 YOLO 模型下载

```bash
# 自动下载脚本（首次运行时执行）
python3 -c "
import urllib.request
import os

model_dir = os.path.expanduser('~/ros-chat/src/llm_chat_node/models')
os.makedirs(model_dir, exist_ok=True)

# YOLOv8n ONNX 模型
url = 'https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.onnx'
output = os.path.join(model_dir, 'yolov8n.onnx')

if not os.path.exists(output):
    print(f'Downloading YOLOv8n model...')
    urllib.request.urlretrieve(url, output)
    print('Download complete!')
else:
    print('Model already exists.')
"
```

### 7.2 Ollama 多模态模型

```bash
# 安装 LLaVA 多模态模型
ollama pull llava

# 或使用 Gemma3 Vision（如果可用）
ollama pull gemma3:12b
```

---

## 8. 使用指南

### 8.1 快速启动（YOLO 方案）

```bash
# 1. 构建
cd ~/Desktop/ros-chat
source /opt/ros/jazzy/setup.bash
colcon build --packages-select llm_chat_node
source install/setup.bash

# 2. 启动（YOLO 检测 + LLM 聊天）
ros2 launch llm_chat_node vision_chat_launch.py detector_type:=yolo

# 3. 发送消息（AI 会自动感知摄像头画面）
ros2 topic pub --once /chat_input std_msgs/String "data: '我现在面前有什么？'"
```

### 8.2 快速启动（Ollama 多模态方案）

```bash
# 启动（使用 LLaVA 多模态模型）
ros2 launch llm_chat_node vision_chat_launch.py detector_type:=ollama

# 发送消息
ros2 topic pub --once /chat_input std_msgs/String "data: '描述一下你看到的场景'"
```

### 8.3 调试命令

```bash
# 查看原始检测结果（结构化）
ros2 topic echo /vision/detection

# 查看检测文本描述
ros2 topic echo /vision/detection_text

# 查看摄像头画面（需要 image_view 包）
ros2 run image_view image_view image:=/camera/image_raw

# 手动触发检测
ros2 topic pub --once /vision/trigger std_msgs/String "data: 'detect'"
```

---

## 9. 精准识别优化策略

### 9.1 提高 YOLO 检测精度

| 策略 | 方法 | 预期提升 |
|------|------|---------|
| 模型升级 | YOLOv8s → YOLOv8m/l/x | mAP +5~15% |
| 输入分辨率 | 640→1280 | 小物体检测 +20% |
| 置信度调优 | 0.5→0.3（召回优先） | 减少漏检 |
| 数据增强 | Mosaic, MixUp | 泛化能力 +10% |
| 自定义训练 | 针对特定场景微调 YOLO | 特定场景精度 +30%+ |

### 9.2 多模型级联策略

```
用户提问
  → 关键词分析（是否需要视觉信息？）
    → 是：触发视觉检测
      → YOLO 快速检测（毫秒级）
        → 检测到物体？
          → 是：将检测结果注入 LLM 上下文
          → 否：触发 Ollama 多模态深度分析（秒级）
    → 否：直接发送给 LLM
```

### 9.3 视觉上下文管理

- **滑动窗口**：保留最近 N 帧的检测结果，避免单帧误检
- **置信度过滤**：低于阈值的检测结果不注入 LLM 上下文
- **去重合并**：同一物体在连续帧中只报告一次
- **时间戳标记**：标注检测时间，LLM 可判断信息时效性

---

## 10. 扩展性设计

### 10.1 插件式检测器架构

```python
class BaseDetector(ABC):
    """检测器基类"""
    @abstractmethod
    def detect(self, image: np.ndarray) -> list:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

class YOLODetector(BaseDetector):
    def detect(self, image):
        # YOLO 实现
        pass

    def get_name(self):
        return "YOLOv8"

class OLLAMADetector(BaseDetector):
    def detect(self, image):
        # Ollama 多模态实现
        pass

    def get_name(self):
        return "LLaVA"

class OCRDetector(BaseDetector):
    def detect(self, image):
        # OCR 文字识别
        pass

    def get_name(self):
        return "PaddleOCR"

class FaceDetector(BaseDetector):
    def detect(self, image):
        # 人脸检测
        pass

    def get_name(self):
        return "FaceNet"
```

### 10.2 未来可扩展功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 人脸识别 | 识别人物身份 | ⭐⭐⭐ |
| OCR 文字识别 | 识别图像中的文字 | ⭐⭐⭐ |
| 手势识别 | 识别手势指令 | ⭐⭐ |
| 目标跟踪 | 跟踪移动物体 | ⭐⭐ |
| 深度估计 | 估算物体距离 | ⭐ |
| 场景分类 | 识别场景类型（室内/室外） | ⭐ |

---

## 11. 性能与资源评估

### 11.1 资源消耗估算

| 组件 | CPU 使用率 | GPU 显存 | 内存 | 磁盘 |
|------|-----------|---------|------|------|
| 摄像头节点 | ~5% | 0MB | ~50MB | 0MB |
| YOLO 检测节点 | ~20% (CPU) / ~5% (GPU) | ~500MB | ~200MB | ~6MB |
| Ollama 多模态节点 | ~50% | ~4-8GB | ~2GB | ~4-7GB |
| LLM 聊天节点 | ~10% | ~2-4GB (gemma4) | ~500MB | ~4GB |

### 11.2 推荐硬件配置

| 配置等级 | CPU | GPU | 内存 | 适用场景 |
|---------|-----|-----|------|---------|
| 最低配置 | 4 核 | 集成显卡 | 8GB | YOLO CPU 推理 |
| 推荐配置 | 8 核 | NVIDIA GTX 1060 6GB | 16GB | YOLO GPU + LLM |
| 最佳配置 | 12 核 | NVIDIA RTX 3060 12GB+ | 32GB | 全功能运行 |

---

## 12. 实施路线图

### Phase 1：基础搭建（1-2 天）
- [x] 项目结构分析完成
- [ ] 创建 `vision_node.py` 基础框架
- [ ] 创建 `camera_node.py` 摄像头驱动
- [ ] 更新 `package.xml` 和 `setup.py`
- [ ] 创建启动文件 `vision_chat_launch.py`
- [ ] 下载 YOLO 模型
- [ ] 构建并验证基本通信

### Phase 2：YOLO 集成（2-3 天）
- [ ] 实现 YOLO ONNX 推理
- [ ] 实现 NMS 后处理
- [ ] 实现 Detection2DArray 消息发布
- [ ] 实现检测文本描述生成
- [ ] 性能调优（GPU 加速）

### Phase 3：LLM 视觉集成（1-2 天）
- [ ] 增强 LLMChatNode 订阅视觉话题
- [ ] 实现视觉上下文注入逻辑
- [ ] 实现 Prompt 模板系统
- [ ] 测试端到端对话

### Phase 4：Ollama 多模态方案（1-2 天）
- [ ] 实现 Base64 图像编码
- [ ] 实现 Ollama 多模态 API 调用
- [ ] 实现检测器类型切换
- [ ] 对比测试两种方案

### Phase 5：优化与扩展（持续）
- [ ] 实现多模型级联策略
- [ ] 实现视觉上下文滑动窗口
- [ ] 添加 OCR 识别支持
- [ ] 添加人脸识别支持
- [ ] 编写单元测试
- [ ] 编写使用文档

---

## 13. 总结

本设计方案为 `ros-chat` 项目提供了完整的视觉识别模块集成方案，核心特点：

1. **双方案并行**：YOLO 提供毫秒级实时检测，Ollama 多模态提供深度场景理解，用户可根据需求灵活切换
2. **ROS2 原生集成**：所有视觉数据通过 ROS2 话题发布，与现有 LLM 聊天节点无缝对接，保持系统架构一致性
3. **可扩展架构**：插件式检测器设计，便于后续添加人脸识别、OCR 等功能
4. **精准识别优化**：提供多级优化策略，从模型升级到自定义训练，满足不同精度需求
5. **低门槛部署**：YOLO 模型仅 6MB，CPU 即可运行，适合资源受限场景

通过本方案的实施，`ros-chat` 将从纯文本聊天系统升级为具备视觉感知能力的智能交互系统，能够"看见"并"理解"周围环境，实现更自然、更智能的人机交互体验。
