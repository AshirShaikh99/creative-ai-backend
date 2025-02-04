from typing import Dict, Optional, List, Tuple
from app.models.model import Message, ChatSession, ChatResponse
from uuid import UUID
from groq import AsyncGroq
from app.config.config import get_settings
from app.service.qdrant_service import QdrantService
from app.utils.search import QdrantSearch, SearchResult  # Added SearchResult import
from functools import lru_cache
import json
import hashlib

settings = get_settings()
groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

class CreativeAIChatbot:
    def __init__(self):
        self.sessions: Dict[UUID, ChatSession] = {}
        # Initialize semantic search
        qdrant_client = QdrantService.get_instance()
        self.semantic_search = QdrantSearch(qdrant_client=qdrant_client)
        
    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[UUID] = None
    ) -> ChatSession:
        # Get or create session
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
        else:
            session = ChatSession(user_id=user_id)
            self.sessions[session.id] = session
        
        # Add user message
        user_message = Message(content=message, role="user")
        session.messages.append(user_message)
        
        # Search relevant documents
        search_results = await self.semantic_search.search(
            query=message,
            collection_name="documents",
            limit=3,
            score_threshold=0.7
        )
        
        # Generate response with context
        response = await self._generate_response(message, search_results, session)
        
        # Add assistant message
        assistant_message = Message(content=response, role="assistant")
        session.messages.append(assistant_message)
        
        return session
    
    @lru_cache(maxsize=1000)
    def _format_context_cached(self, context_tuple: Tuple[Tuple[str, str, float, str], ...]) -> str:
        """Cached version of context formatting. Takes tuple for immutability."""
        if not context_tuple:
            return ""
            
        context_parts = []
        for source, content, score, _ in context_tuple:
            context_parts.append(f"Context from {source}:\n{content}\n")
        
        return "\n".join(context_parts)
    
    def _format_context(self, search_results: List[SearchResult]) -> str:
        """Format search results into context for the LLM with caching"""
        # Convert search results to tuple for caching
        context_tuple = tuple(
            (r.source, r.content, r.score, r.metadata.get("type", "")) 
            for r in search_results
        )
        return self._format_context_cached(context_tuple)

    @lru_cache(maxsize=1000)
    def _cache_llm_response(self, message_hash: str, context_hash: str) -> str:
        """Cache for LLM responses"""
        return ""  # Empty string triggers cache miss

    async def _generate_response(self, message: str, search_results: List[SearchResult], session: ChatSession) -> str:
        try:
            context = self._format_context(search_results)
            
            # Generate cache keys
            message_hash = hashlib.sha256(message.encode()).hexdigest()
            context_hash = hashlib.sha256(context.encode()).hexdigest()
            
            # Try to get from cache
            try:
                cached_response = self._cache_llm_response(message_hash, context_hash)
                if cached_response:
                    return cached_response
            except Exception:
                pass  # Cache miss, continue with generation
            
            system_prompt = """You are a Creative AI assistant specialized in generating innovative ideas. 
            Focus on providing unique, actionable suggestions while considering multiple perspectives.
            When provided with context, use it to enhance your response but maintain a natural conversational tone.
            Don't explicitly mention the context unless asked about sources."""
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add context if available
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Here is some relevant information to consider:\n{context}"
                })
            
            # Add user message
            messages.append({"role": "user", "content": message})
            
            completion = await groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=messages,
                temperature=0.8,
                stream=False
            )
            
            response = completion.choices[0].message.content
            
            # Cache the response
            self._cache_llm_response.cache_clear()  # Clear old cache entry
            self._cache_llm_response(message_hash, context_hash)  # Cache new response
            
            return response
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")

# Create singleton instance
chatbot = CreativeAIChatbot()