from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    ai_builder_token: str
    ai_builder_base_url: str = "https://space.ai-builders.com/backend/v1"
    knowledge_base_path: Path = Path("data/tennis_knowledge")
    chroma_db_path: Path = Path("chroma_db")
    chroma_collection_name: str = "tennis_knowledge"
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "deepseek"
    top_k: int = 5
    similarity_threshold: float = 0.70
    max_conversation_turns: int = 5
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
