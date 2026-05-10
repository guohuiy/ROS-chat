import { useCallback } from 'react';
import { useAppStore } from '../store';

/**
 * 摄像头控制 Hook
 * 不再使用浏览器本地摄像头（getUserMedia），
 * 改为通过 rosbridge 订阅 ROS2 端 camera_node 发布的压缩图像话题
 * (/camera/image_raw/compressed) 来获取摄像头画面。
 *
 * 摄像头开启/关闭仅控制前端是否显示画面，
 * 实际的摄像头驱动由 ROS2 后端的 camera_node 负责。
 */
export function useCamera() {
  const { isCameraOn, toggleCamera, updateSystemStatus, rosConnection } = useAppStore();

  /**
   * 切换摄像头显示状态
   * 注意：实际的摄像头由 ROS2 后端 camera_node 驱动，
   * 前端仅控制是否显示接收到的画面。
   */
  const handleToggleCamera = useCallback(() => {
    if (isCameraOn) {
      // 关闭显示
      toggleCamera();
      updateSystemStatus({ camera: 'disconnected' });
    } else {
      // 开启显示
      toggleCamera();
      if (rosConnection === 'connected') {
        updateSystemStatus({ camera: 'connected' });
      } else {
        updateSystemStatus({ camera: 'disconnected' });
      }
    }
  }, [isCameraOn, toggleCamera, updateSystemStatus, rosConnection]);

  return {
    isCameraOn,
    toggleCamera: handleToggleCamera,
  };
}
