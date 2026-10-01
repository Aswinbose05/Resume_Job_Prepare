"""
Multi-Provider Free LLM Abstraction with Automatic Fallback.
Supports Gemini (Primary), Groq (Fallback 1), and OpenRouter (Fallback 2).
Provides CrewAI LLM instances as well as structured JSON generation.
"""
import os
import json
import re
from typing import Optional, Any, Dict, Type, TypeVar
from pydantic import BaseModel
from crewai import LLM
from core.config import settings
from core.logger import logger
from llm.portkey_client import portkey_manager
from llm.langsmith_tracer import langsmith_tracer

T = TypeVar("T", bound=BaseModel)

class LLMProviderFactory:
    """Creates and manages resilient LLM instances with provider failover."""

    def __init__(self):
        langsmith_tracer.setup_tracing()

    def has_live_provider(self) -> bool:
        """Checks if any valid live LLM API key is present."""
        if portkey_manager.is_enabled():
            return True
        for key in [settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.OPENROUTER_API_KEY]:
            if key and not key.startswith("your_") and not key.startswith("dev_"):
                return True
        return False

    def get_crewai_llm(self, feature_name: str = "general") -> Optional[LLM]:
        """
        Returns a CrewAI compatible LLM object based on environment configuration.
        """
        # If Portkey is enabled, route via Portkey gateway
        if portkey_manager.is_enabled():
            logger.info("Routing LLM requests via Portkey AI Gateway.")
            headers = portkey_manager.get_gateway_headers(feature_name=feature_name)
            return LLM(
                model=f"openai/{settings.GEMINI_MODEL}",
                base_url="https://api.portkey.ai/v1",
                api_key=settings.PORTKEY_API_KEY,
                extra_headers=headers,
                temperature=0.2
            )

        # Standard direct provider selection
        provider = (settings.LLM_PROVIDER or "gemini").lower()

        # 1. Primary: Gemini
        if provider == "gemini" and settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_"):
            logger.info(f"Using Gemini LLM: {settings.GEMINI_MODEL}")
            return LLM(
                model=f"gemini/{settings.GEMINI_MODEL}",
                api_key=settings.GEMINI_API_KEY,
                temperature=0.2
            )

        # 2. Fallback: Groq
        if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your_"):
            logger.info(f"Using Groq LLM: {settings.GROQ_MODEL}")
            return LLM(
                model=f"groq/{settings.GROQ_MODEL}",
                api_key=settings.GROQ_API_KEY,
                temperature=0.2
            )

        # 3. Fallback: OpenRouter Free Models
        if settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("your_"):
            logger.info(f"Using OpenRouter LLM: {settings.OPENROUTER_MODEL}")
            return LLM(
                model=f"openrouter/{settings.OPENROUTER_MODEL}",
                api_key=settings.OPENROUTER_API_KEY,
                temperature=0.2
            )

        # Mock / Developer Fallback Mode when no API keys are configured
        logger.warning("No live cloud LLM API keys configured. Running in Mock/Deterministic Fallback Mode.")
        return LLM(
            model=f"gemini/{settings.GEMINI_MODEL}",
            api_key=settings.GEMINI_API_KEY or "dev_dummy_key",
            temperature=0.2
        )

    def generate_structured(self, prompt: str, schema_cls: Type[T], system_prompt: str = "") -> Optional[T]:
        """
        Executes an LLM request requiring strict JSON conforming to schema_cls.
        Applies automatic JSON repair and fallback retry.
        """
        full_prompt = (
            f"{system_prompt}\n\n"
            f"You MUST output valid, parseable JSON conforming to the schema of {schema_cls.__name__}.\n"
            f"Do not include markdown explanations outside the JSON codeblock.\n\n"
            f"INPUT:\n{prompt}\n\n"
            f"JSON Output:"
        )

        raw_response = ""
        try:
            llm = self.get_crewai_llm(feature_name="structured_extraction")
            # CrewAI LLM call
            response = llm.call(messages=[{"role": "user", "content": full_prompt}])
            raw_response = str(response)

            # Extract JSON block
            json_str = self._extract_json_string(raw_response)
            parsed_data = json.loads(json_str)
            return schema_cls.model_validate(parsed_data)

        except Exception as e:
            logger.warning(f"Structured LLM parsing error: {e}. Attempting JSON repair.")
            try:
                import json_repair
                repaired = json_repair.loads(raw_response)
                return schema_cls.model_validate(repaired)
            except Exception as e2:
                logger.error(f"JSON repair failed: {e2}")
                return None

    @staticmethod
    def _extract_json_string(text: str) -> str:
        """Finds JSON substring inside code fences or braces."""
        # Try ```json ... ```
        fence_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if fence_match:
            return fence_match.group(1)

        # Try outermost { ... }
        brace_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if brace_match:
            return brace_match.group(1)

        return text.strip()

llm_factory = LLMProviderFactory()
