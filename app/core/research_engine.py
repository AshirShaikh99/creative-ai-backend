# File: app/core/research_engine.py
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import json
from pathlib import Path
from functools import lru_cache
from groq import AsyncGroq
from app.config.config import get_settings
from app.models.model import ResearchResult, ResearchTopic

logger = logging.getLogger(__name__)
settings = get_settings()

class GPTResearchEngine:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        
    async def research_topic(self, query: str, context: Optional[str] = None, deep_research: bool = False) -> ResearchResult:
        try:
            if deep_research:
                # Perform deep research using Groq
                research_prompt = f"""Conduct a deep analysis on this topic:
                Query: {query}
                Context: {context if context else 'No additional context'}
                
                Provide:
                1. Comprehensive analysis
                2. Multiple perspectives
                3. Potential implications
                4. Related concepts
                5. Supporting evidence"""

                completion = await self.groq_client.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[{"role": "user", "content": research_prompt}],
                    temperature=0.7
                )
                
                analysis = completion.choices[0].message.content
                
                finding = {
                    "topic": query,
                    "summary": analysis,
                    "details": [context] if context else [],
                    "source": "deep-research-analysis",
                    "relevance": 1.0
                }
            else:
                # Use existing simple context-based analysis
                finding = {
                    "topic": query,
                    "summary": "Context-based research",
                    "details": [context] if context else [],
                    "source": "context-analysis",
                    "relevance": 1.0
                }
            
            research_result = ResearchResult(
                topic=query,
                findings=[finding],
                sources=["deep-research" if deep_research else "context-based-analysis"],
                confidence_score=1.0,
                metadata={
                    "context": context,
                    "research_type": "deep_research" if deep_research else "context_based",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return research_result
            
        except Exception as e:
            logger.error(f"Research error: {str(e)}")
            return ResearchResult(
                topic=query,
                findings=[{"error": str(e), "summary": "Research failed"}],
                sources=[],
                confidence_score=0.0,
                metadata={"error": str(e)}
            )

    def _generate_cache_key(self, query: str, context: Optional[str] = None) -> str:
        """
        Generate cache key for research results
        """
        key_parts = [query]
        if context:
            key_parts.append(context)
        return ":".join(key_parts)

# Create singleton instance
research_engine = GPTResearchEngine()