from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Query
from typing import Optional, Dict, Any
from app.models.knowledgebase_model import (
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseUpdate,
    KnowledgeBaseDelete
)
from app.service.knowledgebase_service import KnowledgeBaseService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
kb_service = KnowledgeBaseService()

@router.post("/create", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    uuid: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    document: UploadFile = File(...)
):
    """
    Create a new knowledge base from an uploaded PDF document.
    - **uuid**: Unique identifier for the user
    - **title**: Title of the knowledge base
    - **description**: Description of the knowledge base
    - **document**: PDF file to be processed and stored
    """
    # Validate file type
    if not document.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    logger.info(f"Creating knowledge base '{title}' for user {uuid}")
    
    # Process the request
    response = await kb_service.create_knowledge_base(
        user_uuid=uuid,
        title=title,
        description=description,
        document=document
    )
    
    return response

@router.get("/list/{uuid}", response_model=KnowledgeBaseListResponse)
async def get_knowledge_bases(
    uuid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """
    Get all knowledge bases for a user.
    - **uuid**: Unique identifier for the user
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page
    """
    logger.info(f"Retrieving knowledge bases for user {uuid}, page {page}, page_size {page_size}")
    
    return await kb_service.get_knowledge_bases(
        user_uuid=uuid,
        page=page,
        page_size=page_size
    )

@router.put("/update", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    uuid: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    document: Optional[UploadFile] = File(None)
):
    """
    Update an existing knowledge base.
    - **uuid**: Unique identifier for the user
    - **title**: Title of the knowledge base to update
    - **description**: Updated description (optional)
    - **document**: New PDF file to replace existing content (optional)
    """
    # Validate file type if provided
    if document and not document.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    logger.info(f"Updating knowledge base '{title}' for user {uuid}")
    
    return await kb_service.update_knowledge_base(
        user_uuid=uuid,
        title=title,
        description=description,
        document=document
    )

@router.delete("/delete", response_model=Dict[str, Any])
async def delete_knowledge_base(
    uuid: str = Form(...),
    title: str = Form(...)
):
    """
    Delete a knowledge base.
    - **uuid**: Unique identifier for the user
    - **title**: Title of the knowledge base to delete
    """
    logger.info(f"Deleting knowledge base '{title}' for user {uuid}")
    
    return await kb_service.delete_knowledge_base(
        user_uuid=uuid,
        title=title
    )