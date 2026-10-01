"""
Security models and schemas for the AI Security Layer.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class SeverityLevel(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SecurityEventType(str, Enum):
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    JAILBREAK_ATTEMPT = "JAILBREAK_ATTEMPT"
    SSRF_BLOCKED = "SSRF_BLOCKED"
    INVALID_FILE_SIGNATURE = "INVALID_FILE_SIGNATURE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EXCESSIVE_PAGES = "EXCESSIVE_PAGES"
    PII_DETECTED = "PII_DETECTED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"

class SecurityEvent(BaseModel):
    event_type: SecurityEventType
    severity: SeverityLevel
    description: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)

class SecurityScanResult(BaseModel):
    is_safe: bool = True
    blocked: bool = False
    block_reason: Optional[str] = None
    events: List[SecurityEvent] = Field(default_factory=list)
    sanitized_content: Optional[str] = None
