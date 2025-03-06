from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.route import router as chat_router
from app.routes.knowledgebase_route.route import router as knowledge_base_router
from app.routes.audio_route import router as audio_router

from app.config.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    chat_router,
    prefix=settings.API_V1_STR,
    tags=["chat"]
)
app.include_router(
    knowledge_base_router, 
    prefix="/api/knowledge-base", 
    tags=["Knowledge Base"]
)
app.include_router(
    audio_router,
    prefix="/api/audio",
    tags=["Voice Agent"]
)

@app.get("/")
async def root():
    return {"message": "Welcome to Creative AI Chatbot"}