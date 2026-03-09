const LEVELS = [
  { value: '2.0', ntrp: '2.0', name: '初学入门', desc: '刚开始学习，能把球打过网' },
  { value: '2.5', ntrp: '2.5', name: '基础建立', desc: '短距离对拉，移动击球困难' },
  { value: '3.0', ntrp: '3.0', name: '稳定成长', desc: '能打完整比赛，正反手稳定' },
  { value: '3.5', ntrp: '3.5', name: '战术意识', desc: '有一定武器，能使用基本战术' },
  { value: '4.0', ntrp: '4.0', name: '全面提升', desc: '技术较全面，有明确得分模式' },
  { value: '4.5', ntrp: '4.5', name: '精英进阶', desc: '有突出特长，比赛经验丰富' },
];

export default function LevelSelector({ onSelect }) {
  return (
    <div className="level-selector-overlay">
      <div className="level-selector-lines" />
      <div className="level-selector-card">
        <div className="level-selector-tagline">AI 网球教练</div>
        <h1>你的网球水平<br />在哪个阶段？</h1>
        <p>根据你的 NTRP 评级，我将为你调整教学深度与风格</p>
        <div className="level-grid">
          {LEVELS.map(l => (
            <button key={l.value} className="level-btn" onClick={() => onSelect(l.value)}>
              <span className="level-ntrp">{l.ntrp}</span>
              <span className="level-name">{l.name}</span>
              <span className="level-desc">{l.desc}</span>
            </button>
          ))}
        </div>
        <button className="skip-btn" onClick={() => onSelect(null)}>
          暂时跳过
        </button>
      </div>
    </div>
  );
}
