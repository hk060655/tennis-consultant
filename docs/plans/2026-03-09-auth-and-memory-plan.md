# Auth + Memory System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add optional email/password login with cross-device persistent coach notes, without breaking the existing anonymous user flow.

**Architecture:** Backend-mediated auth via Supabase (Python client). All Supabase calls stay in FastAPI. Frontend stores JWT in localStorage and sends it as a Bearer token. `/chat` handles both anonymous (no token) and authenticated (token present) requests. After each authenticated reply, an asyncio background task extracts a structured user profile (`coach_notes`) from the conversation and writes it back to Supabase.

**Tech Stack:** `supabase==2.x` (Python), Supabase Auth + PostgreSQL, React (no new frontend SDK), `python-jose` for JWT decode if needed.

---

## Task 1: Supabase Project Setup (Manual)

**Files:** None (external setup)

**Step 1: Create Supabase project**

Go to https://supabase.com → New Project. Note down:
- Project URL (looks like `https://xxxx.supabase.co`)
- `anon` key (public)
- `service_role` key (secret — used by backend only, never commit)

**Step 2: Create tables in Supabase SQL Editor**

Run this SQL:

```sql
-- User profiles table
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  ntrp_level TEXT,
  coach_notes TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation history table
CREATE TABLE conversation_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast user history lookup
CREATE INDEX idx_conversation_history_user_id
  ON conversation_history(user_id, created_at DESC);

-- Auto-update updated_at on user_profiles
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_profiles_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

**Step 3: Disable RLS on both tables** (backend uses service_role key which bypasses RLS anyway, but disabling avoids confusion)

In Supabase Dashboard → Table Editor → each table → RLS → Disable.

**Step 4: Add env vars to `.env`**

```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # service_role key
```

---

## Task 2: Backend Dependencies + Config

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/config.py`

**Step 1: Add supabase to requirements**

```text
# Add to backend/requirements.txt
supabase==2.10.0
```

**Step 2: Add Supabase config fields**

In `backend/config.py`, add two new optional fields:

```python
from typing import Optional

class Settings(BaseSettings):
    # ... existing fields ...
    supabase_url: Optional[str] = None
    supabase_service_key: Optional[str] = None
```

Both are `Optional` so the app still starts without them (anonymous-only mode).

**Step 3: Install and verify**

```bash
pip3 install supabase==2.10.0
python3 -c "from supabase import create_client; print('ok')"
```

Expected: `ok`

**Step 4: Commit**

```bash
git add backend/requirements.txt backend/config.py
git commit -m "feat: add supabase dependency and config fields"
```

---

## Task 3: Supabase Client Module

**Files:**
- Create: `backend/db/supabase_client.py`
- Create: `backend/db/__init__.py`

**Step 1: Create the module**

```python
# backend/db/__init__.py
# (empty)
```

```python
# backend/db/supabase_client.py
import logging
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Returns Supabase client, or None if not configured."""
    global _client
    if _client is not None:
        return _client
    from backend.config import settings
    if not settings.supabase_url or not settings.supabase_service_key:
        return None
    _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def is_supabase_enabled() -> bool:
    return get_supabase() is not None
```

**Step 2: Verify import**

```bash
cd /path/to/tennis_consultant
python3 -c "from backend.db.supabase_client import get_supabase; print(get_supabase())"
```

Expected: prints the client object (not None) if `.env` is set, or `None` if not.

**Step 3: Commit**

```bash
git add backend/db/
git commit -m "feat: add supabase client module"
```

---

## Task 4: Auth Schemas + Endpoints

**Files:**
- Modify: `backend/models/schemas.py`
- Create: `backend/routers/auth.py`
- Create: `backend/routers/__init__.py`
- Modify: `backend/main.py`

**Step 1: Add auth schemas to `schemas.py`**

```python
# Add to backend/models/schemas.py

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    user_id: str
    email: str
    ntrp_level: Optional[str] = None

class UserProfile(BaseModel):
    user_id: str
    email: str
    ntrp_level: Optional[str] = None
    coach_notes: str = ""
```

**Step 2: Create `backend/routers/__init__.py`** (empty)

**Step 3: Create `backend/routers/auth.py`**

```python
# backend/routers/auth.py
import logging
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from backend.models.schemas import RegisterRequest, LoginRequest, AuthResponse, UserProfile
from backend.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _require_supabase():
    sb = get_supabase()
    if sb is None:
        raise HTTPException(status_code=503, detail="Auth not configured")
    return sb


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    sb = _require_supabase()
    try:
        res = sb.auth.sign_up({"email": req.email, "password": req.password})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not res.user:
        raise HTTPException(status_code=400, detail="Registration failed")

    user_id = str(res.user.id)
    # Insert profile row
    sb.table("user_profiles").insert({
        "id": user_id,
        "email": req.email,
        "coach_notes": "",
    }).execute()

    token = res.session.access_token if res.session else ""
    return AuthResponse(
        access_token=token,
        user_id=user_id,
        email=req.email,
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    sb = _require_supabase()
    try:
        res = sb.auth.sign_in_with_password({"email": req.email, "password": req.password})
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not res.user or not res.session:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(res.user.id)
    # Fetch profile
    profile = sb.table("user_profiles").select("ntrp_level").eq("id", user_id).single().execute()
    ntrp = profile.data.get("ntrp_level") if profile.data else None

    return AuthResponse(
        access_token=res.session.access_token,
        user_id=user_id,
        email=req.email,
        ntrp_level=ntrp,
    )


@router.get("/me", response_model=UserProfile)
async def me(authorization: Optional[str] = Header(None)):
    sb = _require_supabase()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        user_res = sb.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = str(user_res.user.id)
    profile = sb.table("user_profiles").select("*").eq("id", user_id).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return UserProfile(
        user_id=user_id,
        email=profile.data["email"],
        ntrp_level=profile.data.get("ntrp_level"),
        coach_notes=profile.data.get("coach_notes", ""),
    )
```

**Step 4: Register router in `main.py`**

Add near the top imports:
```python
from backend.routers.auth import router as auth_router
```

Add after `app = FastAPI(...)` and middleware setup:
```python
app.include_router(auth_router)
```

**Step 5: Manual test**

Start the server and open http://localhost:8000/docs. Verify `/auth/register`, `/auth/login`, `/auth/me` appear.

Test register:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234"}'
```
Expected: JSON with `access_token`, `user_id`, `email`.

**Step 6: Commit**

```bash
git add backend/routers/ backend/models/schemas.py backend/main.py
git commit -m "feat: add /auth/register, /auth/login, /auth/me endpoints"
```

---

## Task 5: Auth Helper — Extract User from Token

**Files:**
- Create: `backend/auth_utils.py`

**Step 1: Create helper**

```python
# backend/auth_utils.py
from typing import Optional, Tuple
from backend.db.supabase_client import get_supabase


def get_user_from_token(authorization: Optional[str]) -> Optional[Tuple[str, str]]:
    """
    Given an Authorization header value, returns (user_id, email) or None.
    Returns None for anonymous requests or invalid tokens.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    sb = get_supabase()
    if sb is None:
        return None
    try:
        res = sb.auth.get_user(token)
        return str(res.user.id), res.user.email
    except Exception:
        return None
```

**Step 2: Commit**

```bash
git add backend/auth_utils.py
git commit -m "feat: add auth_utils helper for token extraction"
```

---

## Task 6: Profile Extractor (Async Background Task)

**Files:**
- Create: `backend/rag/profiler.py`

**Step 1: Create profiler**

```python
# backend/rag/profiler.py
import logging
from backend.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

PROFILER_SYSTEM = """你是一个助手，负责从网球教练与学员的对话中提炼学员画像。
请输出简洁的要点列表（用"-"开头），涵盖：
- 学员的技术弱点和问题
- 已经给出过的训练建议
- 学员的学习风格和偏好
- 近期进展或改善
- 其他值得记住的个人信息（如惯用手、训练频率等）

如果信息不足，只输出已知内容。不要编造信息。保持简洁，不超过200字。"""


async def update_coach_notes(user_id: str, recent_messages: list[dict], existing_notes: str):
    """
    Async task: summarize recent conversation into coach_notes and update Supabase.
    Called as a background task — must not raise.
    """
    sb = get_supabase()
    if sb is None:
        return
    try:
        from backend.config import settings
        from openai import OpenAI
        client = OpenAI(api_key=settings.ai_builder_token, base_url=settings.ai_builder_base_url)

        # Build context: existing notes + recent messages
        convo_text = "\n".join(
            f"{'学员' if m['role'] == 'user' else '教练'}: {m['content']}"
            for m in recent_messages[-20:]
        )
        existing_section = f"现有学员档案：\n{existing_notes}\n\n" if existing_notes else ""
        user_prompt = f"{existing_section}最新对话记录：\n{convo_text}\n\n请更新学员画像："

        response = client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=300,
            messages=[
                {"role": "system", "content": PROFILER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )
        new_notes = response.choices[0].message.content.strip()
        if new_notes:
            sb.table("user_profiles").update({"coach_notes": new_notes}).eq("id", user_id).execute()
            logger.info(f"[PROFILER] Updated coach_notes for user {user_id[:8]}...")
    except Exception as e:
        logger.warning(f"[PROFILER] Failed to update coach_notes: {e}")
```

**Step 2: Commit**

```bash
git add backend/rag/profiler.py
git commit -m "feat: add async profiler to extract coach_notes from conversation"
```

---

## Task 7: Update `/chat` for Authenticated Users

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/rag/generator.py`

**Step 1: Update `generator.py` to accept `coach_notes`**

In `generate()` method signature, add `coach_notes: str = ""`:

```python
def generate(
    self,
    user_message: str,
    retrieved_chunks: list[SourceChunk],
    user_level: Optional[str],
    conversation_history: list[dict],
    is_uncertain: bool,
    coach_notes: str = "",
) -> str:
```

In the body, inject memory into `context_injection` if `coach_notes` is non-empty:

```python
memory_section = ""
if coach_notes:
    memory_section = (
        f"<user_memory>\n"
        f"以下是你对这位学员的了解，请在回答中自然地考虑这些信息：\n"
        f"{coach_notes}\n"
        f"</user_memory>\n\n"
    )

context_injection = (
    f"{memory_section}"
    f"<background_knowledge>\n"
    f"{level_info}\n\n"
    f"{knowledge_context}\n"
    f"</background_knowledge>\n\n"
    f"重要：请将以上background_knowledge作为你的专业知识背景来回答，"
    f"不要在回答中引用、提及或暗示任何「知识片段」「来源」「文档」等字样，"
    f"直接以教练身份自然地给出建议。"
)
```

**Step 2: Update `/chat` in `main.py`**

Add imports at top:
```python
from fastapi import Header
from typing import Optional
from backend.auth_utils import get_user_from_token
from backend.rag.profiler import update_coach_notes
```

Replace the `chat()` function:

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, authorization: Optional[str] = Header(None)):
    # --- Resolve user identity ---
    auth_user = get_user_from_token(authorization)
    is_authenticated = auth_user is not None

    if is_authenticated:
        user_id, _ = auth_user
    else:
        user_id = request.user_id

    level_str = request.user_level.value if request.user_level else None

    # --- For authenticated users: load profile + persistent history ---
    coach_notes = ""
    if is_authenticated:
        sb = get_supabase()
        if sb:
            # Load profile (coach_notes, ntrp_level)
            profile_res = sb.table("user_profiles").select("coach_notes, ntrp_level").eq("id", user_id).single().execute()
            if profile_res.data:
                coach_notes = profile_res.data.get("coach_notes") or ""
                if not level_str:
                    level_str = profile_res.data.get("ntrp_level")

            # Load persistent conversation history (last 10 turns = 20 rows)
            hist_res = sb.table("conversation_history") \
                .select("role, content") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(20) \
                .execute()
            if hist_res.data:
                db_history = list(reversed(hist_res.data))
            else:
                db_history = []

            # Merge with in-memory (in-memory takes precedence for current session)
            history = db_history
        else:
            history = conversation_store[user_id]
    else:
        history = conversation_store[user_id]

    # --- RAG retrieval ---
    t0 = time.perf_counter()
    chunks, is_uncertain = retriever.retrieve(
        query=request.message,
        user_level=level_str,
        top_k=settings.top_k,
    )
    t_rag = time.perf_counter() - t0

    # --- LLM generation ---
    try:
        t1 = time.perf_counter()
        reply = generator.generate(
            user_message=request.message,
            retrieved_chunks=chunks,
            user_level=level_str,
            conversation_history=history,
            is_uncertain=is_uncertain,
            coach_notes=coach_notes,
        )
        t_llm = time.perf_counter() - t1
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise HTTPException(status_code=502, detail="AI service unavailable")

    t_total = time.perf_counter() - t0
    logger.info(f"[LATENCY] total={t_total:.2f}s  rag={t_rag:.2f}s  llm={t_llm:.2f}s")

    # --- Persist messages for authenticated users ---
    new_messages = [
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": reply},
    ]

    if is_authenticated:
        sb = get_supabase()
        if sb:
            sb.table("conversation_history").insert([
                {"user_id": user_id, "role": m["role"], "content": m["content"]}
                for m in new_messages
            ]).execute()

            # Update ntrp_level in profile if provided in this request
            if request.user_level:
                sb.table("user_profiles").update({"ntrp_level": level_str}).eq("id", user_id).execute()

            # Async background task: update coach_notes
            all_history = history + new_messages
            import asyncio
            asyncio.create_task(update_coach_notes(user_id, all_history, coach_notes))
    else:
        # Anonymous: keep in-memory store
        history.extend(new_messages)
        conversation_store[user_id] = history[-40:]

    return ChatResponse(
        reply=reply,
        sources=chunks,
        user_id=user_id,
        is_uncertain=is_uncertain,
    )
```

**Step 3: Manual test — anonymous flow still works**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"正手怎么练","user_id":"test123"}'
```
Expected: normal reply, no auth errors.

**Step 4: Manual test — authenticated flow**

```bash
# First login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Chat with token
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"我的正手总是打出界","user_id":"ignored_when_authed"}'
```
Expected: reply saved to Supabase, `coach_notes` updated in background.

**Step 5: Commit**

```bash
git add backend/main.py backend/rag/generator.py
git commit -m "feat: update /chat to support auth, persistent history, and coach_notes injection"
```

---

## Task 8: Frontend — Auth State Management

**Files:**
- Modify: `frontend/src/App.jsx`

**Step 1: Add auth state and helpers to `App.jsx`**

Add these helpers at the top (after imports):

```js
function getStoredToken() {
  return localStorage.getItem('tennis_auth_token');
}

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('tennis_auth_user') || 'null');
  } catch { return null; }
}
```

Add state in the component:

```js
const [currentUser, setCurrentUser] = useState(getStoredUser);
const [authToken, setAuthToken] = useState(getStoredToken);
const [showAuthPage, setShowAuthPage] = useState(false);
```

Add login/logout handlers:

```js
const handleLogin = (token, user) => {
  localStorage.setItem('tennis_auth_token', token);
  localStorage.setItem('tennis_auth_user', JSON.stringify(user));
  setAuthToken(token);
  setCurrentUser(user);
  setShowAuthPage(false);
  // If server returned ntrp_level, use it
  if (user.ntrp_level) {
    setUserLevel(user.ntrp_level);
    localStorage.setItem('tennis_user_level', user.ntrp_level);
  }
};

const handleLogout = () => {
  localStorage.removeItem('tennis_auth_token');
  localStorage.removeItem('tennis_auth_user');
  setAuthToken(null);
  setCurrentUser(null);
};
```

Update `sendMessage` to include token when present:

```js
const { data } = await axios.post('/chat', {
  message: messageText,
  user_id: userId,
  user_level: userLevel || undefined,
}, authToken ? {
  headers: { Authorization: `Bearer ${authToken}` }
} : {});
```

Add auth page rendering (before level selector check):

```js
if (showAuthPage) {
  return <AuthPage onSuccess={handleLogin} onBack={() => setShowAuthPage(false)} />;
}
```

Pass auth props to `TopicSidebar`:

```js
<TopicSidebar
  activeTopic={activeTopic}
  onTopicSelect={handleTopicSelect}
  userLevel={userLevel}
  onChangeLevel={() => setShowLevelSelector(true)}
  currentUser={currentUser}
  onLoginClick={() => setShowAuthPage(true)}
  onLogout={handleLogout}
/>
```

**Step 2: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add auth state management to App.jsx"
```

---

## Task 9: Frontend — Auth Page Component

**Files:**
- Create: `frontend/src/components/AuthPage.jsx`

**Step 1: Create the component**

```jsx
// frontend/src/components/AuthPage.jsx
import { useState } from 'react';
import axios from 'axios';

export default function AuthPage({ onSuccess, onBack }) {
  const [tab, setTab] = useState('login'); // 'login' | 'register'
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
      setError(err.response?.data?.detail || '操作失败，请重试');
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
          <button
            className={`auth-tab ${tab === 'login' ? 'active' : ''}`}
            onClick={() => setTab('login')}
          >登录</button>
          <button
            className={`auth-tab ${tab === 'register' ? 'active' : ''}`}
            onClick={() => setTab('register')}
          >注册</button>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            className="auth-input"
            type="email"
            placeholder="邮箱"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <input
            className="auth-input"
            type="password"
            placeholder="密码（至少6位）"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            minLength={6}
          />
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
```

**Step 2: Add auth styles to `App.css`**

```css
/* ════ AUTH PAGE ════ */
.auth-overlay {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--court);
  padding: 32px 24px;
  position: relative;
  overflow: hidden;
}

.auth-overlay::before {
  content: '';
  position: absolute;
  top: -10%; right: -5%;
  width: 500px; height: 500px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(193,68,14,0.15) 0%, transparent 68%);
  pointer-events: none;
}

.auth-card {
  max-width: 400px;
  width: 100%;
  text-align: center;
  animation: selectorIn 0.4s ease-out forwards;
}

.auth-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: none;
  color: rgba(255,255,255,0.4);
  font-family: var(--font-body);
  font-size: 13px;
  cursor: pointer;
  padding: 4px 0 20px;
  transition: color 0.2s;
}
.auth-back-btn:hover { color: rgba(255,255,255,0.7); }

.auth-logo {
  width: 56px; height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--clay) 0%, var(--clay-dark) 100%);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-display);
  font-size: 22px; font-weight: 700; color: #fff;
  margin: 0 auto 14px;
  box-shadow: 0 4px 18px rgba(193,68,14,0.45);
}

.auth-title {
  font-family: var(--font-display);
  font-size: 26px; font-weight: 700;
  color: #fff; margin-bottom: 28px;
}

.auth-tabs {
  display: flex;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 24px;
}

.auth-tab {
  flex: 1;
  padding: 10px;
  background: transparent;
  border: none;
  color: rgba(255,255,255,0.45);
  font-family: var(--font-body);
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.auth-tab.active {
  background: var(--clay);
  color: #fff;
  font-weight: 600;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.auth-input {
  width: 100%;
  padding: 13px 16px;
  background: rgba(255,255,255,0.06);
  border: 1.5px solid rgba(255,255,255,0.12);
  border-radius: 12px;
  color: #fff;
  font-family: var(--font-body);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.auth-input::placeholder { color: rgba(255,255,255,0.3); }
.auth-input:focus { border-color: var(--clay-light); }

.auth-error {
  padding: 10px 14px;
  background: rgba(193,68,14,0.18);
  border: 1px solid rgba(193,68,14,0.4);
  border-radius: 8px;
  color: var(--clay-light);
  font-size: 13px;
  text-align: left;
}

.auth-submit-btn {
  padding: 13px;
  background: var(--clay);
  border: none;
  border-radius: 12px;
  color: #fff;
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s;
  box-shadow: 0 3px 14px rgba(193,68,14,0.38);
  margin-top: 4px;
}

.auth-submit-btn:hover:not(:disabled) {
  background: var(--clay-dark);
  transform: translateY(-1px);
}

.auth-submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.auth-hint {
  margin-top: 20px;
  font-size: 12px;
  color: rgba(255,255,255,0.28);
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/AuthPage.jsx frontend/src/App.css
git commit -m "feat: add AuthPage component with login/register UI"
```

---

## Task 10: Frontend — Login Button in Sidebar

**Files:**
- Modify: `frontend/src/components/TopicSidebar.jsx`
- Modify: `frontend/src/App.css`

**Step 1: Update `TopicSidebar.jsx`**

Add login/user section to the sidebar footer:

```jsx
export default function TopicSidebar({ activeTopic, onTopicSelect, userLevel, onChangeLevel, currentUser, onLoginClick, onLogout }) {
  return (
    <aside className="sidebar">
      {/* ... existing header and nav ... */}
      <div className="sidebar-footer">
        <div className="level-display">
          {userLevel ? `NTRP ${userLevel}` : '水平未设置'}
        </div>
        <button className="change-level-btn" onClick={onChangeLevel}>
          修改水平
        </button>
        <div className="auth-section">
          {currentUser ? (
            <>
              <div className="user-email-display">
                <span className="user-avatar-initial">
                  {currentUser.email[0].toUpperCase()}
                </span>
                <span className="user-email-text">{currentUser.email}</span>
              </div>
              <button className="logout-btn" onClick={onLogout}>退出登录</button>
            </>
          ) : (
            <button className="login-sidebar-btn" onClick={onLoginClick}>
              登录 / 注册
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
```

**Step 2: Add sidebar auth styles to `App.css`**

```css
.auth-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.07);
}

.login-sidebar-btn {
  width: 100%;
  padding: 9px 12px;
  background: var(--clay);
  border: none;
  border-radius: 8px;
  color: #fff;
  cursor: pointer;
  font-size: 13px;
  font-family: var(--font-body);
  font-weight: 500;
  transition: background 0.2s;
}

.login-sidebar-btn:hover { background: var(--clay-dark); }

.user-email-display {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.user-avatar-initial {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--clay);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: #fff;
  flex-shrink: 0;
}

.user-email-text {
  font-size: 11.5px;
  color: rgba(255,255,255,0.55);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-btn {
  width: 100%;
  padding: 7px 12px;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  color: rgba(255,255,255,0.4);
  cursor: pointer;
  font-size: 12px;
  font-family: var(--font-body);
  transition: border-color 0.2s, color 0.2s;
}

.logout-btn:hover {
  border-color: rgba(255,255,255,0.3);
  color: rgba(255,255,255,0.7);
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/TopicSidebar.jsx frontend/src/App.css
git commit -m "feat: add login/logout UI to sidebar"
```

---

## Task 11: Add Supabase Env Vars to Deployment

**Files:**
- Modify: deployment trigger command

**Step 1: Add env vars to deployment**

```bash
curl -s -X POST "https://space.ai-builders.com/backend/v1/deployments" \
  -H "Authorization: Bearer sk_431f3480_d94c1cf2e25a25a99bf5a83724f02682ded0" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/hk060655/tennis-consultant",
    "service_name": "tennis-consultant",
    "branch": "main",
    "env_vars": {
      "SUPABASE_URL": "YOUR_SUPABASE_URL",
      "SUPABASE_SERVICE_KEY": "YOUR_SERVICE_ROLE_KEY"
    }
  }'
```

**Step 2: Add to `.env` for local dev**

```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

**Step 3: Add to `.env.example`**

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

**Step 4: Commit**

```bash
git add .env.example
git commit -m "docs: add Supabase env vars to .env.example"
```

---

## Task 12: Final Push and Deploy

**Step 1: Final git push**

```bash
git push origin main
```

**Step 2: Trigger deployment with Supabase env vars**

(Use the curl command from Task 11 with real values.)

**Step 3: Verify in production**

1. Visit deployed URL, click "登录 / 注册"
2. Register a new account
3. Send a few chat messages
4. Check Supabase Table Editor → `conversation_history` has rows
5. Check `user_profiles` → `coach_notes` updated within a few seconds
6. Open incognito / different device, log in with same account
7. Verify conversation context carries over
