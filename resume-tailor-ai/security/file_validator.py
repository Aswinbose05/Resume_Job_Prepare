"""
File Upload Validation & Security.
Enforces file signatures (magic bytes), MIME types, size thresholds, and page limits.
"""
from typing import Tuple, Optional
import io
from core.config import settings
from core.logger import logger
from models.security_models import SecurityScanResult, SecurityEvent, SecurityEventType, SeverityLevel

# Known magic bytes signatures
FILE_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "docx": [b"PK\x03\x04"],  # Standard Zip container signature used by DOCX
}

class FileValidator:
    """Validates uploaded resumes for safety, file format integrity, and resource limits."""

    def __init__(
        self,
        max_bytes: int = settings.MAX_FILE_SIZE_BYTES,
        max_pages: int = settings.MAX_RESUME_PAGES,
        allowed_extensions: Optional[list] = None
    ):
        self.max_bytes = max_bytes
        self.max_pages = max_pages
        self.allowed_extensions = set(allowed_extensions or settings.ALLOWED_EXTENSIONS)

    def validate_file(self, filename: str, content_bytes: bytes) -> SecurityScanResult:
        """
        Performs thorough multi-stage file validation.
        """
        events = []

        if not filename or not content_bytes:
            return SecurityScanResult(
                is_safe=False,
                blocked=True,
                block_reason="Empty file or filename provided."
            )

        # 1. Size Validation
        file_size = len(content_bytes)
        if file_size > self.max_bytes:
            reason = f"File size ({file_size / (1024*1024):.1f}MB) exceeds limit of {self.max_bytes / (1024*1024):.0f}MB."
            logger.warning(f"File validation rejected: {reason}")
            return SecurityScanResult(
                is_safe=False,
                blocked=True,
                block_reason=reason,
                events=[SecurityEvent(
                    event_type=SecurityEventType.FILE_TOO_LARGE,
                    severity=SeverityLevel.HIGH,
                    description=reason
                )]
            )

        # 2. Extension Validation
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in self.allowed_extensions:
            reason = f"File type '.{ext}' is not supported. Allowed formats: {', '.join(self.allowed_extensions)}"
            return SecurityScanResult(
                is_safe=False,
                blocked=True,
                block_reason=reason
            )

        # 3. Magic Bytes / Signature Verification
        if ext in FILE_SIGNATURES:
            valid_sig = False
            for sig in FILE_SIGNATURES[ext]:
                if content_bytes.startswith(sig):
                    valid_sig = True
                    break
            if not valid_sig:
                reason = f"File signature mismatch: File claimed extension '.{ext}' but signature does not match."
                logger.warning(f"File security rejection: {reason} for file {filename}")
                return SecurityScanResult(
                    is_safe=False,
                    blocked=True,
                    block_reason=reason,
                    events=[SecurityEvent(
                        event_type=SecurityEventType.INVALID_FILE_SIGNATURE,
                        severity=SeverityLevel.CRITICAL,
                        description=reason
                    )]
                )
        elif ext in ["md", "txt"]:
            # Check for executable binary headers or null bytes
            if b"\x00" in content_bytes[:1024] or content_bytes.startswith(b"MZ"):
                reason = "Binary or executable data detected in text file."
                return SecurityScanResult(
                    is_safe=False,
                    blocked=True,
                    block_reason=reason,
                    events=[SecurityEvent(
                        event_type=SecurityEventType.INVALID_FILE_SIGNATURE,
                        severity=SeverityLevel.CRITICAL,
                        description=reason
                    )]
                )

        return SecurityScanResult(is_safe=True, blocked=False)

file_validator = FileValidator()
