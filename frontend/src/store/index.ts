import { create } from 'zustand';
import {
  Detection,
  ChatMessage,
  SystemStatus,
  ObjectStat,
  RosConnectionStatus,
  getObjectColor,
} from '../types';

interface AppState {
  // ROS 连接
  rosConnection: RosConnectionStatus;
  setRosConnection: (status: RosConnectionStatus) => void;

  // 摄像头
  isCameraOn: boolean;
  toggleCamera: () => void;

  // ROS2 端摄像头画面（通过 rosbridge 订阅 /camera/image_raw/compressed 获取）
  rosImageData: string | null;  // base64 JPEG 数据
  setRosImageData: (data: string | null) => void;

  // 检测数据
  detections: Detection[];
  setDetections: (detections: Detection[]) => void;
  objectStats: ObjectStat[];
  updateObjectStats: (detections: Detection[]) => void;

  // 聊天
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  isProcessing: boolean;
  setProcessing: (processing: boolean) => void;

  // 系统状态
  systemStatus: SystemStatus;
  updateSystemStatus: (status: Partial<SystemStatus>) => void;

  // 设置
  showSettings: boolean;
  setShowSettings: (show: boolean) => void;
  modelName: string;
  setModelName: (name: string) => void;
  confidenceThreshold: number;
  setConfidenceThreshold: (threshold: number) => void;
}

let messageId = 0;

export const useAppStore = create<AppState>((set, get) => ({
  // ROS 连接
  rosConnection: 'disconnected',
  setRosConnection: (status) => set({ rosConnection: status }),

  // 摄像头
  isCameraOn: false,
  toggleCamera: () => set((state) => ({ isCameraOn: !state.isCameraOn })),

  // ROS2 端摄像头画面
  rosImageData: null,
  setRosImageData: (data) => set({ rosImageData: data }),

  // 检测数据
  detections: [],
  setDetections: (detections) => {
    set({ detections });
    get().updateObjectStats(detections);
  },
  objectStats: [],
  updateObjectStats: (detections) => {
    const countMap = new Map<string, number>();
    detections.forEach((d) => {
      countMap.set(d.class_name, (countMap.get(d.class_name) || 0) + 1);
    });
    const stats: ObjectStat[] = Array.from(countMap.entries())
      .map(([className, count]) => ({
        className,
        count,
        color: getObjectColor(className),
      }))
      .sort((a, b) => b.count - a.count);
    set({ objectStats: stats });
  },

  // 聊天
  messages: [
    {
      id: '0',
      role: 'system',
      content: '👋 你好！我是视觉AI助手。\n\n**当前状态**：ROS Bridge 已连接 ✅，等待 ROS2 后端响应。\n\n请确保已启动以下服务：\n\n1️⃣ **rosbridge_server**（已启动 ✅）\n2️⃣ **ROS2 LLM 聊天节点**（AI 后端）：\n```bash\ncd ~/Desktop/ros-chat\nsource install/setup.bash\nsource ~/Desktop/llama-env/bin/activate\nros2 launch llm_chat_node llm_chat_launch.py\n```\n3️⃣ **（可选）视觉识别完整版**：\n```bash\nros2 launch llm_chat_node vision_chat_launch.py detector_type:=yolo\n```\n\n启动后即可开始对话！',
      timestamp: Date.now(),
    },
  ],
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  isProcessing: false,
  setProcessing: (processing) => set({ isProcessing: processing }),

  // 系统状态
  systemStatus: {
    camera: 'disconnected',
    yolo: 'stopped',
    ollama: 'disconnected',
    llm: 'stopped',
    rosbridge: 'disconnected',
    fps: 0,
    detectionLatency: 0,
    detectionText: '',
  },
  updateSystemStatus: (status) =>
    set((state) => ({
      systemStatus: { ...state.systemStatus, ...status },
    })),

  // 设置
  showSettings: false,
  setShowSettings: (show) => set({ showSettings: show }),
  modelName: 'gemma4:e2b',
  setModelName: (name) => set({ modelName: name }),
  confidenceThreshold: 0.5,
  setConfidenceThreshold: (threshold) => set({ confidenceThreshold: threshold }),
}));

/** 生成唯一消息 ID */
export function generateMessageId(): string {
  messageId++;
  return `msg_${Date.now()}_${messageId}`;
}
