from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class NTRPLevel(str, Enum):
    L20 = "2.0"
    L25 = "2.5"
    L30 = "3.0"
    L35 = "3.5"
    L40 = "4.0"
    L45 = "4.5"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(..., min_length=1, max_length=64)
    user_level: Optional[NTRPLevel] = None


class SourceChunk(BaseModel):
    text: str
    source_file: str
    section_title: str
    skill_level: str
    distance: float


class ChatResponse(BaseModel):
    reply: str
    sources: list[SourceChunk]
    user_id: str
    is_uncertain: bool


class ReloadResponse(BaseModel):
    status: str
    chunks_loaded: int
    message: str


class HealthResponse(BaseModel):
    status: str
    chroma_ready: bool
    chunks_in_db: int


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
