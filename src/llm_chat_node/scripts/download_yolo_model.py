#!/usr/bin/env python3
"""
YOLOv8n ONNX 模型下载脚本
首次运行视觉识别模块前执行此脚本下载模型
"""
import urllib.request
import os
import sys


def download_model():
    # 模型保存目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(script_dir, '..', 'llm_chat_node', 'models')
    os.makedirs(model_dir, exist_ok=True)

    output = os.path.join(model_dir, 'yolov8n.onnx')

    if os.path.exists(output):
        size_mb = os.path.getsize(output) / 1024 / 1024
        print(f'Model already exists at: {output}')
        print(f'Size: {size_mb:.1f} MB')
        return True

    # 多个可能的下载源（按优先级排列）
    urls = [
        'https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.onnx',
        'https://github.com/ultralytics/ultralytics/releases/download/v8.2.0/yolov8n.onnx',
        'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx',
    ]

    for url in urls:
        print(f'Trying to download from: {url}')
        print(f'Saving to: {output}')
        try:
            urllib.request.urlretrieve(url, output)
            size_mb = os.path.getsize(output) / 1024 / 1024
            print(f'Download complete! Size: {size_mb:.1f} MB')
            print(f'Model saved to: {output}')
            return True
        except Exception as e:
            print(f'Failed: {e}')
            # 清理可能的部分下载文件
            if os.path.exists(output):
                os.remove(output)
            continue

    print('\nAll download sources failed.')
    print('\nYou can manually download the model:')
    print('1. Visit: https://github.com/ultralytics/ultralytics/releases')
    print('2. Download yolov8n.onnx from the latest release')
    print(f'3. Save it to: {output}')
    print('\nOr use the following command:')
    print('  wget https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.onnx -O ' + output)
    return False


if __name__ == '__main__':
    success = download_model()
    sys.exit(0 if success else 1)
