from typing import Dict, Optional, List, Tuple
from app.models.model import Message, ChatSession, ChatResponse
from uuid import UUID, uuid4
from ai21 import AI21Client
from ai21.models.chat import UserMessage, SystemMessage
from app.config.config import get_settings
from functools import lru_cache
import json
import hashlib
import logging
import time
from datetime import datetime, timedelta
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
# Initialize AI21 client with API key
ai21_client = AI21Client(api_key=settings.AI21_API_KEY)

class CreativeAIChatbot:
    def __init__(self):
        self.sessions: Dict[str, Dict[UUID, ChatSession]] = {}  # Map user_id to their sessions
        self.session_expiry: Dict[UUID, float] = {}  # Track when sessions expire
        self.SESSION_TIMEOUT = 60 * 60  # Sessions expire after 1 hour of inactivity

    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[UUID] = None,
        deep_research: bool = False
    ) -> ChatSession:
        logger.info(f"Processing message for user: {user_id} (deep_research: {deep_research})")
        
        # Get or create session
        session = self._get_or_create_session(user_id, session_id)
        
        # Add user message
        session.messages.append(Message(content=message, role="user"))
        
        try:
            combined_context = {"research_findings": [], "research_sources": []}
            
            # Only perform research if deep_research is True
            if deep_research:
                logger.info("Starting deep research process...")
                research_result = await research_engine.research_topic(
                    query=message,
                    context="",
                    deep_research=True
                )
                
                if research_result and research_result.findings:
                    combined_context["research_findings"] = research_result.findings
                    combined_context["research_sources"] = research_result.sources
                    logger.info(f"Deep research completed with {len(research_result.findings)} findings")
            
            # Generate response
            response = await self._generate_response(message, combined_context, session)
            session.messages.append(Message(content=response, role="assistant"))
            
            # Update session expiry time
            self._update_session_expiry(session.id)
            
            return session
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            raise

    def _get_or_create_session(self, user_id: str, session_id: Optional[UUID] = None) -> ChatSession:
        """
        Get an existing session or create a new one for the given user
        
        Args:
            user_id: ID of the user
            session_id: Optional ID of an existing session
            
        Returns:
            The session
        """
        # Create user's session dictionary if it doesn't exist
        if user_id not in self.sessions:
            self.sessions[user_id] = {}
            
        # Clean expired sessions periodically
        self._clean_expired_sessions()
            
        # If session_id is provided and exists for this user, return it
        if session_id and session_id in self.sessions[user_id]:
            logger.info(f"Retrieved existing session {session_id} for user {user_id}")
            session = self.sessions[user_id][session_id]
            return session
            
        # Otherwise create a new session
        session = ChatSession(user_id=user_id)
        self.sessions[user_id][session.id] = session
        self._update_session_expiry(session.id)
        logger.info(f"Created new session {session.id} for user {user_id}")
        
        return session
        
    def _update_session_expiry(self, session_id: UUID) -> None:
        """Update the expiry time for a session"""
        self.session_expiry[session_id] = time.time() + self.SESSION_TIMEOUT
        
    def _clean_expired_sessions(self) -> None:
        """Remove expired sessions to prevent memory leaks"""
        current_time = time.time()
        expired_sessions = [sid for sid, expiry in self.session_expiry.items() if expiry < current_time]
        
        if expired_sessions:
            logger.info(f"Cleaning {len(expired_sessions)} expired sessions")
            
            # Remove expired sessions from each user's sessions dict
            for user_id, sessions in list(self.sessions.items()):
                for session_id in list(sessions.keys()):
                    if session_id in expired_sessions:
                        del sessions[session_id]
                
                # Remove user entry if they have no sessions
                if not sessions:
                    del self.sessions[user_id]
            
            # Remove from expiry tracking
            for session_id in expired_sessions:
                if session_id in self.session_expiry:
                    del self.session_expiry[session_id]

    @lru_cache(maxsize=1000)
    def _cache_llm_response(self, message_hash: str, context_hash: str) -> str:
        """Cache for LLM responses"""
        return ""  # Empty string triggers cache miss

    async def _generate_response(self, message: str, combined_context: Dict, session: ChatSession) -> str:
        try:
            # Add debug logging for research findings
            logger.debug(f"Research findings: {bool(combined_context.get('research_findings'))}")
            
            # Format context based on whether we have research findings
            context = ""
            messages = [SystemMessage(content=self._get_system_prompt())]
            
            # Check if we have research findings and add them to context
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
                
                # Set full context
                context = research_context + "\n\n" + self._format_research_context(combined_context)
            else:
                # Use standard research context format if no specific findings
                context = self._format_research_context(combined_context)
            
            # Add context if we have any
            if context:
                messages.append(SystemMessage(content=f"Here is relevant research information:\n{context}"))
            
            # Add user message
            messages.append(UserMessage(content=message))
            
            # Calculate hashes for caching
            message_hash = hashlib.sha256(message.encode()).hexdigest()
            context_hash = hashlib.sha256(context.encode()).hexdigest()
            
            # Try to get from cache
            try:
                cached_response = self._cache_llm_response(message_hash, context_hash)
                if cached_response:
                    return cached_response
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {str(e)}")
            
            # Use AI21 Client for chat completion with a single model
            response = ai21_client.chat.completions.create(
                model="jamba-large-1.6",
                messages=messages,
                temperature=0.8,
                max_tokens=500,
                top_p=0.95,
                presence_penalty=0.6,
                frequency_penalty=0.5,
                response_format={"type": "text"},
                stop=None,
            )
            
            response_text = response.choices[0].message.content
            
            # Cache the response
            self._cache_llm_response.cache_clear()
            self._cache_llm_response(message_hash, context_hash)
            
            return response_text
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise Exception(f"Error generating response: {str(e)}")

    def _format_research_context(self, combined_context: Dict) -> str:
        """Format research findings into a single context"""
        context_parts = []
        
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