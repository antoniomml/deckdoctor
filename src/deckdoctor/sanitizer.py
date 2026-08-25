from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Any

# Best-effort only. Never advertised as perfect.

_EMAIL = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
_MAC = re.compile(r"\b([0-9A-F]{2}:){5}[0-9A-F]{2}\b", re.I)
_STEAM_ID = re.compile(r"\b7656119\d{10}\b")
_IPV4 = re.compile(r"\b(\d{1,3}\.){3}\d{1,3}\b")
_IPV6 = re.compile(
    r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b|\b::1\b",
)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_\-]+=*\.[A-Za-z0-9_\-]+=*\.[A-Za-z0-9_\-+=]*")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-+=/]+")
_GITHUB_TOKEN = re.compile(r"\b(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]+\b")
_AWS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GENERIC_SECRET = re.compile(
    r'(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[:=]\s*["\']?([^\s"\']+)'
)
_URL_CREDS = re.compile(r"(https?://)([^/@:\s]+):([^/@\s]+)@")
_SSH_BLOCK = re.compile(
    r"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----.*?-----END (?:OPENSSH |RSA |EC )?PRIVATE KEY-----",
    re.S,
)
_MIN_TOKEN_LEN = 3


def _is_private_ipv4(ip: str) -> bool:
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return bool(addr.is_private or addr.is_loopback or addr.is_link_local)


def _is_private_ipv6(ip: str) -> bool:
    try:
        addr = ipaddress.IPv6Address(ip)
    except ValueError:
        return False
    return bool(addr.is_private or addr.is_loopback or addr.is_link_local)


@dataclass
class Sanitizer:
    user: str
    home: str
    hostname: str
    _ip_map: dict[str, str] = field(default_factory=dict)

    def apply(self, text: str) -> str:
        if not text:
            return text
        out = text
        out = _SSH_BLOCK.sub("<SSH_KEY>", out)
        out = _URL_CREDS.sub(r"\1<REDACTED>:<REDACTED>@", out)
        out = _JWT.sub("<REDACTED>", out)
        out = _GITHUB_TOKEN.sub("<REDACTED>", out)
        out = _AWS_KEY.sub("<REDACTED>", out)
        out = _BEARER.sub(r"\1<REDACTED>", out)

        def _secret(match: re.Match[str]) -> str:
            return f"{match.group(1)}=<REDACTED>"

        out = _GENERIC_SECRET.sub(_secret, out)
        out = _EMAIL.sub("<EMAIL>", out)
        out = _MAC.sub("<MAC>", out)
        out = _STEAM_ID.sub("<STEAM_ID>", out)

        def _ip4(match: re.Match[str]) -> str:
            ip = match.group(0)
            if not _is_private_ipv4(ip):
                return ip
            return self._label(ip)

        def _ip6(match: re.Match[str]) -> str:
            ip = match.group(0)
            if not _is_private_ipv6(ip):
                return ip
            return self._label(ip)

        out = _IPV4.sub(_ip4, out)
        out = _IPV6.sub(_ip6, out)

        if self.home:
            out = out.replace(self.home, "/home/<USER>")
        if self.user and len(self.user) >= _MIN_TOKEN_LEN:
            out = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(self.user)}(?![A-Za-z0-9_])", "<USER>", out)
        if self.hostname and len(self.hostname) >= _MIN_TOKEN_LEN:
            out = re.sub(
                rf"(?<![A-Za-z0-9_]){re.escape(self.hostname)}(?![A-Za-z0-9_])",
                "<HOSTNAME>",
                out,
                flags=re.I,
            )
        return out

    def _label(self, ip: str) -> str:
        if ip not in self._ip_map:
            self._ip_map[ip] = f"<PRIVATE_IP_{len(self._ip_map) + 1}>"
        return self._ip_map[ip]

    def apply_obj(self, value: Any) -> Any:
        """Sanitise strings inside JSON-compatible structures without breaking types."""
        if isinstance(value, str):
            return self.apply(value)
        if isinstance(value, dict):
            return {str(k): self.apply_obj(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.apply_obj(item) for item in value]
        if isinstance(value, tuple):
            return [self.apply_obj(item) for item in value]
        return value
