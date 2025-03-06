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
    FAST_LLM: str = Field("groq:mixtral-8x7b-32768", env="FAST_LLM")
    SMART_LLM: str = Field("groq:mixtral-8x7b-32768", env="SMART_LLM")
    STRATEGIC_LLM: str = Field("groq:mixtral-8x7b-32768", env="STRATEGIC_LLM")
    EMBEDDING: str = Field(default="text-embedding-3-small", env="EMBEDDING")
    
    # LiveKit Configuration
    LIVEKIT_API_KEY: str = Field(..., env="LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET: str = Field(..., env="LIVEKIT_API_SECRET")
    LIVEKIT_WS_URL: str = Field(..., env="LIVEKIT_WS_URL")
    
    # Deepgram and ElevenLabs Configuration
    DEEPGRAM_API_KEY: str = Field(..., env="DEEPGRAM_API_KEY")
    DEEPGRAM_MODEL: str = Field(default="nova-2", env="DEEPGRAM_MODEL")
    ELEVENLABS_API_KEY: str = Field(..., env="ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID: str = Field(default="Antoni", env="ELEVENLABS_VOICE_ID")
    
    # Audio processing settings
    AUDIO_SAMPLE_RATE: int = Field(default=16000, env="AUDIO_SAMPLE_RATE")
    AUDIO_CHUNK_SIZE: int = Field(default=4096, env="AUDIO_CHUNK_SIZE")

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }

@lru_cache()
def get_settings() -> Settings:
    return Settings()
