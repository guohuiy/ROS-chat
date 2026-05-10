/** 检测到的对象 */
export interface Detection {
  class_name: string;
  confidence: number;
  bbox: [number, number, number, number]; // [x, y, w, h]
}

/** 聊天消息 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

/** 系统状态 */
export interface SystemStatus {
  camera: 'connected' | 'disconnected' | 'error';
  yolo: 'running' | 'stopped' | 'error';
  ollama: 'connected' | 'disconnected' | 'error';
  llm: 'running' | 'stopped' | 'error';
  rosbridge: 'connected' | 'disconnected' | 'error';
  fps: number;
  detectionLatency: number;
  detectionText: string;
}

/** 对象统计数据 */
export interface ObjectStat {
  className: string;
  count: number;
  color: string;
}

/** ROS 连接状态 */
export type RosConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

/** 模拟检测数据生成器 - 每次生成不同的对象组合，模拟实时检测变化 */
export function generateMockDetections(): Detection[] {
  const classes = [
    'person', 'laptop', 'cup', 'cell phone', 'chair',
    'book', 'bottle', 'keyboard', 'mouse', 'tv'
  ];
  // 随机选择 2-4 个不同的类
  const shuffled = [...classes].sort(() => Math.random() - 0.5);
  const count = Math.floor(Math.random() * 3) + 2; // 2-4 个对象
  const selectedClasses = shuffled.slice(0, count);

  return selectedClasses.map((cls) => ({
    class_name: cls,
    confidence: 0.5 + Math.random() * 0.5,
    bbox: [
      Math.random() * 500,
      Math.random() * 300,
      50 + Math.random() * 150,
      50 + Math.random() * 200,
    ],
  }));
}


/** 对象颜色映射 */
export const OBJECT_COLORS: Record<string, string> = {
  person: '#FF6B6B',
  laptop: '#4ECDC4',
  cup: '#45B7D1',
  'cell phone': '#96CEB4',
  chair: '#FFEAA7',
  book: '#DDA0DD',
  bottle: '#98D8C8',
  keyboard: '#F7DC6F',
  mouse: '#BB8FCE',
  tv: '#85C1E9',
  default: '#95A5A6',
};

export function getObjectColor(className: string): string {
  return OBJECT_COLORS[className] || OBJECT_COLORS.default;
}
