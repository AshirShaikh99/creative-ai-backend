from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from app.models.knowledgebase_model import KnowledgeBaseCreate, KnowledgeBaseResponse
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