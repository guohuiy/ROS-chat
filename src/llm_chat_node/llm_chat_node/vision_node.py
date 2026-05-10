# File: src/llm_chat_node/llm_chat_node/vision_node.py
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from cv_bridge import CvBridge
import cv2
import json
import numpy as np
import sys
import os


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

        # === 健康检查 ===
        self.health_pub = self.create_publisher(String, '/vision/health', 10)
        self.health_timer = self.create_timer(5.0, self._publish_health)

        self.get_logger().info(
            f'Vision node ready. Detector: {self.detector_type}'
        )

    def _publish_health(self):
        """发布健康检查心跳"""
        msg = String()
        msg.data = json.dumps({
            'status': 'running',
            'detector': self.detector_type,
            'fps': 0,
            'timestamp': self.get_clock().now().to_msg().sec
        })
        self.health_pub.publish(msg)

    def _init_yolo_detector(self):
        """初始化 YOLO 检测器（使用 ONNX Runtime）"""
        model_path = self.get_parameter('yolo_model_path').value
        if not model_path:
            model_path = self._get_default_yolo_model()

        if not os.path.exists(model_path):
            self.get_logger().error(
                f'YOLO model not found at: {model_path}\n'
                'Please run: python3 src/llm_chat_node/scripts/download_yolo_model.py'
            )
            self.get_logger().warn('YOLO detector disabled: model not found')
            self.yolo_disabled = True
            return

        self.yolo_disabled = False

        # 尝试导入 onnxruntime
        # ROS2 launch 可能不使用虚拟环境的 Python，需要手动添加虚拟环境路径
        _ort = None
        try:
            import onnxruntime as _ort
        except ImportError:
            # 尝试查找并添加 llama-env 虚拟环境的 site-packages
            _venv_site = os.path.expanduser('~/Desktop/llama-env/lib/python3.10/site-packages')
            if os.path.isdir(_venv_site) and _venv_site not in sys.path:
                sys.path.insert(0, _venv_site)
            try:
                import onnxruntime as _ort
                self.get_logger().info('onnxruntime loaded from virtual environment')
            except ImportError:
                self.get_logger().warn(
                    'onnxruntime not found. '
                    'Falling back to OpenCV DNN. '
                    'Install with: pip install onnxruntime-gpu'
                )

        # 使用 ONNX Runtime（优先）或 OpenCV DNN（回退）
        if _ort is not None:
            try:
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                self.ort_session = _ort.InferenceSession(
                    model_path, providers=providers
                )
                actual_provider = self.ort_session.get_providers()[0]
                if 'CUDA' in actual_provider:
                    self.get_logger().info('YOLO: CUDA acceleration enabled (ONNX Runtime)')
                else:
                    self.get_logger().info('YOLO: Using CPU (ONNX Runtime)')
            except Exception as e:
                self.get_logger().error(f'ONNX Runtime failed to load model: {e}')
                self.get_logger().warn('YOLO detector disabled: ONNX Runtime model load failed')
                self.yolo_disabled = True
                return
        else:
            # 回退到 OpenCV DNN
            self.get_logger().warn(
                'onnxruntime not available, falling back to OpenCV DNN. '
                'Install with: pip install onnxruntime-gpu'
            )
            try:
                self.net = cv2.dnn.readNetFromONNX(model_path)
                try:
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                    self.get_logger().info('YOLO: CUDA acceleration enabled (OpenCV DNN)')
                except Exception:
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self.get_logger().info('YOLO: Using CPU (OpenCV DNN)')
            except Exception as e:
                self.get_logger().error(f'OpenCV DNN failed to load model: {e}')
                self.get_logger().warn('YOLO detector disabled: OpenCV DNN model load failed')
                self.yolo_disabled = True
                return

        # COCO 类别名称（80 类）
        self.classes = self._load_coco_classes()
        self.get_logger().info(
            f'YOLO: Loaded {len(self.classes)} COCO classes'
        )


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
        """YOLO 推理（支持 ONNX Runtime 和 OpenCV DNN）"""
        # 检查 YOLO 是否已禁用（模型加载失败）
        if getattr(self, 'yolo_disabled', False):
            return []

        confidence_threshold = self.get_parameter('yolo_confidence').value
        nms_threshold = self.get_parameter('yolo_nms_threshold').value

        # 预处理：缩放到 640x640
        h_img, w_img = image.shape[:2]
        from .detectors import yolo_preprocess, yolo_postprocess

        input_blob, scale, pad = yolo_preprocess(image, (640, 640))

        # 推理
        if hasattr(self, 'ort_session'):
            # ONNX Runtime 推理
            input_name = self.ort_session.get_inputs()[0].name
            outputs = self.ort_session.run(None, {input_name: input_blob})[0][0]
        elif hasattr(self, 'net'):
            # OpenCV DNN 推理
            self.net.setInput(input_blob)
            outputs = self.net.forward()[0]
        else:
            return []

        # 后处理：使用可测试的 postprocess 工具
        try:
            # ONNX Runtime/ OpenCV DNN 输出不同，统一传递给 postprocess
            from .detectors import yolo_postprocess

            results = yolo_postprocess(outputs, scale, pad, (h_img, w_img), confidence_threshold, nms_threshold, self.classes)
            return results
        except Exception as e:
            self.get_logger().error(f'YOLO postprocess failed: {e}')
            return []

    def _yolo_preprocess(self, image: np.ndarray, target_size=(640, 640)):
        """YOLO 图像预处理：保持宽高比的 letterbox 缩放"""
        h, w = image.shape[:2]
        target_w, target_h = target_size

        # 计算缩放比例
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)

        # 缩放图像
        resized = cv2.resize(image, (new_w, new_h))

        # 创建画布并居中放置
        canvas = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        pad_x = (target_w - new_w) // 2
        pad_y = (target_h - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

        # 转换为 blob (NCHW 格式)
        blob = cv2.dnn.blobFromImage(canvas, 1/255.0, swapRB=True, crop=False)

        return blob, scale, (pad_x, pad_y)


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
            d.bbox.center.position.x = float(det['bbox'][0] + det['bbox'][2] / 2)
            d.bbox.center.position.y = float(det['bbox'][1] + det['bbox'][3] / 2)
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
        """获取默认 YOLO 模型路径（支持 src 和 install 两种部署方式）"""
        import os

        # 当前文件所在目录（安装后为 .../site-packages/llm_chat_node/）
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 优先查找与当前 package 同目录下的 models
        candidate_local = os.path.join(current_dir, 'models', 'yolov8n.onnx')
        if os.path.exists(candidate_local):
            return candidate_local

        # 向上查找仓库中的 src 路径（兼容安装与源码布局）
        parts = current_dir.split(os.sep)
        for i in range(len(parts), 0, -1):
            parent = os.sep.join(parts[:i])
            src_path = os.path.join(parent, 'src', 'llm_chat_node', 'llm_chat_node', 'models', 'yolov8n.onnx')
            if os.path.exists(src_path):
                return src_path

        # 通过环境变量前缀查找（使用 os.pathsep，兼容 Windows 与 Unix）
        for env_var in ['COLCON_PREFIX_PATH', 'AMENT_PREFIX_PATH']:
            prefixes = os.environ.get(env_var, '').split(os.pathsep)
            for prefix in prefixes:
                if not prefix:
                    continue
                src_path = os.path.normpath(os.path.join(prefix, '..', 'src', 'llm_chat_node', 'llm_chat_node', 'models', 'yolov8n.onnx'))
                if os.path.exists(src_path):
                    return src_path

        # 最后返回本地候选路径（即使不存在），调用方会在不存在时抛错并提示下载
        return candidate_local




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
