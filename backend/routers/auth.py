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
    sb.table("user_profiles").insert({
        "id": user_id,
        "email": req.email,
        "coach_notes": "",
    }).execute()
    token = res.session.access_token if res.session else ""
    return AuthResponse(access_token=token, user_id=user_id, email=req.email)

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
