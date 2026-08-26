from __future__ import annotations

from deckdoctor.checks._util import result, skip_not_steamos
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "SYS-OS-REBOOT"
TITLE = "SteamOS pending reboot"


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    skipped = skip_not_steamos(ctx, ID, title)
    if skipped:
        return skipped

    path = ctx.reboot_for_update_path
    evidence = [str(path)]
    if not ctx.exists(path):
        ctx.facts.pending_reboot = False
        return result(
            ID,
            title,
            Status.PASS,
            ctx.tr("sys.reboot.none"),
            explanation=ctx.tr("sys.reboot.none.explain"),
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
            extra={"pending": False},
        )

    text = (ctx.read_text(path, max_bytes=256) or "").strip()
    ctx.facts.pending_reboot = True
    ctx.facts.pending_reboot_build = text or None
    finding = ctx.tr("sys.reboot.pending.build", build=text) if text else ctx.tr("sys.reboot.pending")
    if text:
        evidence.append(f"buildid={text}")
    return result(
        ID,
        title,
        Status.WARNING,
        finding,
        explanation=ctx.tr("sys.reboot.pending.explain"),
        recommendation=ctx.tr("sys.reboot.pending.rec"),
        evidence=evidence,
        source=EvidenceSource.OS_METADATA,
        severity=Severity.MEDIUM,
        extra={"pending": True, "build": text},
    )
