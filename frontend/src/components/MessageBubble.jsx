import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function formatTime(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function CopyIcon({ copied }) {
  if (copied) {
    return (
      <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 8l4 4 8-8" />
      </svg>
    );
  }
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="5" width="9" height="9" rx="1.5" />
      <path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" />
    </svg>
  );
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'assistant-row'}`}>
      {!isUser && <div className="avatar coach-avatar-mono">教</div>}
      <div className={`bubble-wrapper ${isUser ? 'user-wrapper' : 'assistant-wrapper'}`}>
        <div className={`bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
              {message.isUncertain && (
                <div className="uncertain-badge">
                  ⚠️ 知识库中没有完全匹配的内容，建议进一步确认
                </div>
              )}
              {message.isError && (
                <div className="error-badge">
                  ❌ 连接出现问题，请检查后端服务
                </div>
              )}
            </>
          )}
        </div>
        <div className={`message-meta ${isUser ? 'meta-right' : 'meta-left'}`}>
          {message.timestamp && (
            <span className="message-time">{formatTime(message.timestamp)}</span>
          )}
          {!isUser && (
            <button
              className={`copy-btn ${copied ? 'copied' : ''}`}
              onClick={handleCopy}
              title="复制"
            >
              <CopyIcon copied={copied} />
              <span>{copied ? '已复制' : '复制'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
