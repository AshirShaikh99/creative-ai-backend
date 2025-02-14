from typing import Dict, Optional, List, Tuple
from app.models.model import Message, ChatSession, ChatResponse
from uuid import UUID
from groq import AsyncGroq
from app.config.config import get_settings
from app.service.qdrant_service import QdrantService
from app.utils.search import QdrantSearch, SearchResult
from functools import lru_cache
import json
import hashlib
import logging
from app.core.research_engine import research_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

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
        session_id: Optional[UUID] = None,
        deep_research: bool = False
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
        
        try:
            # First, get search results
            search_results = await self.semantic_search.search(
                query=message,
                collection_name="documents",
                limit=3,
                score_threshold=0.7
            )
            
            # Conduct research with search context
            research_result = await research_engine.research_topic(
                query=message,
                context=self._format_context(search_results),
                deep_research=deep_research  # Pass the deep_research parameter
            )
            
            # Combine search results and research findings for final response
            combined_context = {
                "search_results": search_results,
                "research_findings": research_result.findings,
                "research_sources": research_result.sources
            }
            
            # Generate final response using Groq
            response = await self._generate_response(message, combined_context, session)
            
            # Add assistant message
            assistant_message = Message(content=response, role="assistant")
            session.messages.append(assistant_message)
            
            return session
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise

    @lru_cache(maxsize=1000)
    def _format_context_cached(self, context_tuple: Tuple[Tuple[str, str, float, str], ...]) -> str:
        """Cached version of context formatting. Takes tuple for immutability."""
        if not context_tuple:
            return ""
            
        context_parts = []
        for source, content, score, metadata_type in context_tuple:
            context_parts.append(f"Context from {source}:\n{content}\n")
        
        return "\n".join(context_parts)
    
    def _format_context(self, search_results: List[SearchResult]) -> str:
        """Format search results into context for the LLM with caching"""
        # Convert SearchResult objects to tuple for caching
        context_tuple = tuple(
            (
                result.source if hasattr(result, 'source') else "unknown",
                result.content if hasattr(result, 'content') else "",
                float(result.score) if hasattr(result, 'score') else 0.0,
                result.metadata.get('type', '') if hasattr(result, 'metadata') else ""
            ) 
            for result in search_results
        )
        return self._format_context_cached(context_tuple)

    @lru_cache(maxsize=1000)
    def _cache_llm_response(self, message_hash: str, context_hash: str) -> str:
        """Cache for LLM responses"""
        return ""  # Empty string triggers cache miss

    async def _generate_response(self, message: str, combined_context: Dict, session: ChatSession) -> str:
        try:
            # Format combined context
            context = self._format_combined_context(combined_context)
            
            # Generate cache keys
            message_hash = hashlib.sha256(message.encode()).hexdigest()
            context_hash = hashlib.sha256(context.encode()).hexdigest()
            
            # Try to get from cache
            try:
                cached_response = self._cache_llm_response(message_hash, context_hash)
                if cached_response:
                    return cached_response
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {str(e)}")
            
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "system", "content": f"Here is relevant information from search and research:\n{context}"},
                {"role": "user", "content": message}
            ]
            
            completion = await groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=messages,
                temperature=0.8,
                stream=False
            )
            
            response = completion.choices[0].message.content
            
            # Cache the response
            self._cache_llm_response.cache_clear()
            self._cache_llm_response(message_hash, context_hash)
            
            return response
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise Exception(f"Error generating response: {str(e)}")

    def _format_combined_context(self, combined_context: Dict) -> str:
        """Format both search results and research findings into a single context"""
        context_parts = []
        
        # Add search results - handle SearchResult objects
        for result in combined_context["search_results"]:
            source = result.source if hasattr(result, 'source') else "unknown"
            content = result.content if hasattr(result, 'content') else ""
            context_parts.append(f"Search Result from {source}:\n{content}\n")
        
        # Add research findings
        for finding in combined_context["research_findings"]:
            context_parts.append(f"Research Finding on {finding['topic']}:\n{finding['summary']}\n")
            if finding.get('details'):
                context_parts.append("Details:\n" + "\n".join(finding['details']) + "\n")
        
        # Add research sources
        if combined_context["research_sources"]:
            context_parts.append("Additional Sources:\n" + "\n".join(combined_context["research_sources"]))
        
        return "\n".join(context_parts)

    def _get_system_prompt(self) -> str:
        """Return the system prompt"""
        return """You are Creatigen, a cutting-edge assistant designed to generate groundbreaking ideas across various domains, including technology, business, startups, design, and innovation. 

        Your primary goal is to provide **original, forward-thinking, and highly actionable suggestions** while exploring multiple perspectives. Your responses should inspire creativity, challenge conventional thinking, and encourage innovative problem-solving.
        
        ### Key Guidelines:
        - **Think beyond the ordinary** – propose ideas that push boundaries, disrupt industries, or introduce novel solutions.
        - **Contextual Awareness** – If relevant information is provided, integrate it seamlessly into your response without explicitly mentioning it unless asked.
        - **Conversational & Engaging** – Maintain a natural, inspiring, and motivating tone that encourages further exploration of ideas.
        - **Structure & Clarity** – Use Markdown formatting for better readability, including bullet points, headings, and code blocks where applicable.
        - **Diverse Perspectives** – Consider unconventional angles, emerging trends, and future possibilities to enrich your suggestions.
        
        Always aim to **spark curiosity, encourage innovation, and fuel creativity** in every response."""

# Create singleton instance
chatbot = CreativeAIChatbot()