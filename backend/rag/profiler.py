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

async def update_coach_notes(user_id: str, recent_messages: list, existing_notes: str):
    sb = get_supabase()
    if sb is None:
        return
    try:
        from backend.config import settings
        from openai import OpenAI
        client = OpenAI(api_key=settings.ai_builder_token, base_url=settings.ai_builder_base_url)
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
