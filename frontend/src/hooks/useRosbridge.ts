import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '../store';

/**
 * ROS 消息类型定义（rosbridge 协议）
 */
interface RosMessage {
  op: string;           // 操作类型: 'subscribe' | 'unsubscribe' | 'publish' | 'advertise'
  topic?: string;       // 话题名称
  type?: string;        // 消息类型
  msg?: any;            // 消息内容
  id?: string;          // 消息ID
}

/**
 * ROS2 WebSocket 连接 Hook
 * 通过 rosbridge 协议与 ROS2 后端通信
 * 内部自动管理连接生命周期，无需外部调用 connect()
 */
export function useRosbridge() {
  const {
    rosConnection,
    setRosConnection,
    setDetections,
    addMessage,
    setProcessing,
    updateSystemStatus,
    setRosImageData,
  } = useAppStore();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const connectCalledRef = useRef(false);

  // 使用 ref 存储 store actions，避免闭包捕获过期值
  const storeActionsRef = useRef({ setRosConnection, setDetections, addMessage, setProcessing, updateSystemStatus, setRosImageData });
  storeActionsRef.current = { setRosConnection, setDetections, addMessage, setProcessing, updateSystemStatus, setRosImageData };

  /**
   * 发送 ROS 操作消息
   */
  const sendRosMessage = useCallback((msg: RosMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  /**
   * 订阅话题
   */
  const subscribeTopic = useCallback((topic: string, type: string) => {
    sendRosMessage({ op: 'subscribe', topic, type });
    console.log(`[ROS] Subscribed to ${topic} (${type})`);
  }, [sendRosMessage]);

  /**
   * 取消订阅话题
   */
  const unsubscribeTopic = useCallback((topic: string) => {
    sendRosMessage({ op: 'unsubscribe', topic });
    console.log(`[ROS] Unsubscribed from ${topic}`);
  }, [sendRosMessage]);

  // 使用 Set 跟踪已广告的话题，避免重复广告
  const advertisedTopicsRef = useRef<Set<string>>(new Set());

  /**
   * 发布消息到话题（自动先广告话题类型）
   */
  const publishMessage = useCallback((topic: string, type: string, msg: any) => {
    // 如果话题尚未广告，先发送 advertise 操作
    if (!advertisedTopicsRef.current.has(topic)) {
      sendRosMessage({ op: 'advertise', topic, type });
      advertisedTopicsRef.current.add(topic);
      console.log(`[ROS] Advertised ${topic} (${type})`);
    }
    sendRosMessage({ op: 'publish', topic, type, msg });
    console.log(`[ROS] Published to ${topic}:`, msg);
  }, [sendRosMessage]);

  /**
   * 处理接收到的 ROS 消息
   */
  const handleRosMessage = useCallback((data: any) => {
    const { op, topic, msg } = data;
    const actions = storeActionsRef.current;

    if (op === 'publish') {
      switch (topic) {
        case '/vision/detection':
          if (msg?.detections) {
            const detections = msg.detections.map((d: any) => ({
              class_name: d.results?.[0]?.hypothesis?.class_id || 'unknown',
              confidence: d.results?.[0]?.hypothesis?.score || 0,
              bbox: [
                d.bbox?.center?.position?.x - (d.bbox?.size_x || 0) / 2 || 0,
                d.bbox?.center?.position?.y - (d.bbox?.size_y || 0) / 2 || 0,
                d.bbox?.size_x || 0,
                d.bbox?.size_y || 0,
              ] as [number, number, number, number],
            }));
            actions.setDetections(detections);
          }
          break;

        case '/chat_output':
          if (msg?.data) {
            const assistantMsg = {
              id: `msg_${Date.now()}`,
              role: 'assistant' as const,
              content: msg.data,
              timestamp: Date.now(),
            };
            actions.addMessage(assistantMsg);
            actions.setProcessing(false);
          }
          break;

        case '/vision/detection_text':
          if (msg?.data) {
            actions.updateSystemStatus({ detectionText: msg.data });
          }
          break;

        case '/camera/image_raw':
          if (msg) {
            actions.updateSystemStatus({ camera: 'connected' });
          }
          break;

        case '/camera/image_web':
          if (msg?.data) {
            actions.updateSystemStatus({ camera: 'connected' });
            // 直接使用 base64 编码的 JPEG 数据（由 camera_node 编码）
            // 格式: data:image/jpeg;base64,<base64_string>
            const base64Data = msg.data;
            if (typeof base64Data === 'string' && base64Data.length > 0) {
              actions.setRosImageData(`data:image/jpeg;base64,${base64Data}`);
            }
          }
          break;
      }
    }
  }, []);

  /**
   * 建立 WebSocket 连接（使用 ref 存储，确保引用稳定）
   */
  const connectRef = useRef((url: string = 'ws://localhost:9090') => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[ROS] Already connected');
      return;
    }

    const actions = storeActionsRef.current;
    actions.setRosConnection('connecting');
    console.log(`[ROS] Connecting to ${url}...`);

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('[ROS] Connected to rosbridge');
        actions.setRosConnection('connected');
        actions.updateSystemStatus({ rosbridge: 'connected' });

        // 订阅所有需要的话题
        subscribeTopic('/vision/detection', 'vision_msgs/Detection2DArray');
        subscribeTopic('/chat_output', 'std_msgs/String');
        subscribeTopic('/vision/detection_text', 'std_msgs/String');
        subscribeTopic('/camera/image_raw', 'sensor_msgs/Image');
        subscribeTopic('/camera/image_web', 'std_msgs/String');

        // 心跳检测：定期检查 WebSocket 连接状态
        heartbeatTimerRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            console.debug('[ROS] Heartbeat check OK');
          } else if (wsRef.current?.readyState === WebSocket.CLOSED) {
            console.warn('[ROS] Heartbeat: connection closed');
            const a = storeActionsRef.current;
            a.setRosConnection('disconnected');
            a.updateSystemStatus({ rosbridge: 'disconnected' });
            if (heartbeatTimerRef.current) {
              clearInterval(heartbeatTimerRef.current);
              heartbeatTimerRef.current = null;
            }
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleRosMessage(data);
        } catch (e) {
          console.error('[ROS] Failed to parse message:', e);
        }
      };

      ws.onclose = (event) => {
        console.log(`[ROS] Disconnected (code: ${event.code})`);
        const a = storeActionsRef.current;
        a.setRosConnection('disconnected');
        a.updateSystemStatus({ rosbridge: 'disconnected' });
        wsRef.current = null;

        if (heartbeatTimerRef.current) {
          clearInterval(heartbeatTimerRef.current);
          heartbeatTimerRef.current = null;
        }

        // 自动重连（3 秒后）
        reconnectTimerRef.current = setTimeout(() => {
          console.log('[ROS] Attempting reconnection...');
          connectRef.current(url);
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error('[ROS] WebSocket error:', error);
        const a = storeActionsRef.current;
        a.setRosConnection('error');
        a.updateSystemStatus({ rosbridge: 'error' });
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[ROS] Failed to create WebSocket:', error);
      const a = storeActionsRef.current;
      a.setRosConnection('error');
      a.updateSystemStatus({ rosbridge: 'error' });
    }
  });

  /**
   * 断开连接
   */
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      unsubscribeTopic('/vision/detection');
      unsubscribeTopic('/chat_output');
      unsubscribeTopic('/vision/detection_text');
      unsubscribeTopic('/camera/image_raw');
      unsubscribeTopic('/camera/image_web');

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
    const actions = storeActionsRef.current;
    actions.setRosConnection('disconnected');
    actions.updateSystemStatus({ rosbridge: 'disconnected' });
    console.log('[ROS] Disconnected');
  }, [unsubscribeTopic]);

  // 自动连接（仅在组件挂载时执行一次）
  useEffect(() => {
    if (!connectCalledRef.current) {
      connectCalledRef.current = true;
      connectRef.current();
    }
  }, []);

  // 自动重连（当 rosConnection 变为 disconnected/error 时触发）
  useEffect(() => {
    if (connectCalledRef.current && (rosConnection === 'disconnected' || rosConnection === 'error')) {
      reconnectTimerRef.current = setTimeout(() => {
        console.log('[ROS] Auto reconnecting...');
        connectRef.current();
      }, 3000);
    }
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [rosConnection]);

  // 清理（组件卸载时断开连接）
  useEffect(() => {
    return () => {
      if (wsRef.current) {
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
    };
  }, []);

  return {
    connect: connectRef.current,
    disconnect,
    publishMessage,
    isConnected: rosConnection === 'connected',
  };
}
