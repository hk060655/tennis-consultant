import logging
import threading
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Optional[Client] = None
_lock = threading.Lock()


def get_supabase() -> Optional[Client]:
    global _client
    if _client is not None:
        return _client
    with _lock:
        if _client is not None:
            return _client
        from backend.config import settings
        if not settings.supabase_url or not settings.supabase_service_key:
            return None
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def is_supabase_enabled() -> bool:
    return get_supabase() is not None
