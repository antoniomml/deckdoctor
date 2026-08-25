from __future__ import annotations

from deckdoctor.checks._util import relevant_log_lines, result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "DECKY-LOGS"
TITLE = "Decky backend logs"

JOURNAL_CMD = ["journalctl", "-b0", "-u", "plugin_loader.service", "-n", "200", "--no-pager"]


def run(ctx: DiagnosticContext) -> CheckResult:
    if ctx.facts.get("decky_installed") is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Decky is not installed",
            source=EvidenceSource.JOURNAL,
        )

    proc = ctx.run(JOURNAL_CMD, timeout=20.0)
    if proc.error == "not_found":
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "journalctl is not available",
            source=EvidenceSource.JOURNAL,
        )

    blob = f"{proc.stdout}\n{proc.stderr}"
    lowered = blob.lower()
    if proc.exit_code != 0 and (
        "permission denied" in lowered
        or "not allowed" in lowered
        or "current user is not an administrator" in lowered
        or "no journal files were found" in lowered
    ):
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "System journal for plugin_loader.service is not readable",
            explanation="DeckDoctor does not request sudo. Add the user to systemd-journal or re-run with privileges you already have.",
            evidence=[proc.stderr.strip()[:400] or proc.stdout.strip()[:400]],
            source=EvidenceSource.JOURNAL,
        )

    if proc.timed_out:
        return result(
            ID,
            TITLE,
            Status.UNKNOWN,
            "journalctl timed out",
            source=EvidenceSource.JOURNAL,
        )

    lines = relevant_log_lines(proc.stdout, limit=80)
    ctx.facts["decky_log_hits"] = lines[:20]
    ctx.facts["decky_log_text"] = proc.stdout[-8000:]

    signatures = {
        "Failed Downloading Remote Binaries": "remote_binaries",
        "Couldn't connect to debugger": "cef_connect",
        "Failed to inject": "inject",
        "PermissionError": "permission",
        "Could not load": "plugin_load",
        "rate limit": "rate_limit",
        "Too Many Requests": "rate_limit",
        "Traceback": "traceback",
    }
    found = [name for needle, name in signatures.items() if needle.lower() in proc.stdout.lower()]
    ctx.facts["decky_log_signatures"] = found

    if not lines:
        return result(
            ID,
            TITLE,
            Status.PASS,
            "No recent backend ERROR/CRITICAL signatures in the current boot journal",
            explanation="Warnings alone are not treated as failures. Older boots are ignored (`-b0`).",
            evidence=[f"journal lines scanned from plugin_loader.service (boot 0)"],
            source=EvidenceSource.JOURNAL,
        )

    high = [s for s in found if s in {"remote_binaries", "plugin_load", "permission", "traceback", "inject"}]
    status = Status.FAIL if high else Status.WARNING
    return result(
        ID,
        TITLE,
        status,
        f"{len(lines)} relevant backend log line(s); signatures: {', '.join(found) or 'generic ERROR'}",
        explanation="Matched concrete signatures, not every warning. Timestamps are whatever journalctl returned for this boot.",
        recommendation="See the report excerpt. A single old ERROR is weaker evidence than a traceback on this boot.",
        evidence=lines[:15],
        source=EvidenceSource.JOURNAL,
        extra={"signatures": found},
    )
