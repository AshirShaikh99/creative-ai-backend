from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi import UploadFile
from uuid import UUID
from datetime import datetime


class KnowledgeBaseCreate(BaseModel):
    uuid: str
    title: str
    description: str


class KnowledgeBaseResponse(BaseModel):
    id: int
    uuid: str
    title: str
    description: str
    status: str
    collection_name: str
    document_count: Optional[int] = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class KnowledgeBaseListResponse(BaseModel):
    uuid: str
    knowledge_bases: List[KnowledgeBaseResponse]
    total_count: int
    page: int
    page_size: int


class KnowledgeBaseUpdate(BaseModel):
    uuid: str
    title: str
    description: Optional[str] = None


class KnowledgeBaseDelete(BaseModel):
    uuid: str
    title: str