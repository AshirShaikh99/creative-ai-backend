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
        logger.info(f"Processing message for user: {user_id} (deep_research: {deep_research})")
        logger.debug(f"Message length: {len(message)} characters")
        
        # Get or create session
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            logger.info(f"Using existing session: {session_id}")
        else:
            session = ChatSession(user_id=user_id)
            self.sessions[session.id] = session
            logger.info(f"Created new session: {session.id}")
        
        # Add user message
        user_message = Message(content=message, role="user")
        session.messages.append(user_message)
        logger.debug(f"Added user message to session. Total messages: {len(session.messages)}")
        
        try:
            logger.info("Starting semantic search...")
            search_results = await self.semantic_search.search(
                query=message,
                collection_name="documents",
                limit=3,
                score_threshold=0.7
            )
            logger.info(f"Search completed. Found {len(search_results)} results")
            
            logger.info("Starting research process...")
            formatted_context = self._format_context(search_results)
            logger.debug(f"Formatted context length: {len(formatted_context)} characters")
            
            research_result = await research_engine.research_topic(
                query=message,
                context=formatted_context,
                deep_research=deep_research
            )
            logger.info(f"Research completed. Found {len(research_result.findings)} findings")
            
            combined_context = {
                "search_results": search_results,
                "research_findings": research_result.findings if research_result else [],
                "research_sources": research_result.sources if research_result else []
            }
            logger.debug(f"Combined context created with {len(combined_context['search_results'])} search results and {len(combined_context['research_findings'])} findings")
            
            logger.info("Generating final response...")
            response = await self._generate_response(message, combined_context, session)
            logger.info(f"Response generated (length: {len(response)} characters)")
            logger.info(f"Response type: {'Deep Research' if deep_research else 'Standard Chat'}")
            logger.info("Response content:")
            logger.info("=" * 50)
            logger.info(response)
            logger.info("=" * 50)
            
            assistant_message = Message(content=response, role="assistant")
            session.messages.append(assistant_message)
            logger.debug(f"Added assistant response. Session now has {len(session.messages)} messages")
            
            logger.info(f"Message processing completed successfully for user: {user_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error processing message for user {user_id}: {str(e)}", exc_info=True)
            logger.debug(f"Session state at error: {len(session.messages)} messages")
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
            # Add debug logging for research findings
            logger.debug(f"Research findings: {bool(combined_context.get('research_findings'))}")
            
            # Check if we have research findings and they're from the research engine
            if (combined_context.get("research_findings") and 
                isinstance(combined_context["research_findings"], list) and 
                len(combined_context["research_findings"]) > 0):
                
                research_finding = combined_context["research_findings"][0]
                logger.info(f"Using research findings for response generation: {research_finding.get('source')}")
                
                # Prioritize research content in the context
                research_context = ""
                if research_finding.get('summary'):
                    research_context += f"Research Summary:\n{research_finding['summary']}\n\n"
                if research_finding.get('details'):
                    research_context += "Key Findings:\n" + "\n".join(f"- {detail}" for detail in research_finding['details'])
                
                # Combine with other context but prioritize research findings
                context = research_context + "\n\n" + self._format_combined_context(combined_context)
                
                messages = [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "system", "content": f"Here is relevant research information:\n{context}"},
                    {"role": "user", "content": message}
                ]
                
                completion = await groq_client.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=messages,
                    temperature=0.8,
                    stream=False
                )
                
                return completion.choices[0].message.content

            # Otherwise, proceed with normal response generation
            context = self._format_combined_context(combined_context)
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
            
            response = f"{completion.choices[0].message.content}"

            
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
        
        # Add research findings with safe key access
        for finding in combined_context["research_findings"]:
            # The topic is the same as the original query in research findings
            summary = finding.get('summary', '')
            details = finding.get('details', [])
            
            if summary:
                context_parts.append(f"Research Finding:\n{summary}\n")
            if details:
                context_parts.append("Details:\n" + "\n".join(f"- {detail}" for detail in details) + "\n")
        
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