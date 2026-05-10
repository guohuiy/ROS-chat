# File: src/llm_chat_node/llm_chat_node/camera_node.py
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import base64


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
            self.get_logger().error(
                f'Failed to open camera (ID: {camera_id}). '
                'Check camera connection or use a different camera_id.'
            )
            raise RuntimeError('Camera not available')

        self.bridge = CvBridge()

        # 发布原始图像（供 vision_node 检测用）
        self.raw_pub = self.create_publisher(Image, '/camera/image_raw', 10)

        # 发布 base64 编码的 JPEG 图像（供前端 Web 显示用，通过 rosbridge 传输）
        # 使用 std_msgs/String 避免 CompressedImage 二进制数据的序列化问题
        self.web_pub = self.create_publisher(String, '/camera/image_web', 10)

        # 定时发布图像
        self.timer = self.create_timer(1.0 / fps, self.timer_callback)

        self.get_logger().info(
            f'Camera node ready. Device: {camera_id}, '
            f'Resolution: {width}x{height} @ {fps}fps'
        )

    def timer_callback(self):
        ret, frame = self.cap.read()
        if ret:
            # 发布原始图像（BGR8，供 vision_node 检测用）
            raw_msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
            raw_msg.header.stamp = self.get_clock().now().to_msg()
            raw_msg.header.frame_id = 'camera_frame'
            self.raw_pub.publish(raw_msg)

            # 发布 base64 JPEG 图像（供前端 Web 显示用）
            # 压缩质量设为 70，减少 WebSocket 传输数据量
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, 70]
            _, jpeg_buffer = cv2.imencode('.jpg', frame, encode_param)
            jpeg_base64 = base64.b64encode(jpeg_buffer).decode('utf-8')

            web_msg = String()
            web_msg.data = jpeg_base64
            self.web_pub.publish(web_msg)

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = CameraNode()
        rclpy.spin(node)
        node.destroy_node()
    except RuntimeError as e:
        import sys
        print(f'Camera node error: {e}')
        sys.exit(1)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
