import React from 'react';
import { useAppStore } from '../store';

/** 系统状态栏 - 显示各节点运行状态 */
const StatusBar: React.FC = () => {
  const { systemStatus, rosConnection } = useAppStore();

  const statusItems = [
    {
      label: 'ROS Bridge',
      status: rosConnection,
      getIcon: (s: string) =>
        s === 'connected' ? '🟢' : s === 'connecting' ? '🟡' : '🔴',
    },
    {
      label: '摄像头',
      status: systemStatus.camera,
      getIcon: (s: string) =>
        s === 'connected' ? '🟢' : s === 'error' ? '🔴' : '⚫',
    },
    {
      label: 'YOLO',
      status: systemStatus.yolo,
      getIcon: (s: string) =>
        s === 'running' ? '🟢' : s === 'error' ? '🔴' : '⚫',
    },
    {
      label: 'Ollama',
      status: systemStatus.ollama,
      getIcon: (s: string) =>
        s === 'connected' ? '🟢' : s === 'error' ? '🔴' : '⚫',
    },
    {
      label: 'LLM',
      status: systemStatus.llm,
      getIcon: (s: string) =>
        s === 'running' ? '🟢' : s === 'error' ? '🔴' : '⚫',
    },
  ];

  return (
    <div className="status-bar">
      <div className="status-bar-left">
        {statusItems.map((item) => (
          <div key={item.label} className="status-item">
            <span className="status-icon">{item.getIcon(item.status)}</span>
            <span className="status-label">{item.label}</span>
          </div>
        ))}
      </div>
      <div className="status-bar-right">
        {systemStatus.fps > 0 && (
          <span className="status-metric">帧率: {systemStatus.fps} fps</span>
        )}
        {systemStatus.detectionLatency > 0 && (
          <span className="status-metric">
            检测延迟: {systemStatus.detectionLatency} ms
          </span>
        )}
        {systemStatus.detectionText && (
          <span className="status-metric status-detection-text" title={systemStatus.detectionText}>
            📝 检测: {systemStatus.detectionText.substring(0, 40)}...
          </span>
        )}
      </div>
    </div>
  );
};

export default StatusBar;
