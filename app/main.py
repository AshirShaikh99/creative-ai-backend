from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.route import router as chat_router  # Updated import path
from app.config.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    chat_router,
    prefix=settings.API_V1_STR,  # Remove the additional "/chat"
    tags=["chat"]
)

@app.get("/")
async def root():
    return {"message": "Welcome to Creative AI Chatbot"}