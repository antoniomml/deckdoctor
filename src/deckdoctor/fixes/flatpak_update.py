from __future__ import annotations

from deckdoctor.context import DiagnosticContext
from deckdoctor.fixes.executor import FixExecutor
from deckdoctor.models import FixPlan, FixResult, Report

ID = "flatpak-update"


def plan(ctx: DiagnosticContext, report: Report) -> FixPlan | None:
    del report
    if ctx.facts.flatpak_available is False:
        return None
    updates = ctx.facts.flatpak_updates or []
    if not updates:
        return None
    if not ctx.network_enabled:
        return None
    return FixPlan(
        id=ID,
        title=ctx.tr("fix.flatpak.title"),
        summary=ctx.tr("fix.flatpak.summary", count=len(updates)),
        mutation=ctx.tr("fix.flatpak.mutation"),
        reversible=ctx.tr("fix.flatpak.undo"),
        related_checks=["FP-UPDATES"],
        risk="medium",
    )


def apply(ctx: DiagnosticContext, executor: FixExecutor) -> FixResult:
    proc = executor.run(["flatpak", "update", "-y"], timeout=300.0)
    evidence = [f"flatpak update -y → exit {proc.exit_code}"]
    if proc.stderr.strip():
        evidence.append(proc.stderr.strip()[:300])
    key = "fix.flatpak.timeout" if proc.timed_out else "fix.flatpak.ok" if proc.ok else "fix.flatpak.fail"
    return FixResult(ID, proc.ok, ctx.tr(key), evidence)
