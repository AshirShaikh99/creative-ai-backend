from pydantic import BaseModel, Field
from typing import Optional
from fastapi import UploadFile
from uuid import UUID


class KnowledgeBaseCreate(BaseModel):
    uuid: str
    title: str
    description: str


class KnowledgeBaseResponse(BaseModel):
    uuid: str
    title: str
    description: str
    status: str
    collection_name: str
    document_count: Optional[int] = 0