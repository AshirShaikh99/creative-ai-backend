from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.route import router as chat_router
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

@app.get("/")
async def root():
    return {"message": "Welcome to Creative AI Chatbot"}