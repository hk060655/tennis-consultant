import asyncio
import logging
from typing import Optional, Tuple
from backend.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


async def get_user_from_token(authorization: Optional[str]) -> Optional[Tuple[str, str]]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    sb = get_supabase()
    if sb is None:
        return None
    try:
        res = await asyncio.to_thread(sb.auth.get_user, token)
        return str(res.user.id), res.user.email
    except Exception as e:
        logger.debug(f"Token validation failed: {e}")
        return None
