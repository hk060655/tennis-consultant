# AI 网球教练

基于 RAG（检索增强生成）的 AI 网球教练助手，使用 Claude + ChromaDB + React 构建。

## 快速启动

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API 密钥
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

首次启动时会自动向量化知识库（调用 OpenAI Embedding API，约需 10-20 秒）。

### 3. 启动前端

```bash
cd frontend
npm install
npm start
```

浏览器访问 http://localhost:3000

## 项目结构

```
tennis_consultant/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置（环境变量）
│   ├── rag/
│   │   ├── loader.py        # Markdown 文档切分
│   │   ├── embedder.py      # ChromaDB 向量化与存储
│   │   ├── retriever.py     # 语义检索
│   │   └── generator.py     # Prompt 组装 + Claude 调用
│   ├── models/
│   │   └── schemas.py       # Pydantic 数据模型
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # 根组件（状态管理）
│   │   ├── App.css          # 全局样式
│   │   └── components/
│   │       ├── LevelSelector.jsx   # NTRP 水平选择页
│   │       ├── TopicSidebar.jsx    # 话题分类侧栏
│   │       ├── ChatWindow.jsx      # 聊天窗口 + 输入框
│   │       └── MessageBubble.jsx   # 消息气泡（支持 Markdown）
│   └── package.json
├── data/
│   └── tennis_knowledge/    # 知识库 Markdown 文件
├── .env.example
└── README.md
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 发送消息，获取 AI 回复 |
| POST | `/knowledge/reload` | 重新向量化知识库 |
| GET  | `/health` | 健康检查 |

### POST /chat 示例

```json
{
  "message": "我的正手总是打出界，怎么纠正？",
  "user_id": "user_abc123",
  "user_level": "3.0"
}
```

## 知识库更新

将新的 `.md` 文件放入 `data/tennis_knowledge/` 对应目录后，调用：

```bash
curl -X POST http://localhost:8000/knowledge/reload
```

## 技术栈

- **LLM**: Anthropic Claude (claude-sonnet-4-5)
- **Embedding**: OpenAI text-embedding-3-small
- **向量数据库**: ChromaDB（本地持久化）
- **后端**: Python FastAPI
- **前端**: React 18 + react-markdown
