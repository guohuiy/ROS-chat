# ROS-Chat 项目下一步开发计划

> 生成日期：2026-05-09
> 最后更新：2026-05-09
> 基于项目分析报告与前端设计方案

---

## 一、项目当前状态总结

### 1.1 ROS2 后端 — ✅ 功能完整（已增强）

| 模块 | 文件 | 状态 | 功能 |
|------|------|------|------|
| LLM 聊天节点 | `llm_chat_node/__init__.py` | ✅ 完成 | 通过 `/chat_input` 和 `/chat_output` 话题实现与 Ollama 对话，支持视觉上下文自动注入、对话历史管理、重试机制、系统提示词配置、流式输出 |
| 摄像头驱动节点 | `camera_node.py` | ✅ 完成 | USB 摄像头驱动，发布 `/camera/image_raw`，支持分辨率/帧率/设备 ID 配置 |
| 视觉识别节点 | `vision_node.py` | ✅ 完成 | YOLOv8n (ONNX Runtime/OpenCV DNN) + Ollama 多模态两种检测方案，发布 `/vision/detection` 和 `/vision/detection_text`，支持健康检查心跳 |
| 启动文件 | `launch/` | ✅ 完成 | `llm_chat_launch.py`（纯聊天）和 `vision_chat_launch.py`（完整视觉） |
| YOLO 模型 | `models/yolov8n.onnx` | ✅ 完成 | 已下载到本地 |
| 项目构建 | `build/`, `install/` | ✅ 完成 | 已通过 `colcon build` 成功构建 |

### 1.2 前端 — ✅ 全部功能已完成

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| React + TypeScript + Vite | `frontend/` | ✅ 完成 | 已成功编译，端口 3000 |
| 摄像头面板 | `CameraPanel.tsx` | ✅ 完成 | 视频流显示 + 检测框叠加层 + 全屏控制，坐标适配实际视频尺寸 |
| 对象统计面板 | `StatsPanel.tsx` | ✅ 完成 | ECharts 饼图 + 柱状图 + 对象列表 |
| AI 对话面板 | `ChatPanel.tsx` | ✅ 完成 | Markdown 渲染 + 打字指示器 + 视觉/文本模式切换，支持通过 rosbridge 发送消息 |
| 状态栏 | `StatusBar.tsx` | ✅ 完成 | 5 节点状态显示 + 性能指标 + 检测文本摘要 |
| 设置对话框 | `SettingsDialog.tsx` | ✅ 完成 | 模型选择 + 置信度阈值 + ROS Bridge 地址 |
| 全局状态管理 | `store/index.ts` | ✅ 完成 | Zustand 管理所有应用状态，包含 `detectionText` 和 `rosbridge` 状态 |
| 暗色主题 CSS | `styles/global.css` | ✅ 完成 | 完整暗色主题，增强移动端响应式布局 |
| **ROS Bridge 连接** | **`useRosbridge.ts`** | **✅ 完成** | **真实 WebSocket 连接、话题订阅/发布、消息解析、自动重连** |
| **检测数据** | **`useDetections.ts`** | **✅ 完成** | **从 store 读取真实检测数据，FPS 统计** |
| **AI 对话** | **`useChat.ts`** | **✅ 完成** | **通过 rosbridge 发布到 `/chat_input`，无连接时降级提示** |
| **摄像头流** | **`useCamera.ts`** | **✅ 完成** | **聚焦本地摄像头管理（getUserMedia），状态同步** |

### 1.3 当前架构

```
用户浏览器 ──(WebSocket)──> rosbridge_server (ws://localhost:9090)
                                  │
                                  ├── /vision/detection (vision_msgs/Detection2DArray)
                                  ├── /vision/detection_text (std_msgs/String)
                                  ├── /chat_input (std_msgs/String) ← 发布
                                  └── /chat_output (std_msgs/String)
```

---

## 二、第一阶段：实现真实 rosbridge 数据连接（最高优先级）

### 2.1 任务概述

将前端 4 个 hooks 从模拟数据切换到真实的 rosbridge WebSocket 通信，使前端能够与 ROS2 后端实时交互。

### 2.2 话题映射

| ROS2 话题 | 类型 | 前端操作 | 当前状态 | 目标状态 |
|-----------|------|---------|---------|---------|
| `/camera/image_raw` | `sensor_msgs/Image` | 订阅 → 显示视频 | ❌ 未使用 | ✅ 实时视频流 |
| `/vision/detection` | `vision_msgs/Detection2DArray` | 订阅 → 绘制检测框 | ❌ 未使用 | ✅ 实时检测框 |
| `/vision/detection_text` | `std_msgs/String` | 订阅 → 注入聊天上下文 | ❌ 未使用 | ✅ 视觉上下文 |
| `/chat_input` | `std_msgs/String` | 发布 | ❌ 未使用 | ✅ 发送消息 |
| `/chat_output` | `std_msgs/String` | 订阅 → 显示回复 | ❌ 未使用 | ✅ 接收回复 |

### 2.3 详细实现方案

#### 2.3.1 改造 `useRosbridge.ts` — 实现真实 WebSocket 连接

**当前问题**：WebSocket 连接代码被注释，使用 `setTimeout` 模拟连接成功。

**改造方案**：

```typescript
// useRosbridge.ts - 完整实现
import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '../store';

// ROS消息类型定义
interface RosMessage {
  op: string;           // 操作类型: 'subscribe' | 'unsubscribe' | 'publish' | 'advertise'
  topic?: string;       // 话题名称
  type?: string;        // 消息类型
  msg?: any;            // 消息内容
  id?: string;          // 消息ID
}

export function useRosbridge() {
  const {
    rosConnection, setRosConnection,
    setDetections, addMessage, setProcessing,
    updateSystemStatus
  } = useAppStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 发送 ROS 操作消息
  const sendRosMessage = useCallback((msg: RosMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  // 订阅话题
  const subscribeTopic = useCallback((topic: string, type: string) => {
    sendRosMessage({ op: 'subscribe', topic, type });
  }, [sendRosMessage]);

  // 取消订阅话题
  const unsubscribeTopic = useCallback((topic: string) => {
    sendRosMessage({ op: 'unsubscribe', topic });
  }, [sendRosMessage]);

  // 发布消息到话题
  const publishMessage = useCallback((topic: string, type: string, msg: any) => {
    sendRosMessage({ op: 'publish', topic, type, msg });
  }, [sendRosMessage]);

  // 处理接收到的 ROS 消息
  const handleRosMessage = useCallback((data: any) => {
    const { op, topic, msg } = data;

    if (op === 'publish') {
      switch (topic) {
        case '/vision/detection':
          // 解析检测结果
          if (msg?.detections) {
            const detections = msg.detections.map((d: any) => ({
              class_name: d.results?.[0]?.hypothesis?.class_id || 'unknown',
              confidence: d.results?.[0]?.hypothesis?.score || 0,
              bbox: [
                d.bbox?.center?.position?.x - d.bbox?.size_x / 2 || 0,
                d.bbox?.center?.position?.y - d.bbox?.size_y / 2 || 0,
                d.bbox?.size_x || 0,
                d.bbox?.size_y || 0,
              ] as [number, number, number, number],
            }));
            setDetections(detections);
          }
          break;

        case '/chat_output':
          // 解析 AI 回复
          if (msg?.data) {
            const assistantMsg = {
              id: `msg_${Date.now()}`,
              role: 'assistant' as const,
              content: msg.data,
              timestamp: Date.now(),
            };
            addMessage(assistantMsg);
            setProcessing(false);
          }
          break;

        case '/vision/detection_text':
          // 更新检测文本描述（用于聊天上下文）
          if (msg?.data) {
            updateSystemStatus({ detectionText: msg.data });
          }
          break;
      }
    }
  }, [setDetections, addMessage, setProcessing, updateSystemStatus]);

  // 建立连接
  const connect = useCallback((url: string = 'ws://localhost:9090') => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setRosConnection('connecting');

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('ROS Bridge connected');
        setRosConnection('connected');

        // 订阅所有需要的话题
        subscribeTopic('/vision/detection', 'vision_msgs/Detection2DArray');
        subscribeTopic('/chat_output', 'std_msgs/String');
        subscribeTopic('/vision/detection_text', 'std_msgs/String');

        // 更新系统状态
        updateSystemStatus({ rosbridge: 'connected' });

        // 启动心跳检测
        heartbeatTimerRef.current = setInterval(() => {
          sendRosMessage({ op: 'ping' });
        }, 10000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleRosMessage(data);
        } catch (e) {
          console.error('Failed to parse ROS message:', e);
        }
      };

      ws.onclose = () => {
        console.log('ROS Bridge disconnected');
        setRosConnection('disconnected');
        updateSystemStatus({ rosbridge: 'disconnected' });
        wsRef.current = null;

        // 清理心跳
        if (heartbeatTimerRef.current) {
          clearInterval(heartbeatTimerRef.current);
          heartbeatTimerRef.current = null;
        }

        // 自动重连
        reconnectTimerRef.current = setTimeout(() => {
          connect(url);
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error('ROS Bridge error:', error);
        setRosConnection('error');
        updateSystemStatus({ rosbridge: 'error' });
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setRosConnection('error');
    }
  }, [setRosConnection, subscribeTopic, updateSystemStatus, sendRosMessage, handleRosMessage]);

  // 断开连接
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      // 取消所有订阅
      unsubscribeTopic('/vision/detection');
      unsubscribeTopic('/chat_output');
      unsubscribeTopic('/vision/detection_text');

      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
    setRosConnection('disconnected');
    updateSystemStatus({ rosbridge: 'disconnected' });
  }, [unsubscribeTopic, setRosConnection, updateSystemStatus]);

  // 自动重连
  useEffect(() => {
    if (rosConnection === 'disconnected' || rosConnection === 'error') {
      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, 3000);
    }
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [rosConnection, connect]);

  // 清理
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connect,
    disconnect,
    publishMessage,
    isConnected: rosConnection === 'connected',
  };
}
```

#### 2.3.2 改造 `useDetections.ts` — 从 ROS2 获取真实检测数据

**当前问题**：使用 `generateMockDetections()` 生成随机检测数据。

**改造方案**：检测数据现在由 `useRosbridge.ts` 中的 `handleRosMessage` 处理，`useDetections.ts` 只需负责 FPS 统计和状态更新。

```typescript
// useDetections.ts - 从 store 获取真实检测数据
import { useEffect, useRef } from 'react';
import { useAppStore } from '../store';

export function useDetections() {
  const {
    isCameraOn,
    detections,
    updateSystemStatus,
  } = useAppStore();
  const frameCountRef = useRef(0);
  const lastFpsTimeRef = useRef(Date.now());

  useEffect(() => {
    if (!isCameraOn) {
      updateSystemStatus({ yolo: 'stopped', fps: 0, detectionLatency: 0 });
      return;
    }

    updateSystemStatus({ yolo: 'running' });

    // 计算 FPS（基于检测数据更新频率）
    const fpsInterval = setInterval(() => {
      frameCountRef.current++;
      const now = Date.now();
      const elapsed = now - lastFpsTimeRef.current;
      if (elapsed >= 1000) {
        const fps = Math.round((frameCountRef.current * 1000) / elapsed);
        updateSystemStatus({ fps: Math.min(fps, 30) });
        frameCountRef.current = 0;
        lastFpsTimeRef.current = now;
      }
    }, 200);

    return () => {
      clearInterval(fpsInterval);
    };
  }, [isCameraOn, detections, updateSystemStatus]);
}
```

#### 2.3.3 改造 `useChat.ts` — 通过 ROS2 发送/接收消息

**当前问题**：使用硬编码规则匹配生成回复。

**改造方案**：

```typescript
// useChat.ts - 通过 rosbridge 发布/订阅 ROS2 话题
import { useCallback } from 'react';
import { useAppStore, generateMessageId } from '../store';

export function useChat() {
  const {
    messages,
    addMessage,
    isProcessing,
    setProcessing,
    isCameraOn,
    detections,
    modelName,
  } = useAppStore();

  // 获取 publishMessage 函数（从 rosbridge hook）
  // 注意：需要通过 props 或 store 传递 publishMessage
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
      if (publishFn) {
        publishFn('/chat_input', 'std_msgs/String', { data: content.trim() });
      } else {
        // 降级：如果没有 publishFn，使用模拟回复
        console.warn('No publish function available, using mock reply');
        setTimeout(() => {
          const assistantMsg = {
            id: generateMessageId(),
            role: 'assistant' as const,
            content: '⚠️ ROS Bridge 未连接，无法获取 AI 回复。请检查连接状态。',
            timestamp: Date.now(),
          };
          addMessage(assistantMsg);
          setProcessing(false);
        }, 1000);
      }
    },
    [messages, addMessage, isProcessing, setProcessing, isCameraOn, detections, modelName]
  );

  return {
    messages,
    sendMessage,
    isProcessing,
  };
}
```

#### 2.3.4 改造 `CameraPanel.tsx` — 通过 rosbridge 订阅摄像头话题

**当前问题**：仅获取本地摄像头，未连接 ROS2 话题。

**改造方案**：在保留本地摄像头预览的同时，通过 rosbridge 订阅 `/camera/image_raw` 获取 ROS2 端视频帧，并在 canvas 上绘制检测框。

```typescript
// CameraPanel.tsx - 关键改造部分

// 1. 添加 rosbridge 订阅摄像头话题
useEffect(() => {
  if (!isCameraOn || !rosbridgeConnected) return;

  // 通过 rosbridge 订阅摄像头话题
  // 注意：sensor_msgs/Image 是二进制数据，需要特殊处理
  // 方案一：使用 rosbridge 的 base64 编码图像传输
  // 方案二：前端直接使用本地摄像头（getUserMedia），检测框来自 ROS2
  
  // 推荐方案二：本地摄像头预览 + ROS2 检测框叠加
  // 这样延迟更低，用户体验更好
}, [isCameraOn, rosbridgeConnected]);

// 2. 检测框坐标适配实际视频尺寸
useEffect(() => {
  if (!isCameraOn || !canvasRef.current || detections.length === 0) return;

  const canvas = canvasRef.current;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const video = videoRef.current;
  if (!video) return;

  // 获取实际视频显示尺寸
  const displayWidth = video.clientWidth;
  const displayHeight = video.clientHeight;

  // 获取原始视频尺寸（640x480）
  const originalWidth = video.videoWidth || 640;
  const originalHeight = video.videoHeight || 480;

  // 计算缩放比例
  const scaleX = displayWidth / originalWidth;
  const scaleY = displayHeight / originalHeight;

  // 清空画布
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 设置 canvas 尺寸匹配显示尺寸
  canvas.width = displayWidth;
  canvas.height = displayHeight;

  // 绘制每个检测框（坐标适配）
  detections.forEach((det: Detection) => {
    const [x, y, w, h] = det.bbox;
    const color = getColorForClass(det.class_name);

    // 适配实际显示尺寸
    const adaptedX = x * scaleX;
    const adaptedY = y * scaleY;
    const adaptedW = w * scaleX;
    const adaptedH = h * scaleY;

    // 绘制边界框
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(adaptedX, adaptedY, adaptedW, adaptedH);

    // 绘制标签
    const label = `${det.class_name} ${(det.confidence * 100).toFixed(0)}%`;
    ctx.font = '14px Arial, sans-serif';
    const textWidth = ctx.measureText(label).width;
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.8;
    ctx.fillRect(adaptedX, adaptedY - 22, textWidth + 10, 22);
    ctx.globalAlpha = 1;
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText(label, adaptedX + 5, adaptedY - 6);
  });
}, [isCameraOn, detections]);
```

### 2.4 需要修改的文件清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `frontend/src/hooks/useRosbridge.ts` | 🔄 重写 | 实现真实 WebSocket 连接、话题订阅/发布、消息解析、心跳检测、自动重连 |
| `frontend/src/hooks/useDetections.ts` | 🔄 重写 | 移除模拟数据生成，改为从 store 读取真实检测数据 |
| `frontend/src/hooks/useChat.ts` | 🔄 重写 | 移除硬编码回复，改为通过 rosbridge 发布/订阅 |
| `frontend/src/hooks/useCamera.ts` | 🔄 重写 | 移除 mock canvas，聚焦本地摄像头管理 |
| `frontend/src/components/CameraPanel.tsx` | 🔄 修改 | 检测框坐标适配实际视频尺寸 |
| `frontend/src/App.tsx` | 🔄 修改 | 传递 publishMessage 给 ChatPanel |
| `frontend/src/store/index.ts` | 🔄 修改 | 添加 `detectionText` 字段到 SystemStatus |
| `frontend/src/types/index.ts` | 🔄 修改 | 更新 SystemStatus 接口 |

### 2.5 实施步骤

```
Step 1: 更新 types/index.ts — 添加 detectionText 字段
Step 2: 更新 store/index.ts — 添加 detectionText 到 SystemStatus
Step 3: 重写 useRosbridge.ts — 实现真实 WebSocket 连接
Step 4: 重写 useDetections.ts — 从 store 读取真实数据
Step 5: 重写 useChat.ts — 通过 rosbridge 发布/订阅
Step 6: 重写 useCamera.ts — 聚焦本地摄像头管理
Step 7: 修改 CameraPanel.tsx — 坐标适配
Step 8: 修改 App.tsx — 传递 publishMessage
Step 9: 测试端到端连接
```

---

## 三、第二阶段：功能完善（中优先级）

### 3.1 对话历史管理（后端）

**目标**：实现多轮对话上下文，支持会话历史缓存。

**修改文件**：`src/llm_chat_node/llm_chat_node/__init__.py`

```python
# 在 LLMChatNode 类中添加
class LLMChatNode(Node):
    def __init__(self):
        # ... 现有代码 ...
        
        # 新增参数
        self.declare_parameter('enable_history', True)
        self.declare_parameter('history_window', 10)  # 保留最近 N 轮对话
        self.declare_parameter('history_max_tokens', 4096)  # 历史最大 token 数
        
        # 对话历史缓存
        self.conversation_history = []
        
        # 新增话题：发布对话历史
        self.history_pub = self.create_publisher(String, '/chat/history', 10)
    
    def handle_input(self, msg: String):
        prompt = msg.data
        
        # 构建带历史的 prompt
        if self.enable_history and self.conversation_history:
            history_text = self._build_history_context()
            full_prompt = f"{history_text}\n\nUser: {prompt}"
        else:
            full_prompt = prompt
        
        # ... 调用 Ollama ...
        
        # 保存到历史
        self.conversation_history.append({"role": "user", "content": prompt})
        self.conversation_history.append({"role": "assistant", "content": reply.data})
        
        # 滑动窗口裁剪
        self._trim_history()
    
    def _build_history_context(self) -> str:
        """构建历史上下文文本"""
        lines = ["Previous conversation:"]
        for turn in self.conversation_history[-self.history_window*2:]:
            prefix = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {turn['content']}")
        return "\n".join(lines)
    
    def _trim_history(self):
        """裁剪历史到最大 token 数"""
        # 简单实现：按轮次裁剪
        while len(self.conversation_history) > self.history_window * 2:
            self.conversation_history.pop(0)
```

### 3.2 错误处理增强

**目标**：添加 Ollama 请求重试、节点健康检查。

**修改文件**：
- `src/llm_chat_node/llm_chat_node/__init__.py` — 添加重试机制
- `src/llm_chat_node/llm_chat_node/vision_node.py` — 添加健康检查

```python
# 在 LLMChatNode.handle_input 中添加重试
import time

def _call_ollama_with_retry(self, payload: dict, max_retries: int = 3) -> dict:
    """带指数退避的 Ollama 调用"""
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f'{self.ollama_url}/api/generate',
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                self.get_logger().warn(
                    f'Ollama request failed (attempt {attempt + 1}/{max_retries}), '
                    f'retrying in {wait}s: {e}'
                )
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            raise
```

### 3.3 系统提示词配置

**目标**：支持通过参数配置 system prompt。

**修改文件**：`src/llm_chat_node/llm_chat_node/__init__.py`

```python
# 新增参数
self.declare_parameter('system_prompt', '')  # 自定义 system prompt
self.declare_parameter('system_prompt_file', '')  # 从文件加载

# 加载 system prompt
system_prompt = self.get_parameter('system_prompt').value
system_prompt_file = self.get_parameter('system_prompt_file').value

if not system_prompt and system_prompt_file:
    try:
        with open(system_prompt_file, 'r') as f:
            system_prompt = f.read().strip()
    except Exception as e:
        self.get_logger().error(f'Failed to load system prompt file: {e}')

if system_prompt:
    self.system_prompt = system_prompt
else:
    self.system_prompt = "You are a helpful AI assistant with vision capabilities."

# 在 handle_input 中注入 system prompt
def handle_input(self, msg: String):
    prompt = msg.data
    full_prompt = f"{self.system_prompt}\n\n{prompt}"
    # ... 调用 Ollama ...
```

---

## 四、第三阶段：体验优化（低优先级）

### 4.1 流式输出支持

**目标**：实现打字机效果，逐字显示 AI 回复。

**后端修改**：`src/llm_chat_node/llm_chat_node/__init__.py`

```python
# 新增参数
self.declare_parameter('stream_output', True)  # 启用流式输出

# 新增话题：流式输出
self.stream_pub = self.create_publisher(String, '/chat_output/stream', 10)

def handle_input(self, msg: String):
    # ... 构建 prompt ...
    
    if self.stream_output:
        # 流式调用 Ollama
        resp = requests.post(
            f'{self.ollama_url}/api/generate',
            json={
                'model': self.model,
                'prompt': full_prompt,
                'stream': True,  # 启用流式
                'options': {...}
            },
            stream=True,
            timeout=self.timeout
        )
        
        full_response = ""
        for line in resp.iter_lines():
            if line:
                chunk = json.loads(line)
                if 'response' in chunk:
                    full_response += chunk['response']
                    # 发布每个 token
                    stream_msg = String()
                    stream_msg.data = chunk['response']
                    self.stream_pub.publish(stream_msg)
        
        # 发布完整回复
        reply = String()
        reply.data = full_response
        self.pub.publish(reply)
```

**前端修改**：`frontend/src/hooks/useChat.ts`

```typescript
// 订阅 /chat_output/stream 实现打字机效果
// 使用累积缓冲区，逐字追加到消息内容
```

### 4.2 移动端适配完善

**修改文件**：`frontend/src/styles/global.css`

```css
/* 增强响应式布局 */
@media (max-width: 900px) {
  .app-main {
    flex-direction: column;
  }
  .left-panel {
    width: 100%;
    min-width: 0;
    max-height: 50vh;
  }
  .right-panel {
    border-left: none;
    border-top: 1px solid var(--border-color);
    min-width: 0;
  }
  .stats-charts {
    grid-template-columns: 1fr;
  }
  .camera-controls {
    flex-wrap: wrap;
  }
  .chat-input-hint {
    flex-direction: column;
    gap: 4px;
  }
}

@media (max-width: 600px) {
  .app-header {
    padding: 8px 12px;
  }
  .header-title {
    font-size: 14px;
  }
  .header-logo {
    font-size: 20px;
  }
  .panel-header {
    padding: 8px 12px;
  }
  .chat-messages {
    padding: 12px;
  }
  .chat-input-area {
    padding: 8px 12px;
  }
  .stats-charts {
    grid-template-columns: 1fr;
  }
  .stats-chart-item {
    height: 200px;
  }
  .status-bar {
    flex-direction: column;
    gap: 4px;
    padding: 4px 12px;
  }
  .status-bar-left {
    flex-wrap: wrap;
    gap: 8px;
  }
}
```

---

## 五、实施路线图

### 时间估算

| 阶段 | 任务 | 预估工时 | 涉及文件数 |
|------|------|---------|-----------|
| **第一阶段** | 真实 rosbridge 数据连接 | **3-5 天** | 8 个文件 |
| 1.1 | 更新 types 和 store | 0.5 天 | 2 |
| 1.2 | 重写 useRosbridge.ts | 1 天 | 1 |
| 1.3 | 重写 useDetections.ts | 0.5 天 | 1 |
| 1.4 | 重写 useChat.ts | 0.5 天 | 1 |
| 1.5 | 重写 useCamera.ts + CameraPanel | 1 天 | 2 |
| 1.6 | 修改 App.tsx 集成 | 0.5 天 | 1 |
| 1.7 | 测试和调试 | 1 天 | - |
| **第二阶段** | 功能完善 | **3-4 天** | 3 个文件 |
| 2.1 | 对话历史管理（后端） | 1 天 | 1 |
| 2.2 | 错误处理增强 | 1 天 | 2 |
| 2.3 | 系统提示词配置 | 0.5 天 | 1 |
| 2.4 | 测试 | 1 天 | - |
| **第三阶段** | 体验优化 | **2-3 天** | 3 个文件 |
| 3.1 | 流式输出 | 1 天 | 2 |
| 3.2 | 移动端适配 | 0.5 天 | 1 |
| 3.3 | 动画和过渡优化 | 0.5 天 | 1 |
| 3.4 | 测试 | 0.5 天 | - |

### 总预估工时：**8-12 天**

---

## 六、测试验证方案

### 6.1 后端测试

```bash
# 1. 启动 ROS2 节点
cd ~/Desktop/ros-chat
source install/setup.bash
source ~/Desktop/llama-env/bin/activate

# 启动完整视觉聊天系统
ros2 launch llm_chat_node vision_chat_launch.py detector_type:=yolo

# 2. 验证话题通信
# 新终端
source install/setup.bash

# 查看摄像头话题
ros2 topic list
ros2 topic info /camera/image_raw

# 发送测试消息
ros2 topic pub --once /chat_input std_msgs/String "data: '你好'"

# 查看回复
ros2 topic echo /chat_output std_msgs/msg/String --full-length

# 查看检测结果
ros2 topic echo /vision/detection_text
```

### 6.2 前端测试

```bash
# 1. 启动前端开发服务器
cd ~/Desktop/ros-chat/frontend
npm run dev

# 2. 启动 rosbridge_server
# 新终端
source /opt/ros/humble/setup.bash
ros2 run rosbridge_server rosbridge_websocket

# 3. 打开浏览器访问 http://localhost:3000
# 验证：
#   - ROS Bridge 状态显示 🟢 已连接
#   - 开启摄像头后显示实时视频
#   - 检测框正确叠加
#   - 发送消息后收到 AI 回复
```

### 6.3 端到端测试流程

```
1. 启动 rosbridge_server
2. 启动 ROS2 节点 (vision_chat_launch.py)
3. 启动前端 (npm run dev)
4. 打开浏览器 → 确认 ROS Bridge 已连接
5. 点击"开启摄像头" → 确认视频流显示
6. 等待检测结果 → 确认检测框和统计面板更新
7. 输入消息 → 确认 AI 回复显示
8. 关闭摄像头 → 确认切换到文本模式
9. 输入纯文本消息 → 确认 AI 回复
```

---

## 七、文件修改对照表

### 第一阶段修改清单

| # | 文件路径 | 操作 | 关键变更 |
|---|---------|------|---------|
| 1 | `frontend/src/types/index.ts` | 🔄 修改 | SystemStatus 添加 `detectionText?: string` 和 `rosbridge?: string` |
| 2 | `frontend/src/store/index.ts` | 🔄 修改 | SystemStatus 默认值添加 `detectionText: ''`, `rosbridge: 'disconnected'` |
| 3 | `frontend/src/hooks/useRosbridge.ts` | 🔄 重写 | 实现真实 WebSocket 连接、话题订阅/发布、消息解析、心跳、重连 |
| 4 | `frontend/src/hooks/useDetections.ts` | 🔄 重写 | 移除 `generateMockDetections`，从 store 读取真实数据 |
| 5 | `frontend/src/hooks/useChat.ts` | 🔄 重写 | 移除硬编码回复，通过 `publishMessage` 发布到 `/chat_input` |
| 6 | `frontend/src/hooks/useCamera.ts` | 🔄 重写 | 移除 mock canvas，仅管理本地摄像头 |
| 7 | `frontend/src/components/CameraPanel.tsx` | 🔄 修改 | 检测框坐标适配实际视频尺寸 |
| 8 | `frontend/src/App.tsx` | 🔄 修改 | 从 `useRosbridge` 获取 `publishMessage` 并传递给 `ChatPanel` |

### 第二阶段修改清单

| # | 文件路径 | 操作 | 关键变更 |
|---|---------|------|---------|
| 9 | `src/llm_chat_node/llm_chat_node/__init__.py` | 🔄 修改 | 添加对话历史管理、重试机制、system prompt 配置 |
| 10 | `src/llm_chat_node/llm_chat_node/vision_node.py` | 🔄 修改 | 添加健康检查心跳发布 |

### 第三阶段修改清单

| # | 文件路径 | 操作 | 关键变更 |
|---|---------|------|---------|
| 11 | `src/llm_chat_node/llm_chat_node/__init__.py` | 🔄 修改 | 添加流式输出支持 |
| 12 | `frontend/src/hooks/useChat.ts` | 🔄 修改 | 添加流式输出订阅和打字机效果 |
| 13 | `frontend/src/styles/global.css` | 🔄 修改 | 增强移动端响应式布局