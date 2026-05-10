from setuptools import find_packages, setup
import os

package_name = 'llm_chat_node'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            [os.path.join('launch', 'llm_chat_launch.py'),
             os.path.join('launch', 'vision_chat_launch.py')]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='huiya',
    maintainer_email='huiya@example.com',
    description='LLM chat node for ROS2 with vision integration',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'llm_chat_node=llm_chat_node.__init__:main',
            'vision_node=llm_chat_node.vision_node:main',
            'camera_node=llm_chat_node.camera_node:main',
        ]
    },
)
