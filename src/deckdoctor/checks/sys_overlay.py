from __future__ import annotations

from deckdoctor.checks._util import result, skip_not_steamos
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "SYS-OVERLAY"
TITLE = "SteamOS /etc overlay"

WATCHED = (
    "steamos-atomupd/client.conf",
    "rauc/system.conf",
)


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    skipped = skip_not_steamos(ctx, ID, title)
    if skipped:
        return skipped

    root = ctx.overlay_root
    evidence = [str(root)]
    if not ctx.exists(root):
        return result(
            ID,
            title,
            Status.PASS,
            ctx.tr("sys.overlay.missing"),
            explanation=ctx.tr("sys.overlay.missing.explain"),
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
        )

    present: list[str] = []
    for rel in WATCHED:
        path = root / rel
        if ctx.exists(path):
            present.append(rel)
            evidence.append(f"present: {path}")
        else:
            evidence.append(f"absent: {path}")

    ctx.facts.overlay_edited = present
    if not present:
        return result(
            ID,
            title,
            Status.PASS,
            ctx.tr("sys.overlay.clean"),
            explanation=ctx.tr("sys.overlay.clean.explain"),
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            extra={"edited": []},
        )

    names = ", ".join(present)
    return result(
        ID,
        title,
        Status.WARNING,
        ctx.tr("sys.overlay.edited", names=names),
        explanation=ctx.tr("sys.overlay.edited.explain"),
        recommendation=ctx.tr("sys.overlay.edited.rec"),
        evidence=evidence,
        source=EvidenceSource.FILESYSTEM,
        severity=Severity.MEDIUM,
        extra={"edited": present},
    )
