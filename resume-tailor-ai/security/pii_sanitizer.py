"""
Personally Identifiable Information (PII) Detection & Sanitization.
Detects sensitive contact numbers, emails, addresses, and provides reversible masking.
"""
import re
from typing import Dict, Tuple, List
from core.logger import logger
from models.security_models import SecurityEvent, SecurityEventType, SeverityLevel

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
PHONE_REGEX = re.compile(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}\b')
LINKEDIN_REGEX = re.compile(r'https?://(?:www\.)?linkedin\.com/in/[\w-]+/?', re.IGNORECASE)
GITHUB_REGEX = re.compile(r'https?://(?:www\.)?github\.com/[\w-]+/?', re.IGNORECASE)

class PIISanitizer:
    """Detects and redacts PII before outbound LLM transmission."""

    @staticmethod
    def detect_pii(text: str) -> List[Dict[str, str]]:
        """Scans for detected PII elements."""
        detected = []
        if not text:
            return detected

        for email in EMAIL_REGEX.findall(text):
            detected.append({"type": "EMAIL", "value": email})

        # Match phone numbers (filter out short strings or pure years)
        for phone in PHONE_REGEX.findall(text):
            raw_phone = "".join(phone).strip()
            digits = re.sub(r'\D', '', raw_phone)
            if 10 <= len(digits) <= 15:
                detected.append({"type": "PHONE", "value": raw_phone})

        return detected

    @staticmethod
    def mask_pii(text: str) -> Tuple[str, Dict[str, str]]:
        """
        Masks PII with reversible surrogate tokens.
        Returns: (masked_text, mapping_dict)
        """
        if not text:
            return text, {}

        mapping = {}

        # 1. Mask Emails
        def email_repl(match):
            val = match.group(0)
            token = f"[EMAIL_{len(mapping)+1}]"
            mapping[token] = val
            return token

        masked = EMAIL_REGEX.sub(email_repl, text)

        # 2. Mask Phone numbers
        def phone_repl(match):
            val = match.group(0)
            digits = re.sub(r'\D', '', val)
            if 10 <= len(digits) <= 15:
                token = f"[PHONE_{len(mapping)+1}]"
                mapping[token] = val
                return token
            return val

        masked = PHONE_REGEX.sub(phone_repl, masked)

        return masked, mapping

    @staticmethod
    def unmask_pii(masked_text: str, mapping: Dict[str, str]) -> str:
        """Restores original PII values from token mapping."""
        if not masked_text or not mapping:
            return masked_text

        result = masked_text
        for token, original in mapping.items():
            result = result.replace(token, original)
        return result

pii_sanitizer = PIISanitizer()
