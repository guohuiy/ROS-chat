from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, OpaqueFunction, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch.events import Shutdown
import os
import site


def generate_launch_description():
    return LaunchDescription([
        # === 参数声明 ===
        DeclareLaunchArgument('detector_type', default_value='yolo',
                              description='Detection type: yolo or ollama'),
        DeclareLaunchArgument('camera_id', default_value='0',
                              description='Camera device ID'),
        DeclareLaunchArgument('enable_vision', default_value='true',
                              description='Enable vision integration'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='Use simulation time'),

        # === 摄像头节点 ===
        Node(
            package='llm_chat_node',
            executable='camera_node',
            name='camera_node',
            output='screen',
            emulate_tty=True,
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
            emulate_tty=True,
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
            emulate_tty=True,
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
