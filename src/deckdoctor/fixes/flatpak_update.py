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
    timeout = 300.0
    evidence: list[str] = []
    timed_out = False
    succeeded = False
    for argv in (["flatpak", "update", "-y"], ["flatpak", "--user", "update", "-y"]):
        proc = executor.run(argv, timeout=timeout)
        evidence.append(f"{' '.join(argv)} → exit {proc.exit_code}")
        if proc.stderr.strip():
            evidence.append(proc.stderr.strip()[:300])
        if proc.timed_out:
            timed_out = True
            continue
        if proc.ok:
            if "--user" not in argv:
                return FixResult(ID, True, ctx.tr("fix.flatpak.ok"), evidence)
            succeeded = True
            continue
        if proc.error == "not_found":
            continue
    if timed_out:
        return FixResult(ID, False, ctx.tr("fix.flatpak.timeout"), evidence)
    if succeeded:
        return FixResult(ID, True, ctx.tr("fix.flatpak.ok"), evidence)
    return FixResult(ID, False, ctx.tr("fix.flatpak.fail"), evidence)
