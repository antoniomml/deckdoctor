from __future__ import annotations

from deckdoctor.checks._util import first_line, result, skip_not_steamos
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "SYS-OS-CHANNEL"
TITLE = "SteamOS channel"


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    skipped = skip_not_steamos(ctx, ID, title)
    if skipped:
        return skipped

    for argv in (["steamos-select-branch", "-c"], ["steamos-select-branch"]):
        proc = ctx.run(argv)
        if proc.error == "not_found":
            continue
        if proc.timed_out:
            return result(
                ID,
                title,
                Status.UNKNOWN,
                ctx.tr("sys.channel.timeout"),
                evidence=[proc.stderr.strip()],
                source=EvidenceSource.OS_METADATA,
            )
        text = (proc.stdout or proc.stderr).strip()
        if proc.ok and text:
            channel = first_line(text, 80)
            ctx.facts.os_channel = channel
            return result(
                ID,
                title,
                Status.PASS,
                ctx.tr("sys.channel.ok", channel=channel),
                explanation=ctx.tr("sys.channel.ok.explain"),
                evidence=[f"{' '.join(argv)} → {channel}"],
                source=EvidenceSource.OS_METADATA,
                extra={"channel": channel},
            )
        if text:
            return result(
                ID,
                title,
                Status.UNKNOWN,
                ctx.tr("sys.channel.parse"),
                evidence=[f"exit {proc.exit_code}: {first_line(text)}"],
                source=EvidenceSource.OS_METADATA,
            )

    return result(
        ID,
        title,
        Status.SKIPPED,
        ctx.tr("sys.channel.missing"),
        explanation=ctx.tr("sys.channel.missing.explain"),
        source=EvidenceSource.OS_METADATA,
    )
