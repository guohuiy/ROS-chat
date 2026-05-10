# ROS2 LLM Chat Node

基于 ROS2 和 Ollama 的 LLM 聊天节点，通过话题（Topic）通信实现与 AI 大模型的对话。支持视觉识别模块，可集成摄像头实时物体检测。

## 系统架构

```
用户输入 "你好"
  → /chat_input 话题 (std_msgs/String)
    → LLMChatNode 节点
      → Ollama API (gemma4:e2b)
        → 生成回复
          → /chat_output 话题 (std_msgs/String)
            → 用户收到回复
```

### 视觉识别架构（可选）

```
摄像头画面
  → /camera/image_raw 话题 (sensor_msgs/Image)
    → VisionNode 节点
      → YOLOv8n ONNX 推理 / Ollama 多模态模型
        → /vision/detection 话题 (vision_msgs/Detection2DArray)
        → /vision/detection_text 话题 (std_msgs/String)
          → LLMChatNode 节点（自动注入视觉上下文）
```

## 环境要求

- **操作系统**: Ubuntu 22.04（本开发环境）/ 24.04
- **ROS2**: Humble（Ubuntu 22.04）/ Jazzy（Ubuntu 24.04）
- **Python**: 3.10（Ubuntu 22.04 默认）/ 3.12（Ubuntu 24.04 默认）
- **Ollama**: 已安装并运行
- **CUDA**: 12.6（可选，用于 GPU 加速）

> **⚠️ 版本兼容性说明**
> - Ubuntu 22.04 (Jammy) → ROS2 **Humble** + Python **3.10**
> - Ubuntu 24.04 (Noble) → ROS2 **Jazzy** + Python **3.12**
> - 请根据你的 Ubuntu 版本选择对应的 ROS2 版本

## 安装与配置

### 1. 安装 ROS2（根据 Ubuntu 版本选择）

#### 选项 A：Ubuntu 22.04 → ROS2 Humble

```bash
# 设置编码
sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# 添加 ROS2 源
sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
# 注意：以下命令必须写在一行，不能换行
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list

# 安装 ROS2 Humble
sudo apt update
sudo apt install ros-humble-ros-base python3-colcon-common-extensions python3-rosdep

# 初始化 rosdep（如果遇到网络超时，重试即可）
sudo rosdep init
rosdep update

# 设置环境变量（建议添加到 ~/.bashrc）
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

#### 选项 B：Ubuntu 24.04 → ROS2 Jazzy

```bash
# 设置编码
sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# 添加 ROS2 源
sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
# 注意：以下命令必须写在一行，不能换行
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list

# 安装 ROS2 Jazzy
sudo apt update
sudo apt install ros-jazzy-ros-base python3-colcon-common-extensions python3-rosdep

# 初始化 rosdep
sudo rosdep init
rosdep update

# 设置环境变量（建议添加到 ~/.bashrc）
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 2. 安装 Ollama 并下载模型

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 启动 Ollama 服务
ollama serve

# 下载模型（以 gemma4:e2b 为例）
ollama pull gemma4:e2b

# 如需使用多模态视觉识别，还需下载 LLaVA 模型
ollama pull llava
```

### 3. 创建并激活 Python 虚拟环境

```bash
cd ~/Desktop
python3 -m venv llama-env
source llama-env/bin/activate
```

### 4. 安装 Python 依赖

```bash
# 确保虚拟环境已激活
source ~/Desktop/llama-env/bin/activate

# 安装基础依赖
pip install --upgrade pip
pip install setuptools

# 安装 ROS2 视觉模块依赖（如需使用视觉识别功能）
# 注意：ROS2 Humble 的 cv_bridge 需要 NumPy 1.x，请勿升级到 NumPy 2.x
pip install opencv-python opencv-contrib-python "numpy<2" requests onnxruntime
```

### 5. 安装 ROS2 依赖

> ⚠️ 将以下命令中的 `humble` 替换为你安装的 ROS2 版本（`humble` 或 `jazzy`）

```bash
cd ~/Desktop/ros-chat
source /opt/ros/humble/setup.bash

# 安装 vision_msgs 包（视觉识别功能需要）
sudo apt install ros-humble-vision-msgs
sudo apt install ros-humble-cv-bridge
```

> **💡 提示**：如果 `ros-humble-vision-msgs` 安装失败（ROS2 Humble 可能不包含此包），可以从源码编译：
> ```bash
> cd ~/Desktop
> git clone https://github.com/ros-perception/vision_msgs.git -b humble
> cd vision_msgs
> source /opt/ros/humble/setup.bash
> colcon build
> source install/setup.bash
> ```

### 6. 构建 ROS2 包

> ⚠️ 将以下命令中的 `humble` 替换为你安装的 ROS2 版本（`humble` 或 `jazzy`）

```bash
cd ~/Desktop/ros-chat
source /opt/ros/humble/setup.bash
source ~/Desktop/llama-env/bin/activate

# 构建
colcon build --packages-select llm_chat_node

# 设置环境（重要！每次新终端都需要执行）
source install/setup.bash

# 验证 ros2 命令可用
which ros2
# 应输出: /opt/ros/humble/bin/ros2
```

### 7. 下载 YOLO 模型（可选，视觉识别需要）

```bash
cd ~/Desktop/ros-chat
source ~/Desktop/llama-env/bin/activate

# 方式一：使用下载脚本
python3 src/llm_chat_node/scripts/download_yolo_model.py

# 方式二：手动下载
wget https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.onnx -O src/llm_chat_node/llm_chat_node/models/yolov8n.onnx
```

### 8. 一键设置环境（推荐）

将以下内容添加到 `~/.bashrc`，避免每次打开新终端都手动 source：

```bash
echo "# ROS2 LLM Chat Node 环境配置" >> ~/.bashrc
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source ~/Desktop/ros-chat/install/setup.bash" >> ~/.bashrc
echo "source ~/Desktop/llama-env/bin/activate" >> ~/.bashrc
source ~/.bashrc
```

## 运行

### 启动 LLM 聊天节点（基础版）

```bash
cd ~/Desktop/ros-chat
source install/setup.bash
source ~/Desktop/llama-env/bin/activate
ros2 launch llm_chat_node llm_chat_launch.py
```

启动后应看到输出：
```
[INFO] [llm_chat_node-1]: LLM chat node ready. Model: gemma4:e2b
```

### 启动视觉识别 + LLM 聊天（完整版）

```bash
cd ~/Desktop/ros-chat
source install/setup.bash
source ~/Desktop/llama-env/bin/activate

# YOLO 方案（推荐，实时物体检测）
ros2 launch llm_chat_node vision_chat_launch.py detector_type:=yolo

# Ollama 多模态方案（深度场景理解）
ros2 launch llm_chat_node vision_chat_launch.py detector_type:=ollama
```

### 发送消息

```bash
# 一次性发送
ros2 topic pub --once /chat_input std_msgs/String "data: '你好，请介绍你自己'"

# 带视觉上下文的问题（视觉模式下）
ros2 topic pub --once /chat_input std_msgs/String "data: '我现在面前有什么？'"
```

### 查看回复

```bash
# 查看完整回复（--full-length 防止截断）
ros2 topic echo /chat_output std_msgs/msg/String --full-length
```

### 视觉识别调试命令

```bash
# 查看检测结果（结构化）
ros2 topic echo /vision/detection

# 查看检测文本描述
ros2 topic echo /vision/detection_text

# 手动触发检测
ros2 topic pub --once /vision/trigger std_msgs/String "data: 'detect'"

# 查看摄像头画面（需要 image_view 包）
ros2 run image_view image_view image:=/camera/image_raw
```

## 话题接口

### 基础聊天话题

| 话题 | 类型 | 方向 | 说明 |
|------|------|------|------|
| `/chat_input` | `std_msgs/String` | 订阅 | 用户输入消息 |
| `/chat_output` | `std_msgs/String` | 发布 | AI 回复消息 |

### 视觉识别话题（可选）

| 话题 | 类型 | 方向 | 说明 |
|------|------|------|------|
| `/camera/image_raw` | `sensor_msgs/Image` | 订阅 | 摄像头原始图像 |
| `/vision/detection` | `vision_msgs/Detection2DArray` | 发布 | 结构化检测结果 |
| `/vision/detection_text` | `std_msgs/String` | 发布 | 检测结果文本描述 |
| `/vision/trigger` | `std_msgs/String` | 订阅 | 手动触发检测 |

## 参数配置

### LLM 聊天节点参数

通过 `launch/llm_chat_launch.py` 配置：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `model` | `gemma4:e2b` | Ollama 模型名称 |
| `ollama_url` | `http://localhost:11434` | Ollama API 地址 |
| `max_tokens` | `2048` | 最大生成 token 数 |
| `temperature` | `0.7` | 生成温度 (0.0~1.0) |
| `timeout` | `300` | API 请求超时时间（秒） |
| `enable_vision` | `true` | 启用视觉集成 |
| `vision_auto_context` | `true` | 自动注入视觉上下文 |

### 视觉识别节点参数

通过 `launch/vision_chat_launch.py` 配置：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `detector_type` | `yolo` | 检测器类型：`yolo` 或 `ollama` |
| `yolo_model_path` | `""` | YOLO 模型路径（自动查找） |
| `yolo_confidence` | `0.5` | 置信度阈值 |
| `yolo_nms_threshold` | `0.45` | NMS 阈值 |
| `ollama_model` | `llava` | Ollama 多模态模型 |
| `detection_interval` | `1.0` | 检测间隔（秒） |
| `enable_auto_trigger` | `true` | 自动定时检测 |

## Web 前端界面

项目包含一个基于 React + TypeScript 的 Web 前端界面，通过 rosbridge 与 ROS2 后端通信，提供实时摄像头画面显示、对象检测统计和 AI 对话功能。

### 前端架构

```
┌─────────────────────────────────────────────────────────────┐
│                    浏览器 (React + TypeScript)               │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │CameraPanel│  │StatsPanel│  │ChatPanel │  │StatusBar │   │
│  └─────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│        │             │             │             │          │
│  ┌─────┴─────────────┴─────────────┴─────────────┴──────┐   │
│  │                    Zustand Store                      │   │
│  │  rosConnection | detections | messages | systemStatus │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                           │                                  │
│  ┌────────────────────────┴─────────────────────────────┐   │
│  │              rosbridge WebSocket Client               │   │
│  │  (roslib.js)  ws://localhost:9090                     │   │
│  └────────────────────────┬─────────────────────────────┘   │
└───────────────────────────┼─────────────────────────────────┘
                            │ WebSocket
┌───────────────────────────┼─────────────────────────────────┐
│  ┌────────────────────────┴─────────────────────────────┐   │
│  │              rosbridge_server (ROS2)                  │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                           │                                  │
│  ┌──────────┐  ┌──────────┴──────────┐  ┌──────────────┐   │
│  │CameraNode│  │    VisionNode       │  │ LLMChatNode  │   │
│  │(USB Cam) │  │  (YOLOv8n ONNX)    │  │ (Ollama API) │   │
│  └──────────┘  └─────────────────────┘  └──────────────┘   │
│                                                             │
│                    ROS2 (Robot Operating System)             │
└─────────────────────────────────────────────────────────────┘
```

### 环境要求

- **Node.js**: 18.x 或更高版本
- **npm**: 9.x 或更高版本
- **rosbridge_server**: 需要 ROS2 环境运行 rosbridge

### 安装与运行

#### 1. 安装前端依赖

```bash
cd ~/Desktop/ros-chat/frontend
npm install
```

#### 2. 启动 rosbridge_server（ROS2 后端通信桥梁）

```bash
# 在已 source ROS2 环境的终端中运行
ros2 run rosbridge_server rosbridge_websocket
```

#### 3. 启动 ROS2 后端节点（可选，如需连接真实 ROS2 数据）

```bash
# 启动视觉聊天完整版（摄像头 + YOLO 检测 + LLM）
cd ~/Desktop/ros-chat
source install/setup.bash
source ~/Desktop/llama-env/bin/activate
ros2 launch llm_chat_node vision_chat_launch.py detector_type:=yolo
```

#### 4. 启动前端开发服务器

```bash
cd ~/Desktop/ros-chat/frontend
npm run dev
```

启动后浏览器访问 `http://localhost:5173` 即可打开 Web 界面。

#### 5. 构建生产版本

```bash
cd ~/Desktop/ros-chat/frontend
npm run build
```

构建产物在 `frontend/dist/` 目录下。

### 前端功能说明

| 功能模块 | 说明 |
|---------|------|
| **摄像头画面** | 显示本地摄像头实时画面，支持开启/关闭、全屏模式 |
| **检测框叠加** | 在视频上实时绘制 YOLO 检测边界框（通过 rosbridge 获取检测数据） |
| **对象统计** | 饼图 + 柱状图展示检测对象分布，列表显示各对象数量 |
| **AI 对话** | 聊天界面，支持 Markdown 渲染，视觉/文本模式切换 |
| **状态栏** | 显示 ROS Bridge、摄像头、YOLO、Ollama、LLM 各节点状态 |
| **设置对话框** | 模型选择、置信度阈值调节、ROS Bridge 地址配置 |

### 前端话题映射

| ROS2 话题 | 类型 | 前端操作 | 说明 |
|-----------|------|---------|------|
| `/camera/image_raw` | `sensor_msgs/Image` | 订阅 | 摄像头原始图像 |
| `/vision/detection` | `vision_msgs/Detection2DArray` | 订阅 → 绘制检测框 | 结构化检测结果 |
| `/vision/detection_text` | `std_msgs/String` | 订阅 → 注入聊天上下文 | 检测结果文本描述 |
| `/chat_input` | `std_msgs/String` | 发布 | 用户输入消息 |
| `/chat_output` | `std_msgs/String` | 订阅 → 显示回复 | AI 回复消息 |

### 常见前端问题

#### 1. 摄像头无法开启

确保浏览器已授予摄像头权限，或在浏览器地址栏左侧点击锁图标 → 网站设置 → 允许摄像头。

#### 2. ROS Bridge 连接失败

确保已启动 rosbridge_server：
```bash
ros2 run rosbridge_server rosbridge_websocket
```

前端默认连接 `ws://localhost:9090`，可在设置对话框中修改地址。

#### 3. 检测框不显示

- 确保 ROS2 后端已启动并正在发布检测数据
- 检查 ROS Bridge 连接状态是否为"已连接"
- 检查 YOLO 节点是否正常运行

#### 4. 前端编译错误

```bash
cd ~/Desktop/ros-chat/frontend
npm install  # 重新安装依赖
npm run build  # 重新构建
```

#### 5. `ENOSPC: System limit for number of file watchers reached` 错误

在 Linux 虚拟机或容器中运行 `npm run dev` 时可能出现此错误，原因是系统文件监控数量限制过低。

**临时解决**（立即生效）：
```bash
sudo sysctl fs.inotify.max_user_watches=524288
```

**永久解决**（重启后仍有效）：
```bash
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```


## 项目结构

```
ros-chat/
├── README.md                          # 项目文档
├── project_analysis_and_frontend_design.md  # 前端设计文档
├── vision_integration_design.md       # 视觉模块设计文档
├── next_development_plan.md           # 下一步开发计划
├── frontend/                          # Web 前端项目
│   ├── index.html                     # HTML 入口
│   ├── package.json                   # npm 依赖配置
│   ├── tsconfig.json                  # TypeScript 配置
│   ├── vite.config.ts                 # Vite 构建配置
│   └── src/
│       ├── main.tsx                   # React 入口
│       ├── App.tsx                    # 主应用组件
│       ├── types/index.ts             # 类型定义
│       ├── store/index.ts             # Zustand 状态管理
│       ├── hooks/
│       │   ├── useRosbridge.ts        # ROS2 WebSocket 连接
│       │   ├── useCamera.ts           # 摄像头控制
│       │   ├── useDetections.ts       # 检测数据管理
│       │   └── useChat.ts             # 聊天交互
│       ├── components/
│       │   ├── CameraPanel.tsx        # 摄像头画面面板
│       │   ├── StatsPanel.tsx         # 对象统计面板
│       │   ├── ChatPanel.tsx          # AI 对话面板
│       │   ├── StatusBar.tsx          # 状态栏
│       │   └── SettingsDialog.tsx     # 设置对话框
│       └── styles/
│           └── global.css             # 全局样式（暗色主题）
├── src/
│   └── llm_chat_node/
│       ├── package.xml                # ROS2 包描述
│       ├── setup.py                   # Python 包配置
│       ├── setup.cfg                  # 安装配置
│       ├── requirements.txt           # Python 依赖
│       ├── package.html               # 旧版包描述（可删除）
│       ├── launch/
│       │   ├── llm_chat_launch.py     # 基础聊天启动文件
│       │   └── vision_chat_launch.py  # 视觉聊天启动文件
│       ├── resource/
│       │   └── llm_chat_node          # 资源索引
│       ├── scripts/
│       │   └── download_yolo_model.py # YOLO 模型下载脚本
│       └── llm_chat_node/
│           ├── __init__.py            # LLM 聊天节点实现
│           ├── vision_node.py         # 视觉识别节点实现
│           ├── camera_node.py         # 摄像头驱动节点实现
│           ├── llm_chat_node          # 可执行入口脚本
│           ├── vision_node            # 视觉节点入口脚本
│           ├── camera_node            # 摄像头节点入口脚本
│           └── models/
│               └── yolov8n.onnx       # YOLO 模型文件
├── build/                             # 构建输出
├── install/                           # 安装输出
└── log/                               # 构建日志
```



## 常见问题

### 1. `ros2 topic echo` 显示不全

默认有截断限制，请使用 `--full-length` 参数：
```bash
ros2 topic echo /chat_output std_msgs/msg/String --full-length
```

### 2. 回复为空

`num_predict` 值过小可能导致模型返回空回复。建议设置为 `2048` 或更高。

### 3. Ollama 连接失败

确保 Ollama 服务正在运行：
```bash
ollama serve
curl http://localhost:11434/api/generate -d '{"model":"gemma4:e2b","prompt":"你好","stream":false}'
```

### 4. 找不到可执行文件

重新构建并 source 环境：
```bash
colcon build --packages-select llm_chat_node
source install/setup.bash
```

### 5. 虚拟环境找不到包

确保在运行节点前激活了虚拟环境：
```bash
source ~/Desktop/llama-env/bin/activate
```

### 6. 摄像头无法打开

检查摄像头连接，或指定不同的设备 ID：
```bash
ros2 launch llm_chat_node vision_chat_launch.py camera_id:=1
```

### 7. YOLO 模型未找到

运行下载脚本下载模型：
```bash
python3 src/llm_chat_node/scripts/download_yolo_model.py
```

### 8. ROS2 版本不匹配（"无法定位软件包"）

如果你遇到 `E: 无法定位软件包 ros-jazzy-xxx` 错误，说明你的 Ubuntu 版本与 ROS2 版本不匹配：

```bash
# 检查 Ubuntu 版本
lsb_release -a

# Ubuntu 22.04 → 使用 ROS2 Humble
sudo apt install ros-humble-ros-base

# Ubuntu 24.04 → 使用 ROS2 Jazzy
sudo apt install ros-jazzy-ros-base
```

### 9. `ros2：未找到命令`（command not found）

运行 `ros2 launch` 前必须先 source ROS2 环境和项目构建输出：

```bash
# 每次打开新终端都需要执行以下命令
source /opt/ros/humble/setup.bash      # 加载 ROS2 环境
source ~/Desktop/ros-chat/install/setup.bash  # 加载项目包
source ~/Desktop/llama-env/bin/activate       # 加载虚拟环境

# 验证
which ros2    # 应输出: /opt/ros/humble/bin/ros2
ros2 launch llm_chat_node llm_chat_launch.py
```

> **提示**：可以将以上 source 命令添加到 `~/.bashrc` 中，避免每次手动执行。

### 10. vision_msgs 在 ROS2 Humble 中不可用

ROS2 Humble 可能不包含 `vision_msgs` 包。如果 `sudo apt install ros-humble-vision-msgs` 失败，可以：

```bash
# 方式一：从源码安装
cd ~/Desktop
git clone https://github.com/ros-perception/vision_msgs.git -b humble
cd vision_msgs
source /opt/ros/humble/setup.bash
colcon build

# 方式二：使用 std_msgs/String 替代（简化方案）
# 视觉识别节点已经同时发布 /vision/detection_text (std_msgs/String)
# LLM 聊天节点只依赖 /vision/detection_text，不需要 vision_msgs
```

### 11. Ollama 返回 500 Internal Server Error

通常由以下原因引起：

**原因 1：系统内存不足**
```bash
# 检查 Ollama 错误
curl http://localhost:11434/api/generate -d '{"model":"gemma4:e2b","prompt":"hi","stream":false}'
# 可能返回: "model requires more system memory (X GiB) than is available (Y GiB)"

# 解决方案：使用更小的模型
ollama pull gemma4:2b    # 仅 ~1.6GB，适合 8GB 内存机器
# 或
ollama pull llama3.2:3b  # Meta 的轻量模型

# 启动时指定小模型
ros2 launch llm_chat_node llm_chat_launch.py model:=gemma4:2b
```

**原因 2：Ollama 服务未运行**
```bash
# 启动 Ollama
ollama serve

# 验证服务可用
curl http://localhost:11434/api/tags
```

**原因 3：模型未下载**
```bash
# 查看已下载的模型
curl http://localhost:11434/api/tags

# 下载模型
ollama pull gemma4:e2b
```

### 12. `/usr/bin/env: "python3\r": 没有那个文件或目录`

这是 Windows 换行符（CRLF）导致的问题。修复方法：

```bash
# 修复入口脚本的换行符
sed -i 's/\r$//' src/llm_chat_node/llm_chat_node/vision_node
sed -i 's/\r$//' src/llm_chat_node/llm_chat_node/camera_node
sed -i 's/\r$//' src/llm_chat_node/scripts/download_yolo_model.py

# 重新构建
colcon build --packages-select llm_chat_node
```

> **💡 预防**：在 Windows 上编辑文件后上传到 Linux 时，请确保使用 Unix 换行符（LF），或在 VS Code 中设置 `"files.eol": "\n"`。

### 13. 节点启动后立即退出（exit code 127）

exit code 127 表示脚本解释器未找到。通常由以下原因引起：
- 入口脚本包含 CRLF 换行符（见上一条）
- 入口脚本缺少可执行权限

```bash
# 添加可执行权限
chmod +x src/llm_chat_node/llm_chat_node/vision_node
chmod +x src/llm_chat_node/llm_chat_node/camera_node
chmod +x src/llm_chat_node/llm_chat_node/llm_chat_node
```

### 14. `AttributeError: _ARRAY_API not found`（NumPy 版本冲突）

ROS2 Humble 的 `cv_bridge` 依赖 NumPy 1.x，但虚拟环境中安装了 NumPy 2.x，导致导入 `cv_bridge` 时崩溃。

```bash
# 检查当前 NumPy 版本
pip show numpy

# 解决方案：降级到 NumPy 1.x
pip install "numpy<2"

# 验证修复
python3 -c "from cv_bridge import CvBridge; print('OK')"
```

> **💡 原因**：`pip install opencv-python` 时会自动安装最新的 NumPy 2.x，但 ROS2 Humble 的 `cv_bridge` 二进制包是用 NumPy 1.x 编译的，两者不兼容。

### 15. 摄像头无法打开（虚拟机环境）

在虚拟机（如 VMware、VirtualBox）中运行，或没有物理摄像头时，`camera_node` 会报错退出：

```
[ERROR] [camera_node]: Failed to open camera (ID: 0). Check camera connection or use a different camera_id.
Camera node error: Camera not available
```

**解决方案：**

```bash
# 方案一：使用虚拟摄像头（v4l2loopback）
sudo apt install v4l2loopback-dkms v4l2loopback-utils
sudo modprobe v4l2loopback

# 方案二：启动时不使用摄像头（仅测试 LLM 聊天）
ros2 launch llm_chat_node llm_chat_launch.py

# 方案三：使用测试图片代替摄像头（修改 camera_id）
ros2 launch llm_chat_node vision_chat_launch.py camera_id:=/dev/video2
```

### 16. CUDA 不可用（ONNX Runtime 警告）

如果看到以下警告，说明系统没有 NVIDIA GPU 或 CUDA 环境未配置：

```
UserWarning: Specified provider 'CUDAExecutionProvider' is not in available provider names.
Available providers: 'AzureExecutionProvider, CPUExecutionProvider'
```

**解决方案：**

```bash
# 方案一：使用 CPU 推理（YOLO 仍可运行，速度较慢）
# 无需任何操作，ONNX Runtime 会自动回退到 CPU

# 方案二：安装 CUDA 和 cuDNN（需要 NVIDIA GPU）
# 参考 NVIDIA 官方文档安装 CUDA 12.x
# 然后安装 GPU 版 ONNX Runtime
pip uninstall onnxruntime
pip install onnxruntime-gpu

# 方案三：使用 OpenCV DNN 后端（在 vision_node.py 中已实现自动回退）
```

## 项目当前进展

### ✅ 已完成功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 基础 LLM 聊天节点 | ✅ 完成 | 支持通过 `/chat_input` 和 `/chat_output` 话题通信 |
| Ollama API 集成 | ✅ 完成 | 支持调用 Ollama 生成回复，可配置模型、温度、token 数等 |
| 视觉识别节点 | ✅ 完成 | 支持 YOLO（ONNX Runtime/OpenCV DNN）和 Ollama 多模态两种检测方案 |
| 摄像头驱动节点 | ✅ 完成 | USB 摄像头驱动，支持配置分辨率、帧率、设备 ID |
| 视觉上下文注入 | ✅ 完成 | LLM 聊天节点自动订阅视觉检测结果并注入 prompt |
| 启动文件 | ✅ 完成 | 提供 `llm_chat_launch.py` 和 `vision_chat_launch.py` 两种启动方式 |
| YOLO 模型下载脚本 | ✅ 完成 | 自动下载 yolov8n.onnx，支持多个备用下载源 |
| YOLO 模型文件 | ✅ 完成 | `models/yolov8n.onnx` 已下载到本地 |
| 项目构建 | ✅ 完成 | 已通过 `colcon build` 成功构建 |

### 🚧 已知问题

| 问题 | 状态 | 说明 |
|------|------|------|
| 入口脚本 CRLF 换行符 | ✅ 已修复 | `vision_node`、`camera_node`、`download_yolo_model.py` 已修复 |
| 对话历史管理 | ❌ 未实现 | 当前每次请求独立，无多轮对话上下文 |
| 系统提示词配置 | ❌ 未实现 | 不支持通过参数配置 system prompt |
| 错误重试机制 | ❌ 未实现 | Ollama 请求失败时无自动重试 |
| 节点健康检查 | ❌ 未实现 | 无心跳检测机制 |

## 下一步开发建议

### 短期任务（1-2 周）

1. **对话历史管理**
   - 实现多轮对话上下文管理，支持会话历史缓存
   - 添加 `/chat/history` 话题发布对话历史
   - 实现滑动窗口机制，控制上下文长度避免超出 token 限制

2. **系统提示词配置**
   - 支持通过参数配置 system prompt
   - 支持角色设定（如"你是一个机器人助手"）
   - 支持从文件加载 system prompt

3. **错误处理增强**
   - 添加 Ollama 请求重试机制（指数退避）
   - 实现节点健康检查心跳（`/health` 话题）
   - 添加 Ollama 服务可用性检测

### 中期任务（2-4 周）

4. **视觉识别优化**
   - 实现多模型级联策略（YOLO 快速检测 + Ollama 深度分析）
   - 添加滑动窗口去重，避免连续帧重复检测
   - 支持检测结果可视化（在图像上绘制边界框）
   - 添加检测结果缓存和置信度过滤

5. **Web 管理界面**
   - 基于 ROS2 Web Bridge 开发 Web 聊天界面
   - 实时显示摄像头画面和检测结果
   - 支持参数在线调整
   - 支持对话历史可视化

6. **多模型支持**
   - 支持切换不同 Ollama 模型
   - 支持本地 llama.cpp 模型推理（替代 Ollama）
   - 支持 OpenAI API 兼容接口

### 长期任务（1-2 个月）

7. **语音交互**
   - 集成语音识别（STT）节点
   - 集成语音合成（TTS）节点
   - 实现完整的语音对话流程

8. **机器人集成**
   - 将检测到的物体坐标转换为机器人导航指令
   - 实现"看到物体 → 导航到物体"的闭环
   - 支持机械臂抓取指令生成

9. **性能监控与日志**
   - 添加 Prometheus 指标暴露
   - 实现结构化日志存储
   - 可视化推理延迟和资源使用
   - 添加性能基准测试

10. **插件化检测器架构**
    - 实现 `BaseDetector` 抽象基类
    - 支持 YOLO、OCR、人脸识别等插件式扩展
    - 提供检测器热加载机制
    - 支持自定义检测器注册

### 代码质量改进

11. **单元测试**
    - 为 LLMChatNode 添加单元测试
    - 为 VisionNode 添加单元测试（mock 摄像头和模型）
    - 添加集成测试（节点间通信验证）

12. **代码重构**
    - 将入口脚本中的虚拟环境路径查找逻辑抽取为公共模块
    - 统一错误处理模式
    - 添加类型注解（Type Hints）
    - 使用 `entry_points` 替代 `scripts`（更符合 ROS2 Python 包规范）

## 许可证

MIT
