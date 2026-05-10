import React from 'react';
import { useAppStore } from '../store';

/** 设置对话框 - 配置模型和检测参数 */
const SettingsDialog: React.FC = () => {
  const {
    showSettings,
    setShowSettings,
    modelName,
    setModelName,
    confidenceThreshold,
    setConfidenceThreshold,
  } = useAppStore();

  if (!showSettings) return null;

  return (
    <div className="dialog-overlay" onClick={() => setShowSettings(false)}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h2>⚙️ 系统设置</h2>
          <button
            className="dialog-close"
            onClick={() => setShowSettings(false)}
          >
            ✕
          </button>
        </div>

        <div className="dialog-body">
          {/* 模型选择 */}
          <div className="setting-group">
            <label className="setting-label">Ollama 模型</label>
            <select
              className="setting-select"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            >
              <option value="gemma4:e2b">Gemma 4 (e2b)</option>
              <option value="gemma4:2b">Gemma 4 (2b)</option>
              <option value="llama3.2:3b">Llama 3.2 (3b)</option>
              <option value="llava">LLaVA (多模态)</option>
              <option value="qwen2.5:7b">Qwen 2.5 (7b)</option>
            </select>
            <p className="setting-hint">选择用于对话的 Ollama 模型</p>
          </div>

          {/* 置信度阈值 */}
          <div className="setting-group">
            <label className="setting-label">
              检测置信度阈值: {confidenceThreshold.toFixed(1)}
            </label>
            <input
              type="range"
              className="setting-range"
              min="0.1"
              max="0.9"
              step="0.1"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
            />
            <p className="setting-hint">
              值越高，检测结果越精确但可能漏检；值越低，检测越多但可能有误检
            </p>
          </div>

          {/* ROS Bridge 地址 */}
          <div className="setting-group">
            <label className="setting-label">ROS Bridge WebSocket 地址</label>
            <input
              type="text"
              className="setting-input"
              value="ws://localhost:9090"
              readOnly
            />
            <p className="setting-hint">
              连接 rosbridge_server 的 WebSocket 地址
            </p>
          </div>

          {/* 系统信息 */}
          <div className="setting-group">
            <label className="setting-label">系统信息</label>
            <div className="setting-info">
              <div className="info-row">
                <span>前端版本</span>
                <span>v0.1.0</span>
              </div>
              <div className="info-row">
                <span>后端框架</span>
                <span>ROS2 + Ollama</span>
              </div>
              <div className="info-row">
                <span>检测引擎</span>
                <span>YOLOv8n (ONNX)</span>
              </div>
            </div>
          </div>
        </div>

        <div className="dialog-footer">
          <button
            className="btn btn-primary"
            onClick={() => setShowSettings(false)}
          >
            确认
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsDialog;
