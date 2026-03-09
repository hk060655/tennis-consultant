import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from backend.auth_utils import get_user_from_token
from backend.rag.profiler import update_coach_notes
from backend.db.supabase_client import get_supabase

from backend.config import settings
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ReloadResponse,
)
from backend.rag.embedder import embedder
from backend.rag.generator import generator
from backend.rag.retriever import retriever
from backend.routers.auth import router as auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory conversation store: {user_id: [{"role": ..., "content": ...}, ...]}
conversation_store: dict[str, list[dict]] = defaultdict(list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing knowledge base...")
    count = embedder.init_collection(force_reload=False)
    logger.info(f"Knowledge base ready: {count} chunks")
    yield


app = FastAPI(title="Tennis AI Coach API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, authorization: Optional[str] = Header(None)):
    # Resolve user identity
    auth_user = get_user_from_token(authorization)
    is_authenticated = auth_user is not None

    if is_authenticated:
        user_id, _ = auth_user
    else:
        user_id = request.user_id

    level_str = request.user_level.value if request.user_level else None

    # For authenticated users: load profile + persistent history
    coach_notes = ""
    if is_authenticated:
        sb = get_supabase()
        if sb:
            profile_res = sb.table("user_profiles").select("coach_notes, ntrp_level").eq("id", user_id).single().execute()
            if profile_res.data:
                coach_notes = profile_res.data.get("coach_notes") or ""
                if not level_str:
                    level_str = profile_res.data.get("ntrp_level")

            hist_res = (
                sb.table("conversation_history")
                .select("role, content")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            history = list(reversed(hist_res.data)) if hist_res.data else []
        else:
            history = conversation_store[user_id]
    else:
        history = conversation_store[user_id]

    t0 = time.perf_counter()
    chunks, is_uncertain = retriever.retrieve(
        query=request.message,
        user_level=level_str,
        top_k=settings.top_k,
    )
    t_rag = time.perf_counter() - t0

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
            if request.user_level:
                sb.table("user_profiles").update({"ntrp_level": level_str}).eq("id", user_id).execute()
            import asyncio
            all_history = history + new_messages
            asyncio.create_task(update_coach_notes(user_id, all_history, coach_notes))
    else:
        history.extend(new_messages)
        conversation_store[user_id] = history[-40:]

    return ChatResponse(
        reply=reply,
        sources=chunks,
        user_id=user_id,
        is_uncertain=is_uncertain,
    )


@app.post("/knowledge/reload", response_model=ReloadResponse)
async def reload_knowledge():
    try:
        count = embedder.init_collection(force_reload=True)
        return ReloadResponse(
            status="success",
            chunks_loaded=count,
            message=f"Knowledge base reloaded with {count} chunks",
        )
    except Exception as e:
        logger.error(f"Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health():
    try:
        col = embedder.get_collection()
        count = col.count()
        return HealthResponse(status="ok", chroma_ready=True, chunks_in_db=count)
    except Exception:
        return HealthResponse(status="degraded", chroma_ready=False, chunks_in_db=0)


# ── Serve React frontend (production) ──────────────────────────────────────
FRONTEND_BUILD = Path("frontend/build")

if FRONTEND_BUILD.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_BUILD / "static")),
        name="static-assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = FRONTEND_BUILD / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_BUILD / "index.html"))
