from typing import Dict, Optional
from app.models.model import Message, ChatSession, ChatResponse  # Fixed import path
from uuid import UUID
from groq import AsyncGroq  # Changed to AsyncGroq
from app.config.config import get_settings

settings = get_settings()
groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)  # Changed to AsyncGroq

class CreativeAIChatbot:
    def __init__(self):
        self.sessions: Dict[UUID, ChatSession] = {}
        
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
        
        # Generate response
        response = await self._generate_response(message, session)
        
        # Add assistant message
        assistant_message = Message(content=response, role="assistant")
        session.messages.append(assistant_message)
        
        return session
    
    async def _generate_response(self, message: str, session: ChatSession) -> str:
        try:
            completion = await groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a Creative AI assistant specialized in generating innovative ideas. 
                        Focus on providing unique, actionable suggestions while considering multiple perspectives."""
                    },
                    {"role": "user", "content": message}
                ],
                temperature=0.8,
                stream=False  # Added to ensure non-streaming response
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")  # Changed to raise exception

# Create singleton instance
chatbot = CreativeAIChatbot()