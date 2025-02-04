from qdrant_client import QdrantClient
import os

class QdrantService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY"),
                timeout=200.0,  # Global timeout
            )
        return cls._instance