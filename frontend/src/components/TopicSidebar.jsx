const TOPICS = [
  { key: '技术', icon: '🎾', label: '技术指导' },
  { key: '战术', icon: '♟️', label: '战术策略' },
  { key: '训练', icon: '💪', label: '训练计划' },
  { key: '装备', icon: '🛒', label: '装备选择' },
  { key: '其他', icon: '💬', label: '其他问题' },
];

export default function TopicSidebar({ activeTopic, onTopicSelect, userLevel, onChangeLevel }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="coach-monogram">教</div>
        <div className="sidebar-header-text">
          <div className="coach-name">AI 网球教练</div>
          <div className="coach-subtitle">20年执教经验</div>
        </div>
        {/* Mobile-only level badge */}
        <button className="mobile-level-badge" onClick={onChangeLevel}>
          <span>{userLevel ? `NTRP ${userLevel}` : '设置水平'}</span>
        </button>
      </div>
      <nav className="topic-nav">
        <div className="topic-nav-title">话题分类</div>
        {TOPICS.map(t => (
          <button
            key={t.key}
            className={`topic-btn ${activeTopic === t.key ? 'active' : ''}`}
            onClick={() => onTopicSelect(t.key)}
          >
            <span className="topic-icon">{t.icon}</span>
            <span className="topic-label">{t.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="level-display">
          {userLevel ? `NTRP ${userLevel}` : '水平未设置'}
        </div>
        <button className="change-level-btn" onClick={onChangeLevel}>
          修改水平
        </button>
      </div>
    </aside>
  );
}
