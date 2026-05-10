import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useAppStore } from '../store';
import { Detection, getObjectColor } from '../types';

/** 摄像头画面面板 - 显示 ROS2 端摄像头实时画面和 YOLO 检测框叠加 */
const CameraPanel: React.FC = () => {
  const {
    isCameraOn,
    detections,
    systemStatus,
    toggleCamera,
    updateSystemStatus,
    rosImageData,
    rosConnection,
  } = useAppStore();
  const detectionCount = detections.length;
  const hasDetections = detectionCount > 0;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const animationFrameRef = useRef<number>(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  // 切换摄像头显示
  const handleToggleCamera = useCallback(() => {
    if (isCameraOn) {
      toggleCamera();
      updateSystemStatus({ camera: 'disconnected' });
      setImageLoaded(false);
    } else {
      toggleCamera();
      if (rosConnection === 'connected') {
        updateSystemStatus({ camera: 'connected' });
      }
    }
  }, [isCameraOn, toggleCamera, updateSystemStatus, rosConnection]);

  // 在 canvas 上持续绘制检测框
  useEffect(() => {
    if (!isCameraOn || !canvasRef.current || !imageRef.current) {
      if (canvasRef.current) {
        const ctx = canvasRef.current.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
      }
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const drawDetections = () => {
      if (!canvas || !ctx || !imageRef.current) return;

      const img = imageRef.current;
      const displayWidth = img.clientWidth || 640;
      const displayHeight = img.clientHeight || 480;
      const originalWidth = img.naturalWidth || 640;
      const originalHeight = img.naturalHeight || 480;

      const scaleX = displayWidth / originalWidth;
      const scaleY = displayHeight / originalHeight;

      canvas.width = displayWidth;
      canvas.height = displayHeight;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      detections.forEach((det: Detection) => {
        const [x, y, w, h] = det.bbox;
        const color = getObjectColor(det.class_name);

        const adaptedX = x * scaleX;
        const adaptedY = y * scaleY;
        const adaptedW = w * scaleX;
        const adaptedH = h * scaleY;

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(adaptedX, adaptedY, adaptedW, adaptedH);

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

      animationFrameRef.current = requestAnimationFrame(drawDetections);
    };

    animationFrameRef.current = requestAnimationFrame(drawDetections);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = 0;
      }
    };
  }, [isCameraOn, detections]);

  // 全屏切换
  const handleFullscreen = useCallback(() => {
    const container = document.getElementById('camera-container');
    if (!container) return;

    if (!document.fullscreenElement) {
      container.requestFullscreen().then(() => setIsFullscreen(true));
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false));
    }
  }, []);

  useEffect(() => {
    const handleChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handleChange);
    return () => document.removeEventListener('fullscreenchange', handleChange);
  }, []);

  return (
    <div className="panel camera-panel">
      <div className="panel-header">
        <span className="panel-icon">📷</span>
        <span className="panel-title">摄像头画面</span>
        <div className="panel-header-right">
          <span className={`status-dot ${isCameraOn ? 'online' : 'offline'}`} />
          <span className="status-text">{isCameraOn ? '已开启' : '已关闭'}</span>
        </div>
      </div>

      <div id="camera-container" className="camera-container">
        {isCameraOn ? (
          <>
            {rosImageData ? (
              <>
                <img
                  ref={imageRef}
                  src={rosImageData}
                  alt="ROS2 Camera Feed"
                  className="camera-video"
                  onLoad={() => setImageLoaded(true)}
                  onError={() => setImageLoaded(false)}
                />
                <canvas
                  ref={canvasRef}
                  className="detection-overlay"
                  width={640}
                  height={480}
                />
                <div className="camera-info">
                  <span>分辨率: 640×480</span>
                  <span>帧率: {systemStatus.fps}fps</span>
                  <span>延迟: {systemStatus.detectionLatency}ms</span>
                </div>
              </>
            ) : (
              <div className="camera-placeholder">
                <div className="placeholder-icon">📷</div>
                <p className="placeholder-text">等待摄像头数据...</p>
                <p className="placeholder-sub">
                  {rosConnection === 'connected'
                    ? '请确保 ROS2 后端 camera_node 已启动'
                    : '等待 ROS2 连接...'}
                </p>
              </div>
            )}
          </>
        ) : (
          <div className="camera-placeholder">
            <div className="placeholder-icon">📷</div>
            <p className="placeholder-text">摄像头已关闭</p>
            <p className="placeholder-sub">点击下方按钮开启摄像头画面</p>
          </div>
        )}
      </div>

      <div className="camera-controls">
        <button
          className={`btn ${isCameraOn ? 'btn-danger' : 'btn-primary'}`}
          onClick={handleToggleCamera}
        >
          {isCameraOn ? '⏹ 关闭画面' : '● 开启画面'}
        </button>
        {isCameraOn && (
          <button className="btn btn-secondary" onClick={handleFullscreen}>
            {isFullscreen ? '⛶ 退出全屏' : '⛶ 全屏'}
          </button>
        )}
      </div>
    </div>
  );
};

export default CameraPanel;
