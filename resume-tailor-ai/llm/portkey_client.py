"""
Portkey AI Gateway Integration.
Provides enterprise AI gateway capabilities: model routing, virtual keys, guardrails, and request telemetry.
"""
from typing import Dict, Optional, Any
from core.config import settings
from core.logger import logger

class PortkeyManager:
    """Manages Portkey Gateway headers and routing metadata."""

    @staticmethod
    def get_gateway_headers(
        trace_id: Optional[str] = None,
        feature_name: str = "career_intelligence",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Builds standardized Portkey headers for model routing and guardrails.
        """
        if not settings.PORTKEY_API_KEY:
            return {}

        headers = {
            "x-portkey-api-key": settings.PORTKEY_API_KEY,
            "x-portkey-trace-id": trace_id or f"trace_{feature_name}",
        }

        if settings.PORTKEY_VIRTUAL_KEY:
            headers["x-portkey-virtual-key"] = settings.PORTKEY_VIRTUAL_KEY

        if settings.PORTKEY_CONFIG_ID:
            headers["x-portkey-config"] = settings.PORTKEY_CONFIG_ID

        # Add custom request metadata
        meta = {
            "project": "ai-career-intelligence",
            "feature": feature_name,
            "env": "production" if not settings.DEBUG else "development"
        }
        if metadata:
            meta.update(metadata)

        for k, v in meta.items():
            headers[f"x-portkey-metadata-{k}"] = str(v)

        return headers

    @staticmethod
    def is_enabled() -> bool:
        """Checks if Portkey is configured with a valid key."""
        return bool(settings.PORTKEY_API_KEY and not settings.PORTKEY_API_KEY.startswith("your_"))

portkey_manager = PortkeyManager()
