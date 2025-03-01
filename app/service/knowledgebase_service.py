import os
import uuid as uuid_lib
import tempfile
import logging
from typing import Dict, Any, List, Optional, Tuple
from fastapi import UploadFile, HTTPException
from app.service.qdrant_service import QdrantService
from app.utils.chunking import DocumentChunker
from sentence_transformers import SentenceTransformer
import torch
from qdrant_client.models import VectorParams, Distance, CollectionStatus
from tenacity import retry, stop_after_attempt, wait_exponential
from app.models.knowledgebase_model import KnowledgeBaseResponse, KnowledgeBaseListResponse
import shutil
import time

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    def __init__(self):
        logger.info("Initializing KnowledgeBaseService")
        self.chunker = DocumentChunker()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Device handling
        if torch.backends.mps.is_available():
            self.device = 'mps'
            logger.info("Using MPS (Metal) device")
        elif torch.cuda.is_available():
            self.device = 'cuda'
            logger.info("Using CUDA device")
        else:
            self.device = 'cpu'
            logger.info("Using CPU device")
            
        self.model = self.model.to(self.device)
        self.qdrant_client = QdrantService.get_instance()
        self.batch_size = 32
        
        # In-memory storage to replace database
        self.knowledge_bases = {}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_knowledge_base(self, user_uuid: str, title: str, description: str, document: UploadFile) -> KnowledgeBaseResponse:
        """Create a new knowledge base for a user with the uploaded document"""
        start_time = time.time()
        collection_name = f"kb_{user_uuid}_{self._sanitize_collection_name(title)}"
        
        try:
            # Check if collection exists in Qdrant
            collections = self.qdrant_client.get_collections()
            if collection_name in [c.name for c in collections.collections]:
                logger.warning(f"Collection {collection_name} already exists in Qdrant")
                raise HTTPException(status_code=409, detail=f"Knowledge base with title '{title}' already exists for this user")
            
            # Check if knowledge base exists in memory
            user_kbs = self.knowledge_bases.get(user_uuid, {})
            if title in user_kbs:
                logger.error(f"Knowledge base with title '{title}' already exists for user {user_uuid}")
                raise HTTPException(status_code=409, detail=f"Knowledge base with title '{title}' already exists for this user")
            
            # Create new knowledge base entry
            kb_entry = {
                "id": len(user_kbs) + 1,
                "uuid": user_uuid,
                "title": title,
                "description": description,
                "status": "processing",
                "collection_name": collection_name,
                "document_count": 0,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Create new collection with optimized config
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=384,  # Dimension size for all-MiniLM-L6-v2
                    distance=Distance.COSINE
                ),
                optimizers_config={
                    "memmap_threshold": 10000,
                    "indexing_threshold": 20000,
                    "max_optimization_threads": 4,
                    "deleted_threshold": 0.2,
                    "vacuum_min_vector_number": 1000,
                    "default_segment_number": 2,
                    "flush_interval_sec": 5
                }
            )
            logger.info(f"Created new collection: {collection_name}")
            
            # Save the uploaded file temporarily and process it
            temp_dir = tempfile.mkdtemp()
            try:
                temp_file_path = os.path.join(temp_dir, document.filename)
                
                # Save uploaded file
                with open(temp_file_path, "wb") as temp_file:
                    content = await document.read()
                    temp_file.write(content)
                    await document.seek(0)  # Reset file pointer for potential reuse
                
                logger.info(f"Saved uploaded file to {temp_file_path}")
                
                # Process and embed the document
                document_count = await self._process_document(temp_file_path, collection_name)
                
                # Update the knowledge base entry
                kb_entry["status"] = "completed"
                kb_entry["document_count"] = document_count
                
                # Store in memory
                if user_uuid not in self.knowledge_bases:
                    self.knowledge_bases[user_uuid] = {}
                self.knowledge_bases[user_uuid][title] = kb_entry
                
                # Create the response
                response = self._entry_to_response(kb_entry)
                
                total_time = time.time() - start_time
                logger.info(f"Completed knowledge base creation in {total_time:.2f} seconds")
                
                return response
                
            finally:
                # Clean up temp directory
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            # Clean up if collection was created but processing failed
            try:
                # Delete Qdrant collection if it was created
                collections = self.qdrant_client.get_collections()
                if collection_name in [c.name for c in collections.collections]:
                    self.qdrant_client.delete_collection(collection_name)
                    logger.info(f"Deleted collection {collection_name} due to processing failure")
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {str(cleanup_error)}")
                
            logger.error(f"Error creating knowledge base: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Failed to create knowledge base: {str(e)}")
    
    async def get_knowledge_bases(self, user_uuid: str, page: int = 1, page_size: int = 10) -> KnowledgeBaseListResponse:
        """Get all knowledge bases for a user with pagination"""
        try:
            # Get knowledge bases for user
            user_kbs = self.knowledge_bases.get(user_uuid, {})
            kb_list = list(user_kbs.values())
            
            # Sort by created_at (newest first)
            kb_list.sort(key=lambda x: x["created_at"], reverse=True)
            
            # Get total count
            total_count = len(kb_list)
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_kbs = kb_list[start_idx:end_idx]
            
            # Convert to response models
            response_models = [self._entry_to_response(kb) for kb in paginated_kbs]
            
            return KnowledgeBaseListResponse(
                uuid=user_uuid,
                knowledge_bases=response_models,
                total_count=total_count,
                page=page,
                page_size=page_size
            )
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge bases for user {user_uuid}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve knowledge bases: {str(e)}")
    
    async def update_knowledge_base(
        self, 
        user_uuid: str, 
        title: str, 
        description: Optional[str] = None,
        document: Optional[UploadFile] = None
    ) -> KnowledgeBaseResponse:
        """Update a knowledge base for a user"""
        try:
            # Find the knowledge base in memory
            user_kbs = self.knowledge_bases.get(user_uuid, {})
            if title not in user_kbs:
                raise HTTPException(status_code=404, detail=f"Knowledge base with title '{title}' not found for this user")
                
            kb_entry = user_kbs[title]
            
            # Update description if provided
            if description is not None:
                kb_entry["description"] = description
                
            # If document is provided, update the vector embeddings
            if document:
                # Temporarily set status to updating
                kb_entry["status"] = "updating"
                
                collection_name = kb_entry["collection_name"]
                
                # Check if collection exists
                collections = self.qdrant_client.get_collections()
                if collection_name not in [c.name for c in collections.collections]:
                    # If collection doesn't exist, create it
                    self.qdrant_client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=384,
                            distance=Distance.COSINE
                        )
                    )
                else:
                    # If collection exists, delete all points
                    self.qdrant_client.delete_collection(collection_name)
                    self.qdrant_client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=384,
                            distance=Distance.COSINE
                        )
                    )
                
                # Process the new document
                temp_dir = tempfile.mkdtemp()
                try:
                    temp_file_path = os.path.join(temp_dir, document.filename)
                    
                    # Save uploaded file
                    with open(temp_file_path, "wb") as temp_file:
                        content = await document.read()
                        temp_file.write(content)
                        await document.seek(0)
                    
                    # Process and embed the document
                    document_count = await self._process_document(temp_file_path, collection_name)
                    
                    # Update the knowledge base entry
                    kb_entry["document_count"] = document_count
                    
                finally:
                    # Clean up temp directory
                    shutil.rmtree(temp_dir)
            
            # Update status and timestamp
            kb_entry["status"] = "completed"
            kb_entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Return the updated knowledge base
            return self._entry_to_response(kb_entry)
            
        except Exception as e:
            logger.error(f"Error updating knowledge base for user {user_uuid}, title {title}: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Failed to update knowledge base: {str(e)}")
    
    async def delete_knowledge_base(self, user_uuid: str, title: str) -> Dict[str, Any]:
        """Delete a knowledge base for a user"""
        try:
            # Find the knowledge base in memory
            user_kbs = self.knowledge_bases.get(user_uuid, {})
            if title not in user_kbs:
                raise HTTPException(status_code=404, detail=f"Knowledge base with title '{title}' not found for this user")
            
            kb_entry = user_kbs[title]
            collection_name = kb_entry["collection_name"]
            
            # Delete from memory
            del user_kbs[title]
            
            # Delete from Qdrant
            collections = self.qdrant_client.get_collections()
            if collection_name in [c.name for c in collections.collections]:
                self.qdrant_client.delete_collection(collection_name)
                logger.info(f"Deleted collection {collection_name}")
            
            return {
                "status": "success", 
                "message": f"Knowledge base '{title}' successfully deleted",
                "uuid": user_uuid,
                "title": title
            }
                
        except Exception as e:
            logger.error(f"Error deleting knowledge base for user {user_uuid}, title {title}: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Failed to delete knowledge base: {str(e)}")
    
    def _sanitize_collection_name(self, name: str) -> str:
        """Convert a title to a valid collection name"""
        # Replace spaces and special characters with underscores
        sanitized = ''.join(c if c.isalnum() else '_' for c in name.lower())
        # Ensure it's not too long (Qdrant has limits)
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        return sanitized
    
    def _entry_to_response(self, entry: Dict[str, Any]) -> KnowledgeBaseResponse:
        """Convert a memory entry to a response model"""
        return KnowledgeBaseResponse(
            id=entry["id"],
            uuid=entry["uuid"],
            title=entry["title"],
            description=entry["description"],
            status=entry["status"],
            collection_name=entry["collection_name"],
            document_count=entry["document_count"],
            created_at=entry["created_at"],
            updated_at=entry["updated_at"]
        )
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _process_document(self, file_path: str, collection_name: str) -> int:
        """Process a document, extract chunks, and store embeddings in Qdrant"""
        try:
            chunks = self.chunker.process_document(file_path)
            logger.info(f"Generated {len(chunks)} chunks from {os.path.basename(file_path)}")
            
            chunks_processed = 0
            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                logger.info(f"Processing batch {i//self.batch_size + 1} of {(len(chunks) + self.batch_size - 1)//self.batch_size}")
                
                # Get embeddings for the batch
                batch_embeddings = self._get_embeddings(batch)
                
                # Create points for Qdrant
                points = []
                for idx, emb in enumerate(batch_embeddings):
                    points.append({
                        "id": str(uuid_lib.uuid4()),
                        "vector": emb,
                        "payload": {
                            "source": os.path.basename(file_path),
                            "content": batch[idx]['content'][:5000],
                            "metadata": {
                                'page': batch[idx].get('page'),
                                'type': batch[idx].get('type')
                            }
                        }
                    })
                
                # Store embeddings in Qdrant
                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=points
                )
                
                chunks_processed += len(batch)
                logger.info(f"Stored batch {i//self.batch_size + 1} of embeddings")
                time.sleep(0.5)  # Prevent overwhelming the service
            
            return chunks_processed
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise
    
    def _get_embeddings(self, chunks):
        """Generate embeddings for text chunks"""
        try:
            texts = [chunk["content"] for chunk in chunks]
            with torch.no_grad():
                embeddings = self.model.encode(texts, convert_to_tensor=True)
                # Move to CPU first if using MPS or CUDA
                if self.device != 'cpu':
                    embeddings = embeddings.cpu()
                # Convert to numpy and then to list for JSON serialization
                return embeddings.numpy().tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise