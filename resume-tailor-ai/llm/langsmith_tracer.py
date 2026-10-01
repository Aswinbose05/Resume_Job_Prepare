"""
LangSmith Tracing and Evaluation Integration.
Enables distributed tracing across CrewAI agents, LLM spans, and tool calls.
"""
import os
from typing import Dict, Any, Optional
from core.config import settings
from core.logger import logger

class LangSmithTracer:
    """Configures LangSmith environment tracing and sanitized metadata."""

    @staticmethod
    def setup_tracing():
        """Applies LangSmith environment variables if configured."""
        if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY and not settings.LANGSMITH_API_KEY.startswith("your_"):
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
            logger.info(f"LangSmith distributed tracing enabled for project: {settings.LANGSMITH_PROJECT}")
        else:
            os.environ["LANGCHAIN_TRACING_V2"] = "false"

    @staticmethod
    def get_run_metadata(agent_name: str, task_name: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Creates sanitized metadata for agent spans without leaking raw PII."""
        meta = {
            "agent": agent_name,
            "task": task_name,
            "app_version": settings.APP_VERSION,
        }
        if extra:
            # Filter out raw resume or raw text keys
            for k, v in extra.items():
                if k.lower() not in ["resume_text", "raw_text", "email", "phone", "password"]:
                    meta[k] = v
        return meta

langsmith_tracer = LangSmithTracer()
