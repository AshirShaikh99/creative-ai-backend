from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import Field
from typing import ClassVar

class Settings(BaseSettings):
    APP_NAME: str = "Creative AI Backend"
    API_V1_STR: str = "/api/v1"
    GROQ_API_KEY: str = Field(..., env="GROQ_API_KEY")
    QDRANT_URL: str = Field(..., env="QDRANT_URL")
    QDRANT_API_KEY: str = Field(..., env="QDRANT_API_KEY")
    FAST_LLM: str = Field(..., env="FAST_LLM")
    SMART_LLM: str = Field(..., env="SMART_LLM")
    STRATEGIC_LLM: str = Field(..., env="STRATEGIC_LLM")  # Optional if using a strategic model
    EMBEDDING: str = Field(..., env="EMBEDDING")  # Optional if using embeddings

    # This ensures Pydantic does not treat `model_config` as a field
    model_config: ClassVar[dict] = {
        "extra": "allow"  # This allows extra fields from the .env file without errors
    }

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }

@lru_cache()
def get_settings() -> Settings:
    return Settings()
