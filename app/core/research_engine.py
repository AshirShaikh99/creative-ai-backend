from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from app.config.config import get_settings
from app.models.model import ResearchResult, ResearchTopic
from gpt_researcher import GPTResearcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)
settings = get_settings()

class GPTResearchEngine:
    def __init__(self):
        import os
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
        os.environ["FAST_LLM"] = "groq"  # Specify provider only
        os.environ["SMART_LLM"] = "groq"  # Specify provider only
        os.environ["LLM_MODEL"] = "mixtral-8x7b-32768"  # Specify model separately
        
        self.fast_llm = "mixtral-8x7b-32768"
        self.smart_llm = "mixtral-8x7b-32768"

    async def research_topic(self, query: str, context: Optional[str] = None, deep_research: bool = False) -> ResearchResult:
        try:
            logger.info(f"Starting research for query: '{query}' (deep_research: {deep_research})")
            logger.debug(f"Context length: {len(context) if context else 0} characters")

            research_query = query
            if context:
                research_query = f"{query}\nContext: {context}"
                logger.debug(f"Combined query with context: {research_query[:200]}...")

            # Choose the model dynamically
            selected_model = self.smart_llm if deep_research else self.fast_llm
            logger.info(f"Using model: {selected_model}")

            # Initialize researcher
            researcher = GPTResearcher(
                query=research_query,
                report_type="research_report" if deep_research else "quick_report",
                config_path=None  # Let GPTResearcher use its default config
            )

            logger.info("Starting research process...")
            if not await researcher.conduct_research():
                raise Exception("Research process failed to complete")

            logger.info("Generating research report...")
            research_report = await researcher.write_report()
            if not research_report:
                raise Exception("Failed to generate research report")
            
            logger.debug(f"Research report type: {type(research_report)}")

            # Process research results
            logger.info("Processing research results...")
            findings = []
            if isinstance(research_report, dict):
                if not research_report.get("summary") and not research_report.get("key_findings"):
                    raise Exception("Research report is empty")
                logger.debug("Processing dictionary research report")
                findings.append({
                    "topic": query,
                    "summary": research_report.get("summary", ""),
                    "details": research_report.get("key_findings", []),
                    "source": "gpt-researcher",
                    "relevance": 1.0
                })
            else:
                logger.debug("Processing string research report")
                findings.append({
                    "topic": query,
                    "summary": research_report if isinstance(research_report, str) else str(research_report),
                    "details": [],
                    "source": "gpt-researcher",
                    "relevance": 1.0
                })

            research_result = ResearchResult(
                topic=query,
                findings=findings,
                sources=getattr(researcher, "research_summary", []),
                confidence_score=1.0,
                metadata={
                    "context": context,
                    "research_type": "deep_research" if deep_research else "quick_research",
                    "timestamp": datetime.now().isoformat(),
                    "report_type": "research_report" if deep_research else "quick_report",
                    "model": selected_model
                }
            )

            logger.info(f"Research completed successfully for query: '{query}'")
            logger.debug(f"Research result contains {len(research_result.findings)} findings")
            return research_result

        except Exception as e:
            logger.error(f"Research error for query '{query}': {str(e)}", exc_info=True)
            raise Exception(f"Research failed: {str(e)}")
            return ResearchResult(
                topic=query,
                findings=[{"error": str(e), "summary": "Research failed"}],
                sources=[],
                confidence_score=0.0,
                metadata={"error": str(e)}
            )

# Create singleton instance
research_engine = GPTResearchEngine()
