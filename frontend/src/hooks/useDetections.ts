import { useEffect, useRef } from 'react';
import { useAppStore } from '../store';

/**
 * 检测数据 Hook
 * 从 store 获取通过 rosbridge 接收的真实检测数据。
 * 仅当 ROS2 后端（YOLO 节点）运行时，检测框才会显示。
 * 负责 FPS 统计和 YOLO 状态更新
 */
export function useDetections() {
  const {
    isCameraOn,
    setDetections,
    updateSystemStatus,
    rosConnection,
  } = useAppStore();
  const frameCountRef = useRef(0);
  const lastFpsTimeRef = useRef(Date.now());
  const fpsIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!isCameraOn) {
      // 摄像头关闭时，清空检测数据并停止所有定时器
      if (fpsIntervalRef.current) {
        clearInterval(fpsIntervalRef.current);
        fpsIntervalRef.current = null;
      }
      setDetections([]);
      updateSystemStatus({ yolo: 'stopped', fps: 0, detectionLatency: 0 });
      return;
    }

    // 摄像头开启时，标记 YOLO 状态为等待中
    updateSystemStatus({ yolo: 'running' });

    // 清空检测数据，等待真实数据通过 rosbridge 到达
    setDetections([]);

    // FPS 统计：每秒计算一次
    fpsIntervalRef.current = setInterval(() => {
      const now = Date.now();
      const elapsed = now - lastFpsTimeRef.current;
      if (elapsed >= 1000) {
        const fps = Math.round((frameCountRef.current * 1000) / elapsed);
        updateSystemStatus({
          fps: Math.min(fps, 30),
          detectionLatency: 0,
        });
        frameCountRef.current = 0;
        lastFpsTimeRef.current = now;
      }
    }, 1000);

    return () => {
      if (fpsIntervalRef.current) {
        clearInterval(fpsIntervalRef.current);
        fpsIntervalRef.current = null;
      }
    };
  }, [isCameraOn, setDetections, updateSystemStatus]);
}
