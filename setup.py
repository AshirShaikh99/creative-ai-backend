from setuptools import setup, find_packages

setup(
    name="creative-ai-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "groq",
        "qdrant-client",
        "ai21>=1.0.0,<3.0.0",
        "livekit",
        "deepgram-sdk",
        "elevenlabs",
        "python-dotenv",
        "pydantic",
        "pydantic-settings",
    ],
    python_requires=">=3.9",
)
