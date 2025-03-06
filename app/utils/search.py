from typing import List, Dict, Any, Optional
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    Range,
    SearchParams,
    PayloadSelectorExclude
)
from dataclasses import dataclass
import hashlib
import json
import asyncio
from functools import lru_cache
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    content: str
    metadata: Dict
    score: float
    source: str

class QdrantSearch:
    def __init__(
        self,
        qdrant_client: QdrantClient,
    ):
        self.qdrant_client = qdrant_client
        
        # Initialize embedding model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
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
        
        self._init_search_params()
        self._init_payload_selector()
        logger.info("QdrantSearch initialized with exact search for optimal results")

    def _init_search_params(self):
        """Initialize search parameters for maximum accuracy"""
        self.default_search_params = SearchParams(
            hnsw_ef=256,  # Increased from 128 for better recall
            exact=True    # Using exact search for best results
        )
        # Removed quantization parameters

    def _init_payload_selector(self):
        """Initialize payload selector to exclude unnecessary fields"""
        self.payload_selector = PayloadSelectorExclude(
            exclude=["created_at", "updated_at", "embedding"]
        )

    @lru_cache(maxsize=1000)
    def _generate_cache_key(self, query: str, collection_name: str, **params) -> str:
        """Generate a deterministic cache key with LRU caching"""
        cache_data = {
            "query": query,
            "collection": collection_name,
            **params
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()

    @lru_cache(maxsize=10000)
    def _get_embedding_cached(self, text: str) -> tuple:
        """Get embedding with LRU caching. Returns tuple for immutability."""
        with torch.no_grad():
            embedding = self.model.encode(text, convert_to_tensor=True)
            if self.device != 'cpu':
                embedding = embedding.cpu()
            return tuple(embedding.numpy().tolist())

    async def _get_embedding(self, text: str) -> List[float]:
        """Async wrapper for cached embedding generation"""
        try:
            # Use run_in_executor to run CPU-intensive operation in thread pool
            embedding = await asyncio.to_thread(self._get_embedding_cached, text)
            return list(embedding)  # Convert back to list for JSON serialization
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    @lru_cache(maxsize=1000)
    def _cache_search_results(self, cache_key: str, results_str: str) -> List[SearchResult]:
        """Cache and deserialize search results"""
        results_data = json.loads(results_str)
        return [SearchResult(**result) for result in results_data]

    async def search(
            self,
            query: str,
            collection_name: str,
            limit: int = 5,
            score_threshold: float = 0.5,
            filter_conditions: Optional[Dict] = None,
            use_cache: bool = True
        ) -> List[SearchResult]:
            try:
                logger.info(f"Starting search in collection: {collection_name}")
                logger.info(f"Query: {query}")
                logger.info(f"Score threshold: {score_threshold}")

                # Get embedding asynchronously
                embedding = await self._get_embedding(query)
                logger.info(f"Generated embedding of size: {len(embedding)}")

                # Build filter if provided
                search_filter = None
                if filter_conditions:
                    search_filter = self._build_filter(filter_conditions)
                    logger.info(f"Applied filter: {search_filter}")

                search_params = {
                    "collection_name": collection_name,
                    "query_vector": embedding,
                    "limit": limit,
                    "score_threshold": score_threshold,
                    "search_params": self.default_search_params,
                    "with_payload": True,
                    "payload_selector": self.payload_selector
                }
                
                # Add filter if it exists
                if search_filter:
                    search_params["filter"] = search_filter
                
                logger.info(f"Search parameters: {search_params}")

                # Check if collection exists
                try:
                    collection_info = self.qdrant_client.get_collection(collection_name)
                    logger.info(f"Collection info: {collection_info}")
                except Exception as e:
                    logger.error(f"Error getting collection info: {str(e)}")
                    return []

                results = await asyncio.to_thread(
                    self.qdrant_client.search,
                    **search_params
                )
                logger.info(f"Raw search results count: {len(results)}")

                processed_results = self._process_results(results)
                logger.info(f"Processed results count: {len(processed_results)}")

                return processed_results

            except Exception as e:
                logger.error(f"Search error: {str(e)}")
                raise

    def _build_filter(self, conditions: Dict) -> Filter:
        """Build optimized Qdrant filter"""
        must_conditions = []
        for key, value in conditions.items():
            if isinstance(value, dict):
                if "range" in value:
                    must_conditions.append(
                        FieldCondition(key=key, range=Range(**value["range"]))
                    )
                elif "match" in value:
                    must_conditions.append(
                        FieldCondition(key=key, match={"value": value["match"]})
                    )
            else:
                must_conditions.append(
                    FieldCondition(key=key, match={"value": value})
                )
        
        return Filter(must=must_conditions)

    def _process_results(self, results: List) -> List[SearchResult]:
        """Process search results with optimized performance"""
        return [
            SearchResult(
                content=result.payload.get("content", ""),
                metadata=result.payload.get("metadata", {}),
                score=result.score,
                source=result.payload.get("source", "unknown")
            )
            for result in results
        ]

SemanticSearch = QdrantSearch