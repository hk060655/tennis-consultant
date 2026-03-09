from typing import Optional, Tuple
from backend.db.supabase_client import get_supabase

def get_user_from_token(authorization: Optional[str]) -> Optional[Tuple[str, str]]:
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
