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
            logger.info(f"Starting research for query: '{query}' (deep_research: {deep_research})")
            logger.debug(f"Context length: {len(context) if context else 0} characters")
            
            if deep_research:
                logger.info("Initiating deep research analysis")
                # Perform deep research using Groq
                research_prompt = f"""
                🎨 **You are a Creatigen Researcher – The Art & Science of Groundbreaking Ideas** 🚀  

                🔍 **Topic of Exploration:** {query}  
                📌 **Context Provided:** {context if context else "No additional context available"}  

                ### 🧠 **Your Role: A Creatigen Researcher**  
                You are not just analyzing—you are **discovering, imagining, and redefining**. Your task is to explore this topic with the mind of a strategist, the curiosity of a scientist, and the vision of a creator.  

                ### ✨ **The Deep Exploration Process:**  
                1️⃣ **Deconstruct & Rebuild:** Break the topic down into fundamental truths, then reassemble it in a way that **unlocks new possibilities.**  
                2️⃣ **Multi-Perspective Thinking:** Examine the subject from different angles—**historical, technological, emotional, and futuristic.**  
                3️⃣ **Challenge the Ordinary:** What if we flipped conventional wisdom? Where do the **hidden opportunities** lie?  

                ### ❤️ **Emotion & Impact – Making Ideas Matter**  
                - Why does this subject evoke curiosity, urgency, or inspiration?  
                - How does it **intersect with human creativity, innovation, or transformation**?  

                ### 🎯 **The Expert Blueprint – Turning Insight into Vision**  
                - **Strategic Breakthroughs:** What powerful, disruptive insights emerge from this?  
                - **Future Forecast:** Where is this concept heading in 3, 5, or 10 years?  
                - **Creative Leverage:** What are the most **actionable, high-impact ideas** that can reshape industries, businesses, or experiences?  

                💡 **Your response should do more than inform—it should spark imagination, provoke thought, and inspire action!**  
                """


                logger.debug(f"Sending research prompt to Groq (length: {len(research_prompt)})")
                completion = await self.groq_client.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[{"role": "user", "content": research_prompt}],
                    temperature=0.7
                )
                
                analysis = completion.choices[0].message.content
                logger.info(f"Received analysis from Groq (length: {len(analysis)})")
                
                finding = {
                    "topic": query,
                    "summary": analysis,
                    "details": [context] if context else [],
                    "source": "deep-research-analysis",
                    "relevance": 1.0
                }
                logger.debug("Deep research finding created")
            else:
                logger.info("Using simple context-based analysis")
                # Use existing simple context-based analysis
                finding = {
                    "topic": query,
                    "summary": "Context-based research",
                    "details": [context] if context else [],
                    "source": "context-analysis",
                    "relevance": 1.0
                }
                logger.debug("Context-based finding created")
            
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
            
            logger.info(f"Research completed successfully for query: '{query}'")
            logger.debug(f"Research result contains {len(research_result.findings)} findings")
            return research_result
            
        except Exception as e:
            logger.error(f"Research error for query '{query}': {str(e)}", exc_info=True)
            logger.debug(f"Context at time of error: {context[:200]}..." if context else "No context")
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