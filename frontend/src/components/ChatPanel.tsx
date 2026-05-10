import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAppStore } from '../store';
import { useChat } from '../hooks/useChat';
import ReactMarkdown from 'react-markdown';

interface ChatPanelProps {
  publishFn?: (topic: string, type: string, msg: any) => void;
}

/** AI 对话面板 - 聊天交互界面 */
const ChatPanel: React.FC<ChatPanelProps> = ({ publishFn }) => {
  const { messages, sendMessage, isProcessing } = useChat();
  const { isCameraOn, detections } = useAppStore();
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 自动滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 发送消息
  const handleSend = useCallback(() => {
    if (!inputValue.trim() || isProcessing) return;
    sendMessage(inputValue, publishFn);
    setInputValue('');
  }, [inputValue, isProcessing, sendMessage, publishFn]);

  // 键盘事件
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // 自动调整输入框高度
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInputValue(e.target.value);
      const textarea = e.target;
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    },
    []
  );

  // 格式化时间
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  };

  return (
    <div className="panel chat-panel">
      <div className="panel-header">
        <span className="panel-icon">💬</span>
        <span className="panel-title">AI 对话</span>
        <div className="panel-header-right">
          {isCameraOn ? (
            <span className="vision-indicator active" title="AI 可看到摄像头画面">
              📷 视觉模式
            </span>
          ) : (
            <span className="vision-indicator inactive" title="纯文本聊天模式">
              💭 文本模式
            </span>
          )}
        </div>
      </div>

      {/* 消息列表 */}
      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message ${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? '👤' : msg.role === 'assistant' ? '🤖' : 'ℹ️'}
            </div>
            <div className="message-content-wrapper">
              <div className="message-header">
                <span className="message-role">
                  {msg.role === 'user' ? '你' : msg.role === 'assistant' ? 'AI 助手' : '系统'}
                </span>
                <span className="message-time">{formatTime(msg.timestamp)}</span>
              </div>
              <div className="message-content">
                {msg.role === 'assistant' || msg.role === 'system' ? (
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                ) : (
                  <p>{msg.content}</p>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* 处理中指示器 */}
        {isProcessing && (
          <div className="chat-message assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-content-wrapper">
              <div className="message-header">
                <span className="message-role">AI 助手</span>
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder={
              isCameraOn
                ? '📷 输入消息，AI 可看到摄像头画面...'
                : '💭 输入消息...'
            }
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isProcessing}
          />
          <button
            className="btn btn-send"
            onClick={handleSend}
            disabled={!inputValue.trim() || isProcessing}
          >
            {isProcessing ? '⏳' : '发送'}
          </button>
        </div>
        <div className="chat-input-hint">
          <span>Enter 发送 · Shift+Enter 换行</span>
          {isCameraOn && detections.length > 0 && (
            <span className="detection-hint">
              检测到 {detections.length} 个对象
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
