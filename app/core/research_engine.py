from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import json
from pathlib import Path
from functools import lru_cache
from groq import AsyncGroq
from app.config.config import get_settings
from app.models.model import ResearchResult, ResearchTopic
from gpt_researcher import GPTResearcher

logger = logging.getLogger(__name__)
settings = get_settings()

class GPTResearchEngine:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        # Define researcher config with Groq Mixtral model
        self.researcher_config = {
            "llm": {
                "api_key": settings.GROQ_API_KEY,
                "provider": "groq",
                "model": "mixtral-8x7b-32768",
                "temperature": 0.7
            },
            "report_format": "markdown",
            "agent": {
                "max_iterations": 3,
                "search_type": "basic"
            },
            "search": {
                "search_depth": 3,
                "enable_web_search": True
            }
        }
        
    async def research_topic(self, query: str, context: Optional[str] = None, deep_research: bool = False) -> ResearchResult:
        try:
            logger.info(f"Starting research for query: '{query}' (deep_research: {deep_research})")
            logger.debug(f"Context length: {len(context) if context else 0} characters")
            
            # Update config based on research depth
            if deep_research:
                self.researcher_config["agent"]["max_iterations"] = 5
                self.researcher_config["search"]["search_depth"] = 5
            else:
                self.researcher_config["agent"]["max_iterations"] = 3
                self.researcher_config["search"]["search_depth"] = 3
            
            research_query = query
            if context:
                research_query = f"{query}\nContext: {context}"
            
            # Initialize researcher with our config
            researcher = GPTResearcher(
                query=research_query,
                report_type="research_report" if deep_research else "quick_report",
                config=self.researcher_config
            )
            
            logger.info("Conducting research")
            await researcher.conduct_research()
            
            logger.info("Generating research report")
            research_report = await researcher.write_report()
            
            # Process research results
            findings = []
            if isinstance(research_report, dict):
                finding = {
                    "topic": query,
                    "summary": research_report.get("summary", ""),
                    "details": research_report.get("key_findings", []),
                    "source": "gpt-researcher",
                    "relevance": 1.0
                }
                findings.append(finding)
            else:
                finding = {
                    "topic": query,
                    "summary": research_report if isinstance(research_report, str) else str(research_report),
                    "details": [],
                    "source": "gpt-researcher",
                    "relevance": 1.0
                }
                findings.append(finding)
            
            research_result = ResearchResult(
                topic=query,
                findings=findings,
                sources=researcher.research_summary if hasattr(researcher, 'research_summary') else [],
                confidence_score=1.0,
                metadata={
                    "context": context,
                    "research_type": "deep_research" if deep_research else "quick_research",
                    "timestamp": datetime.now().isoformat(),
                    "report_type": "research_report" if deep_research else "quick_report",
                    "model": "mixtral-8x7b-32768"
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