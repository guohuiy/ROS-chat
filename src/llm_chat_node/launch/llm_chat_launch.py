from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
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
            }],
        ),
    ])
