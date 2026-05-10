import React from 'react';
import CameraPanel from './components/CameraPanel';
import ChatPanel from './components/ChatPanel';
import StatusBar from './components/StatusBar';
import SettingsDialog from './components/SettingsDialog';
import { useAppStore } from './store';
import { useRosbridge } from './hooks/useRosbridge';
import { useDetections } from './hooks/useDetections';

/** 主应用组件 */
const App: React.FC = () => {
  const { showSettings, setShowSettings, rosConnection } = useAppStore();
  const { publishMessage } = useRosbridge();

  // 启动检测数据管理（真实数据或模拟数据）
  useDetections();

  return (
    <div className="app">
      {/* 顶部导航栏 */}
      <header className="app-header">
        <div className="header-left">
          <span className="header-logo">🔴</span>
          <h1 className="header-title">ROS-Chat AI 视觉对话系统</h1>
        </div>
        <div className="header-right">
          <span className={`connection-status ${rosConnection}`}>
            <span className="status-dot" />
            {rosConnection === 'connected'
              ? '已连接'
              : rosConnection === 'connecting'
              ? '连接中...'
              : '未连接'}
          </span>
          <button
            className="btn btn-icon"
            onClick={() => setShowSettings(true)}
            title="设置"
          >
            ⚙️
          </button>
        </div>
      </header>

      {/* 主内容区域 */}
      <main className="app-main">
        {/* 左侧面板：摄像头画面（含实时检测框叠加） */}
        <div className="left-panel">
          <CameraPanel />
        </div>

        {/* 右侧面板：AI 对话 */}
        <div className="right-panel">
          <ChatPanel publishFn={publishMessage} />
        </div>
      </main>

      {/* 底部状态栏 */}
      <StatusBar />

      {/* 设置对话框 */}
      <SettingsDialog />
    </div>
  );
};

export default App;
