from __future__ import annotations

from deckdoctor.checks._util import relevant_log_lines, result, skip_no_decky
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "DECKY-LOGS"
TITLE = "Decky backend logs"

JOURNAL_CMD = ["journalctl", "-b0", "-u", "plugin_loader.service", "-n", "200", "--no-pager"]


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    skipped = skip_no_decky(ctx, ID, title, source=EvidenceSource.JOURNAL)
    if skipped:
        return skipped

    proc = ctx.run(JOURNAL_CMD, timeout=20.0)
    if proc.error == "not_found":
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("decky.logs.no_journalctl"),
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
            title,
            Status.SKIPPED,
            ctx.tr("decky.logs.denied"),
            explanation=ctx.tr("decky.logs.denied.explain"),
            evidence=[proc.stderr.strip()[:400] or proc.stdout.strip()[:400]],
            source=EvidenceSource.JOURNAL,
        )

    if proc.timed_out:
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("decky.logs.timeout"),
            source=EvidenceSource.JOURNAL,
        )

    lines = relevant_log_lines(proc.stdout, limit=80)
    ctx.facts.decky_log_hits = lines[:20]
    ctx.facts.decky_log_text = proc.stdout[-8000:]

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
    ctx.facts.decky_log_signatures = found

    if not lines:
        return result(
            ID,
            title,
            Status.PASS,
            ctx.tr("decky.logs.clean"),
            explanation=ctx.tr("decky.logs.clean.explain"),
            evidence=["journal lines scanned from plugin_loader.service (boot 0)"],
            source=EvidenceSource.JOURNAL,
        )

    high = [s for s in found if s in {"remote_binaries", "plugin_load", "permission", "traceback", "inject"}]
    status = Status.FAIL if high else Status.WARNING
    return result(
        ID,
        title,
        status,
        ctx.tr("decky.logs.hits", count=len(lines), signatures=", ".join(found) or "generic ERROR"),
        explanation=ctx.tr("decky.logs.hits.explain"),
        recommendation=ctx.tr("decky.logs.hits.rec"),
        evidence=lines[:15],
        source=EvidenceSource.JOURNAL,
        extra={"signatures": found},
    )
