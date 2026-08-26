from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status


def result(
    check_id: str,
    title: str,
    status: Status,
    finding: str,
    *,
    explanation: str = "",
    recommendation: str = "",
    evidence: Iterable[str] | None = None,
    source: EvidenceSource = EvidenceSource.FILESYSTEM,
    severity: Severity | None = None,
    fact_kind: str = "fact",
    extra: dict[str, Any] | None = None,
) -> CheckResult:
    if severity is None:
        if status == Status.FAIL:
            severity = Severity.HIGH
        elif status == Status.WARNING:
            severity = Severity.MEDIUM
        else:
            severity = Severity.NONE
    return CheckResult(
        check_id=check_id,
        title=title,
        status=status,
        finding=finding,
        explanation=explanation,
        recommendation=recommendation,
        evidence=[e for e in (evidence or []) if e],
        source=source,
        severity=severity,
        fact_kind=fact_kind,
        extra=extra or {},
    )


def version_parts(raw: str) -> tuple[int, ...] | None:
    """Parse a dotted version for comparison. Returns None if unusable."""
    text = (raw or "").strip().lstrip("vV")
    if not text or text.lower() == "unknown":
        return None
    parts: list[int] = []
    for token in re.split(r"[.\-+_]", text):
        if token.isdigit():
            parts.append(int(token))
        elif token:
            break
    return tuple(parts) if parts else None


def version_is_newer(candidate: str, current: str) -> bool | None:
    left = version_parts(candidate)
    right = version_parts(current)
    if left is None or right is None:
        return None
    width = max(len(left), len(right))
    left = left + (0,) * (width - len(left))
    right = right + (0,) * (width - len(right))
    return left > right


def first_line(text: str, limit: int = 240) -> str:
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    if len(line) > limit:
        return line[: limit - 1] + "…"
    return line


LOG_SIGNATURES = (
    "CRITICAL",
    "Traceback",
    "PermissionError",
    "ConnectionError",
    "Failed Downloading Remote Binaries",
    "rate limit",
    "Too Many Requests",
    "Could not load",
    "Couldn't connect to debugger",
    "Failed to inject",
    "No such file or directory",
    "Minified React error",
)


def relevant_log_lines(text: str, *, limit: int = 100) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if any(sig.lower() in line.lower() for sig in LOG_SIGNATURES) or " ERROR" in line or "[ERROR]" in line:
            lines.append(line.rstrip())
        if len(lines) >= limit:
            break
    return lines
