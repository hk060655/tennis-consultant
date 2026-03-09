import { useRef, useEffect, useState } from 'react';
import MessageBubble from './MessageBubble';

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
      <path d="M18 10L2 3l3.5 7L2 17l16-7z" fill="currentColor" />
    </svg>
  );
}

export default function ChatWindow({ messages, isLoading, onSendMessage }) {
  const [inputText, setInputText] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isLoading) return;
    setInputText('');
    onSendMessage(text);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <main className="chat-window">
      <div className="chat-header">
        <span className="chat-header-title">与 AI 教练对话</span>
        <span className="chat-header-hint">Enter 发送 · Shift+Enter 换行</span>
      </div>
      <div className="message-list">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {isLoading && (
          <div className="message-row assistant-row">
            <div className="avatar">🎾</div>
            <div className="bubble assistant-bubble loading-bubble">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          className="chat-input"
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的网球问题…"
          rows={2}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="send-btn"
          disabled={isLoading || !inputText.trim()}
        >
          <SendIcon />
        </button>
      </form>
    </main>
  );
}
