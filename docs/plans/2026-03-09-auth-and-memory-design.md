# 账号登录 + 对话记忆 设计文档

日期：2026-03-09

## 概述

在现有网球教练 AI 助手的基础上，新增可选的账号登录功能，并为已登录用户提供跨设备持久化的对话记忆。未登录用户的体验完全不受影响。

---

## 整体架构

```
前端 React
  ├── 登录/注册页面（新增）
  ├── localStorage 存储 JWT token
  └── 已登录请求带 Authorization: Bearer <token>

FastAPI 后端
  ├── POST /auth/register   — 注册
  ├── POST /auth/login      — 登录，返回 JWT
  ├── GET  /auth/me         — 获取当前用户信息
  ├── POST /chat            — 认证可选（有 token 走持久化逻辑，无 token 走匿名逻辑）
  └── Supabase Python Client
        ├── Auth：注册/验证用户
        └── PostgreSQL：存用户档案 + 对话历史

Supabase（外部）
  ├── Auth：管理邮箱/密码、JWT 签发与验证
  └── 数据库（PostgreSQL）
        ├── user_profiles 表
        └── conversation_history 表
```

---

## 数据库结构（Supabase PostgreSQL）

### `user_profiles` 表

| 列名 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键，等于 Supabase Auth 用户 ID |
| `email` | text | 用户邮箱 |
| `ntrp_level` | text | 网球水平（2.0–4.5） |
| `coach_notes` | text | LLM 自动提炼的用户画像摘要 |
| `created_at` | timestamp | 注册时间 |
| `updated_at` | timestamp | 最后更新时间 |

### `conversation_history` 表

| 列名 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `user_id` | UUID | 外键 → user_profiles.id |
| `role` | text | `user` 或 `assistant` |
| `content` | text | 消息内容 |
| `created_at` | timestamp | 消息时间 |

---

## 认证流程

### 注册
1. 用户填写邮箱 + 密码 → `POST /auth/register`
2. 后端调用 Supabase Auth 创建账号
3. 在 `user_profiles` 插入初始行
4. 返回 JWT → 前端存 localStorage，直接进入应用

### 登录
1. 用户填写邮箱 + 密码 → `POST /auth/login`
2. 后端调用 Supabase Auth 验证，返回 JWT
3. 前端存 localStorage，进入应用

### 请求认证（可选）
- **有 token**：后端用 Supabase 验证，提取 `user_id`，走持久化逻辑
- **无 token**：走现有匿名逻辑，行为与当前完全一致
- token 过期时前端静默退出为匿名模式

### NTRP 水平
- 登录后若 `ntrp_level` 为空，仍显示水平选择页
- 选择后写入 `user_profiles`，跨设备同步

---

## 记忆与个性化系统

### `coach_notes` 格式（示例）
```
- 惯用手：右手
- 当前主要问题：正手发力不足，容易打出浮球
- 已讨论过的训练建议：转体发力练习、Shadow Swing
- 学习风格：喜欢比喻，接受技术术语
- 进展：上周反手有改善，正手仍在练习中
```

### 注入方式
每次 `/chat` 请求，将 `coach_notes` 注入 System Prompt：
```
<user_memory>
以下是你对这位学员的了解，请在回答中自然地考虑这些信息：
{coach_notes}
</user_memory>
```

### 异步提炼流程
1. `/chat` 接口正常返回 AI 回复（不阻塞）
2. 后台 `asyncio.create_task()` 启动提炼任务
3. 提炼 Prompt：最近 20 条对话 + 现有 `coach_notes` → LLM 更新画像
4. 写回 `user_profiles.coach_notes`

首次使用时 `coach_notes` 为空，教练按普通方式回答。

---

## 前端改动

### 新增
- 登录/注册页面（邮箱 + 密码，两个 tab，Clay Court Editorial 风格）

### 侧边栏
- 桌面：底部新增"登录"按钮；登录后显示邮箱首字母头像 + "退出登录"
- 手机：顶栏右侧加登录图标按钮

### 状态管理
- `App.jsx` 新增 `currentUser` state（null = 匿名）
- 应用启动时自动从 localStorage 读取 token 并验证
- token 无效时静默退出，不强制跳登录页

### `/chat` 请求
- 已登录：Header 带 token，`user_id` 用 Supabase UUID
- 未登录：与现在完全一致

### 欢迎消息
- 已登录且有 `coach_notes`：欢迎语个性化，引用上次对话内容

---

## 匿名 vs 已登录对比

| 功能 | 匿名用户 | 已登录用户 |
|------|---------|-----------|
| 基本问答 | ✅ | ✅ |
| 当次会话历史 | ✅（内存） | ✅（内存 + 持久化） |
| 跨设备记忆 | ❌ | ✅ |
| 个性化教练笔记 | ❌ | ✅ |
| 服务重启后保留 | ❌ | ✅ |
