import { useState } from 'react';
import axios from 'axios';

export default function AuthPage({ onSuccess, onBack }) {
  const [tab, setTab] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const endpoint = tab === 'login' ? '/auth/login' : '/auth/register';
      const { data } = await axios.post(endpoint, { email, password });
      onSuccess(data.access_token, {
        user_id: data.user_id,
        email: data.email,
        ntrp_level: data.ntrp_level,
      });
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 202) {
        setError('注册成功！请检查邮箱确认后再登录。');
      } else {
        setError(detail || '操作失败，请重试');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay">
      <div className="auth-card">
        <button className="auth-back-btn" onClick={onBack}>← 返回</button>
        <div className="auth-logo">教</div>
        <h1 className="auth-title">AI 网球教练</h1>
        <div className="auth-tabs">
          <button className={`auth-tab ${tab === 'login' ? 'active' : ''}`} onClick={() => setTab('login')}>登录</button>
          <button className={`auth-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => setTab('register')}>注册</button>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <input className="auth-input" type="email" placeholder="邮箱" value={email} onChange={e => setEmail(e.target.value)} required />
          <input className="auth-input" type="password" placeholder="密码（至少6位）" value={password} onChange={e => setPassword(e.target.value)} required minLength={6} />
          {error && <div className="auth-error">{error}</div>}
          <button className="auth-submit-btn" type="submit" disabled={loading}>
            {loading ? '请稍候…' : (tab === 'login' ? '登录' : '注册')}
          </button>
        </form>
        <p className="auth-hint">登录后可跨设备保存对话记忆</p>
      </div>
    </div>
  );
}
