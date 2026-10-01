"""
Structured logging module for AI Career Intelligence Platform.
Ensures sensitive tokens, passwords, and PII are redacted from logs.
"""
import logging
import re
import sys
from typing import Any

SENSITIVE_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'),
    re.compile(r'\b[A-Za-z0-9_-]{32,}\b'),  # Long hex/base64 tokens
]

class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        # Redact labeled secrets
        orig = SENSITIVE_PATTERNS[0].sub(r'\1: [REDACTED]', orig)
        # Redact standalone long tokens
        orig = SENSITIVE_PATTERNS[1].sub('[REDACTED_TOKEN]', orig)
        return orig

def setup_logger(name: str = "career_intelligence", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = setup_logger()
