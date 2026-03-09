import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'assistant-row'}`}>
      {!isUser && <div className="avatar">🎾</div>}
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
    </div>
  );
}
