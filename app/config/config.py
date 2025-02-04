from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Creative AI Backend"
    API_V1_STR: str = "/api/v1"  # Added API version string
    GROQ_API_KEY: str
    QDRANT_URL: str
    QDRANT_API_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()