from __future__ import annotations

import re
from dataclasses import dataclass, field

# Best-effort only. Never advertised as perfect.

_EMAIL = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
_MAC = re.compile(r"\b([0-9A-F]{2}:){5}[0-9A-F]{2}\b", re.I)
_STEAM_ID = re.compile(r"\b7656119\d{10}\b")
_IPV4 = re.compile(r"\b(\d{1,3}\.){3}\d{1,3}\b")
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


def _is_private_ipv4(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return False
    if any(n > 255 for n in nums):
        return False
    a, b = nums[0], nums[1]
    if a == 10:
        return True
    if a == 127:
        return True
    if a == 192 and b == 168:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 169 and b == 254:
        return True
    return False


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

        def _ip(match: re.Match[str]) -> str:
            ip = match.group(0)
            if not _is_private_ipv4(ip):
                return ip
            if ip not in self._ip_map:
                self._ip_map[ip] = f"<PRIVATE_IP_{len(self._ip_map) + 1}>"
            return self._ip_map[ip]

        out = _IPV4.sub(_ip, out)

        if self.home:
            out = out.replace(self.home, "/home/<USER>")
            # also /home/user without trailing parts already covered
        if self.user:
            # word-ish replace after paths so we don't destroy /home/<USER>
            out = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(self.user)}(?![A-Za-z0-9_])", "<USER>", out)
        if self.hostname:
            out = re.sub(
                rf"(?<![A-Za-z0-9_]){re.escape(self.hostname)}(?![A-Za-z0-9_])",
                "<HOSTNAME>",
                out,
                flags=re.I,
            )
        return out
