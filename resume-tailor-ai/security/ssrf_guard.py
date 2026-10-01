"""
Server-Side Request Forgery (SSRF) Protection.
Validates outbound URLs, resolving DNS and blocking private/internal IP ranges.
"""
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple
from core.logger import logger
from models.security_models import SecurityEvent, SecurityEventType, SeverityLevel

DANGEROUS_HOSTNAMES = {
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "metadata.google.internal", "instance-data", "169.254.169.254"
}

ALLOWED_SCHEMES = {"http", "https"}

class SSRFGuard:
    """Guard against SSRF attacks on outbound URL fetching."""

    @classmethod
    def is_url_safe(cls, url: str) -> bool:
        """Returns True if the URL passes all SSRF boundary checks."""
        safe, _ = cls.is_safe_url(url)
        return safe

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, str]:
        """Alias for is_safe_url returning (is_safe, message)."""
        return cls.is_safe_url(url)

    @staticmethod
    def is_safe_url(url: str) -> Tuple[bool, str]:
        """
        Validates whether a URL is safe for external HTTP request.
        Returns: (is_safe, error_or_success_message)
        """
        if not url or not isinstance(url, str):
            return False, "Empty or invalid URL"

        url = url.strip()

        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Malformed URL syntax: {e}"

        # 1. Scheme check
        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            return False, f"Forbidden URL scheme '{parsed.scheme}'. Only HTTP/HTTPS allowed."

        hostname = parsed.hostname
        if not hostname:
            return False, "Missing hostname in URL."

        hostname = hostname.lower()

        # 2. Block direct dangerous hostnames
        if hostname in DANGEROUS_HOSTNAMES:
            logger.warning(f"SSRF attempt blocked: direct forbidden hostname '{hostname}'")
            return False, f"Access to forbidden internal hostname '{hostname}' is blocked."

        # 3. Check for IP address literals
        try:
            ip = ipaddress.ip_address(hostname)
            if SSRFGuard._is_private_or_restricted(ip):
                logger.warning(f"SSRF attempt blocked: private/restricted IP literal '{ip}'")
                return False, f"Access to private/restricted IP address '{ip}' is blocked."
        except ValueError:
            # Not an IP literal, it's a domain name - proceed to DNS resolution
            pass

        # 4. Resolve DNS and inspect target IP (DNS Rebinding Defense)
        try:
            resolved_ips = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
            for res in resolved_ips:
                sockaddr = res[4]
                ip_str = sockaddr[0]
                ip_obj = ipaddress.ip_address(ip_str)
                if SSRFGuard._is_private_or_restricted(ip_obj):
                    logger.warning(f"SSRF attempt blocked: hostname '{hostname}' resolved to private IP '{ip_str}'")
                    return False, f"Target hostname resolved to internal/private IP '{ip_str}'."
        except socket.gaierror as e:
            return False, f"Could not resolve domain '{hostname}': {e}"
        except Exception as e:
            return False, f"DNS resolution security check failed: {e}"

        return True, "URL is safe"

    @staticmethod
    def _is_private_or_restricted(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Checks if IP is private, loopback, link-local, multicast, or reserved."""
        # Check for RFC 6052 Well-Known NAT64 Prefix (64:ff9b::/96)
        if ip.version == 6 and ip in ipaddress.IPv6Network("64:ff9b::/96"):
            # Extract the embedded IPv4 address (the last 32 bits)
            embedded_v4_int = int(ip) & 0xFFFFFFFF
            embedded_v4 = ipaddress.IPv4Address(embedded_v4_int)
            return SSRFGuard._is_private_or_restricted(embedded_v4)

        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or (ip.is_reserved and not (ip.version == 6 and ip in ipaddress.IPv6Network("64:ff9b::/96")))
            or ip.is_unspecified
        )

ssrf_guard = SSRFGuard()
