from __future__ import annotations

from deckdoctor.checks._util import first_line, result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "SYS-OS-CHANNEL"
TITLE = "SteamOS channel"


def run(ctx: DiagnosticContext) -> CheckResult:
    if ctx.facts.is_steamos is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Not SteamOS",
            explanation="Channel detection uses SteamOS tools.",
            source=EvidenceSource.OS_METADATA,
        )

    for argv in (["steamos-select-branch", "-c"], ["steamos-select-branch"]):
        proc = ctx.run(argv)
        if proc.error == "not_found":
            continue
        if proc.timed_out:
            return result(
                ID,
                TITLE,
                Status.UNKNOWN,
                "steamos-select-branch timed out",
                evidence=[proc.stderr.strip()],
                source=EvidenceSource.OS_METADATA,
            )
        text = (proc.stdout or proc.stderr).strip()
        if proc.ok and text:
            channel = first_line(text, 80)
            ctx.facts.os_channel = channel
            return result(
                ID,
                TITLE,
                Status.PASS,
                f"Channel: {channel}",
                explanation="Reported by steamos-select-branch (local).",
                evidence=[f"{' '.join(argv)} → {channel}"],
                source=EvidenceSource.OS_METADATA,
                extra={"channel": channel},
            )
        if text:
            return result(
                ID,
                TITLE,
                Status.UNKNOWN,
                "Could not parse SteamOS channel",
                evidence=[f"exit {proc.exit_code}: {first_line(text)}"],
                source=EvidenceSource.OS_METADATA,
            )

    return result(
        ID,
        TITLE,
        Status.SKIPPED,
        "steamos-select-branch not available",
        explanation="The SteamOS branch tool is not on PATH. This is expected on non-SteamOS images.",
        source=EvidenceSource.OS_METADATA,
    )
