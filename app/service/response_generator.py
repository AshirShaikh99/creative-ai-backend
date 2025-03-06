import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
import groq
from app.config.config import get_settings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize Groq client
groq_client = groq.AsyncClient(api_key=settings.GROQ_API_KEY)

# Initialize Qdrant client for memory storage
qdrant_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


async def generate_response(
    query: str,
    conversation_history: List[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    creative_level: float = 0.8
) -> str:
    """
    Generate an AI response using Groq API.
    
    Args:
        query: User query text
        conversation_history: Previous conversation messages
        session_id: Session identifier for context persistence
        creative_level: Creativity level (0.0 to 1.0)
        
    Returns:
        Generated response text
    """
    if conversation_history is None:
        conversation_history = []
    
    # Retrieve relevant context from memory if session_id is provided
    context = ""
    if session_id:
        try:
            memory_entries = await asyncio.to_thread(
                qdrant_client.search,
                collection_name="conversation_memory",
                query_vector=[0] * 384,  # Placeholder vector, we're searching by ID
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="session_id",
                            match=MatchValue(value=session_id)
                        )
                    ]
                ),
                limit=10
            )
            
            if memory_entries:
                context = "\n".join([entry.payload.get("content", "") for entry in memory_entries])
        except Exception as e:
            logger.error(f"Error retrieving memory: {str(e)}")
    
    # Prepare the messages for the API
    messages = [{"role": "system", "content": f"""You are a creative voice assistant. 
Respond in a natural, conversational way. Keep responses concise but informative.
{context}"""}]
    
    # Add conversation history
    messages.extend(conversation_history)
    
    # Add the current user query
    messages.append({"role": "user", "content": query})
    
    try:
        # Call Groq API
        response = await groq_client.chat.completions.create(
            model=settings.SMART_LLM,
            messages=messages,
            temperature=creative_level,
            max_tokens=1024,
        )
        
        ai_response = response.choices[0].message.content
        
        # Store the conversation in memory if session_id is provided
        if session_id:
            try:
                await asyncio.to_thread(
                    qdrant_client.upsert,
                    collection_name="conversation_memory",
                    points=[{
                        "id": f"{session_id}_{len(conversation_history)}",
                        "vector": [0] * 384,  # Placeholder vector
                        "payload": {
                            "session_id": session_id,
                            "content": f"User: {query}\nAssistant: {ai_response}",
                            "timestamp": asyncio.to_thread(lambda: int(asyncio.get_event_loop().time()))
                        }
                    }]
                )
            except Exception as e:
                logger.error(f"Error storing memory: {str(e)}")
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "I'm sorry, I'm having trouble processing your request right now."


async def stream_response(
    query: str,
    conversation_history: List[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    creative_level: float = 0.8
):
    """
    Stream AI response using Groq API.
    
    Args:
        query: User query text
        conversation_history: Previous conversation messages
        session_id: Session identifier for context persistence
        creative_level: Creativity level (0.0 to 1.0)
        
    Yields:
        Response text chunks
    """
    if conversation_history is None:
        conversation_history = []
    
    # Retrieve relevant context from memory if session_id is provided
    context = ""
    if session_id:
        try:
            memory_entries = await asyncio.to_thread(
                qdrant_client.search,
                collection_name="conversation_memory",
                query_vector=[0] * 384,  # Placeholder vector, we're searching by ID
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="session_id",
                            match=MatchValue(value=session_id)
                        )
                    ]
                ),
                limit=10
            )
            
            if memory_entries:
                context = "\n".join([entry.payload.get("content", "") for entry in memory_entries])
        except Exception as e:
            logger.error(f"Error retrieving memory: {str(e)}")
    
    # Prepare the messages for the API
    messages = [{"role": "system", "content": f"""You are a creative voice assistant. 
Respond in a natural, conversational way. Keep responses concise but informative.
{context}"""}]
    
    # Add conversation history
    messages.extend(conversation_history)
    
    # Add the current user query
    messages.append({"role": "user", "content": query})
    
    try:
        # Stream response from Groq API
        response_stream = await groq_client.chat.completions.create(
            model=settings.SMART_LLM,
            messages=messages,
            temperature=creative_level,
            max_tokens=1024,
            stream=True
        )
        
        full_response = ""
        
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content
        
        # Store the conversation in memory if session_id is provided
        if session_id:
            try:
                await asyncio.to_thread(
                    qdrant_client.upsert,
                    collection_name="conversation_memory",
                    points=[{
                        "id": f"{session_id}_{len(conversation_history)}",
                        "vector": [0] * 384,  # Placeholder vector
                        "payload": {
                            "session_id": session_id,
                            "content": f"User: {query}\nAssistant: {full_response}",
                            "timestamp": asyncio.to_thread(lambda: int(asyncio.get_event_loop().time()))
                        }
                    }]
                )
            except Exception as e:
                logger.error(f"Error storing memory: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error streaming response: {str(e)}")
        yield "I'm sorry, I'm having trouble processing your request right now."
