import os
from typing import List, Dict
import uuid
import hashlib
import pickle
from app.utils.chunking import DocumentChunker
from sentence_transformers import SentenceTransformer
import logging
from app.service.qdrant_service import QdrantService
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from qdrant_client import models
import torch

logger = logging.getLogger(__name__)

class EmbeddingCache:
    def __init__(self, cache_dir="cache/embeddings"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"Initialized embedding cache at {cache_dir}")

    def get_file_hash(self, file_path: str) -> str:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def get_cache_path(self, file_hash: str) -> str:
        return os.path.join(self.cache_dir, f"{file_hash}.pkl")

    def exists(self, file_path: str) -> bool:
        file_hash = self.get_file_hash(file_path)
        return os.path.exists(self.get_cache_path(file_hash))

    def save(self, file_path: str, embeddings_data: List):
        file_hash = self.get_file_hash(file_path)
        cache_path = self.get_cache_path(file_hash)
        with open(cache_path, 'wb') as f:
            pickle.dump(embeddings_data, f)
        logger.info(f"Cached embeddings for {file_path}")

    def load(self, file_path: str) -> List:
        file_hash = self.get_file_hash(file_path)
        cache_path = self.get_cache_path(file_hash)
        with open(cache_path, 'rb') as f:
            return pickle.load(f)

class DocumentProcessor:
    def __init__(self):
        logger.info("Initializing DocumentProcessor")
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
        self.collection_name = "documents"
        self.embedding_cache = EmbeddingCache()
        self.batch_size = 32
        self.max_retries = 3
        self._initialize_collection()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _initialize_collection(self):
        try:
            collections = self.qdrant_client.get_collections()
            collection_exists = self.collection_name in [c.name for c in collections.collections]   

            if collection_exists:
                collection_info = self.qdrant_client.get_collection(self.collection_name)
                points_count = collection_info.points_count
                logger.info(f"Found existing collection '{self.collection_name}' with {points_count} points")
                return
            
            # Create new collection without binary quantization
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE
                ),
                # Removed quantization_config for high-quality vector storage
                optimizers_config={
                    "memmap_threshold": 10000,
                    "indexing_threshold": 20000,
                    "max_optimization_threads": 4,
                    "deleted_threshold": 0.2,
                    "vacuum_min_vector_number": 1000,
                    "default_segment_number": 2,
                    "flush_interval_sec": 5
                },
                hnsw_config=models.HnswConfigDiff(
                    m=16,                 # Number of edges per node in the graph
                    ef_construct=200,     # Size of the dynamic candidate list during construction
                    full_scan_threshold=10000,  # Threshold for switching to full scan search
                    max_indexing_threads=4      # Number of threads used for indexing
                )
            )
            logger.info(f"Created new collection with exact vector storage: {self.collection_name}") 

        except Exception as e:
            logger.error(f"Error initializing collection: {str(e)}")
            raise
        
    def process_directory(self, docs_dir: str):
        start_time = time.time()
        logger.info(f"Starting document processing from directory: {docs_dir}")
        
        if not os.path.exists(docs_dir):
            logger.error(f"Directory not found: {docs_dir}")
            return

        files = [f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f))]
        total_files = len(files)
        logger.info(f"Found {total_files} files to process")

        for idx, filename in enumerate(files, 1):
            file_path = os.path.join(docs_dir, filename)
            logger.info(f"Processing file {idx}/{total_files}: {filename}")
            file_start_time = time.time()

            try:
                if self.embedding_cache.exists(file_path):
                    logger.info(f"Loading cached embeddings for {filename}")
                    embeddings_data = self.embedding_cache.load(file_path)
                    self._store_embeddings_with_retry(embeddings_data, file_path)
                else:
                    self._process_new_file(file_path)
                
                file_process_time = time.time() - file_start_time
                logger.info(f"Completed processing {filename} in {file_process_time:.2f} seconds")
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                continue

        total_time = time.time() - start_time
        logger.info(f"Completed all document processing in {total_time:.2f} seconds")

    def _process_new_file(self, file_path: str):
        try:
            chunks = self.chunker.process_document(file_path)
            logger.info(f"Generated {len(chunks)} chunks from {os.path.basename(file_path)}")
            
            embeddings_data = []
            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                logger.info(f"Processing batch {i//self.batch_size + 1} of {(len(chunks) + self.batch_size - 1)//self.batch_size}")
                
                batch_embeddings = self._get_embeddings_with_retry(batch)
                embeddings_data.extend([{
                    'embedding': emb,
                    'content': batch[idx]['content'],
                    'metadata': {
                        'source': file_path,
                        'page': batch[idx].get('page'),
                        'type': batch[idx].get('type')
                    }
                } for idx, emb in enumerate(batch_embeddings)])
                
                self._store_embeddings_with_retry(embeddings_data[-self.batch_size:], file_path)
            
            self.embedding_cache.save(file_path, embeddings_data)
            
        except Exception as e:
            logger.error(f"Error in _process_new_file for {file_path}: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _get_embeddings_with_retry(self, chunks: List[Dict]):
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _store_embeddings_with_retry(self, embeddings: List, source_file: str):
        try:
            max_batch_size = 50
            for i in range(0, len(embeddings), max_batch_size):
                batch = embeddings[i:i + max_batch_size]
                points = []
                
                for embedding in batch:
                    point = models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding['embedding'],
                        payload={
                            "content": embedding['content'][:5000],  # Limit content length
                            "source": source_file,  # Keep full path
                            "metadata": {
                                "page": embedding['metadata'].get('page'),
                                "type": embedding['metadata'].get('type'),
                                "filename": os.path.basename(source_file)
                            }
                        }
                    )
                    points.append(point)
                
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=models.Batch(
                        ids=[p.id for p in points],
                        vectors=[p.vector for p in points],
                        payloads=[p.payload for p in points]
                    )
                )
                logger.info(f"Stored batch {i//max_batch_size + 1} with {len(points)} points")
                
        except Exception as e:
            logger.error(f"Error storing embeddings: {str(e)}")
            raise