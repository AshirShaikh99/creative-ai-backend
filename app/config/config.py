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
    FAST_LLM: str = Field("mixtral-8x7b-32768", env="FAST_LLM")
    SMART_LLM: str = Field("mixtral-8x7b-32768", env="SMART_LLM")
    STRATEGIC_LLM: str = Field("mixtral-8x7b-32768", env="STRATEGIC_LLM")
    EMBEDDING: str = Field(default="text-embedding-3-small", env="EMBEDDING")

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }

@lru_cache()
def get_settings() -> Settings:
    return Settings()
