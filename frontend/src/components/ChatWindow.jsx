import { useRef, useEffect, useState } from 'react';
import MessageBubble from './MessageBubble';

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
      <path d="M18 10L2 3l3.5 7L2 17l16-7z" fill="currentColor" />
    </svg>
  );
}

function NewChatIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3H5a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-7" />
      <path d="M15.5 2.5a2.121 2.121 0 013 3L11 13H8v-3l7.5-7.5z" />
    </svg>
  );
}

export default function ChatWindow({ messages, isLoading, onSendMessage, onNewConversation }) {
  const [inputText, setInputText] = useState('');
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }, [inputText]);

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
        <div className="chat-header-actions">
          <button
            className="new-chat-btn"
            onClick={onNewConversation}
            title="新对话"
          >
            <NewChatIcon />
            <span>新对话</span>
          </button>
          <span className="chat-header-hint">Enter 发送 · Shift+Enter 换行</span>
        </div>
      </div>
      <div className="message-list">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {isLoading && (
          <div className="message-row assistant-row">
            <div className="avatar coach-avatar-mono">教</div>
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
          ref={textareaRef}
          className="chat-input"
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的网球问题…"
          rows={1}
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
