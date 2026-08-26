from __future__ import annotations

from deckdoctor.context import DiagnosticContext
from deckdoctor.fixes.executor import FixExecutor
from deckdoctor.models import FixPlan, FixResult, Report

ID = "cef-debug"


def plan(ctx: DiagnosticContext, report: Report) -> FixPlan | None:
    del report
    if ctx.facts.decky_installed is False:
        return None
    path = ctx.steam_root / ".cef-enable-remote-debugging"
    if ctx.exists(path):
        return None
    loc = str(path)
    return FixPlan(
        id=ID,
        title=ctx.tr("fix.cef.title"),
        summary=ctx.tr("fix.cef.summary"),
        mutation=ctx.tr("fix.cef.mutation", path=loc),
        reversible=ctx.tr("fix.cef.undo", path=loc),
        related_checks=["DECKY-FRONTEND"],
        risk="low",
    )


def apply(ctx: DiagnosticContext, executor: FixExecutor) -> FixResult:
    path = ctx.steam_root / ".cef-enable-remote-debugging"
    result = executor.touch_empty(ctx, path)
    loc = str(path)
    if result.ok and ctx.exists(path):
        return FixResult(ID, True, ctx.tr("fix.cef.ok", path=loc), [loc])
    return FixResult(ID, False, ctx.tr("fix.cef.fail", path=loc), [result.stderr or result.error or loc])
