from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from deckdoctor.context import DiagnosticContext
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


def skip_not_steamos(ctx: DiagnosticContext, check_id: str, title: str) -> CheckResult | None:
    if ctx.facts.is_steamos is True:
        return None
    return result(
        check_id,
        title,
        Status.SKIPPED,
        ctx.tr("skip.not_steamos"),
        explanation=ctx.tr("skip.not_steamos.explain"),
        source=EvidenceSource.OS_METADATA,
    )


def skip_no_decky(ctx: DiagnosticContext, check_id: str, title: str, *, source: EvidenceSource) -> CheckResult | None:
    if ctx.facts.decky_installed is not False:
        return None
    return result(
        check_id,
        title,
        Status.SKIPPED,
        ctx.tr("skip.decky_missing"),
        source=source,
    )


def format_bytes(num: int) -> str:
    for unit, size in (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)):
        if num >= size:
            return f"{num / size:.1f} {unit}"
    return f"{num} B"


def first_line(text: str, limit: int = 240) -> str:
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    if len(line) > limit:
        return line[: limit - 1] + "…"
    return line


def flatpak_remote_from_stderr(stderr: str) -> str:
    """Best-effort remote name from ``flatpak remote-ls`` errors."""
    text = stderr or ""
    for pattern in (
        r"from remote\s+['\"]?([^:'\"\s]+)",
        r"for remote\s+['\"]?([^:'\"\s]+)",
        r"remote\s+['\"]([^'\"]+)['\"]",
    ):
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return ""


def parse_flatpak_remotes(text: str) -> list[tuple[str, str]]:
    """Return ``(name, --system|--user)`` from ``flatpak remotes`` output."""
    rows: list[tuple[str, str]] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("name"):
            continue
        bits = line.split("\t") if "\t" in line else line.split()
        if not bits:
            continue
        name = bits[0]
        options = bits[1] if len(bits) > 1 else ""
        scope = "--user" if "user" in {p.strip() for p in options.split(",")} else "--system"
        rows.append((name, scope))
    return rows


def flatpak_remote_delete_cmds(remotes_raw: str, names: Iterable[str] | str) -> str:
    """Suggest ``flatpak remote-delete``; never run it. Default scope is ``--user``."""
    wanted = [names] if isinstance(names, str) else list(names)
    parts: list[str] = []
    seen: set[str] = set()
    scopes = {name: scope for name, scope in parse_flatpak_remotes(remotes_raw)}
    for raw in wanted:
        for name in (bit.strip() for bit in str(raw).split(",")):
            if not name or name in seen:
                continue
            seen.add(name)
            parts.append(f"flatpak remote-delete {scopes.get(name, '--user')} {name}")
    return "; ".join(parts)


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
