from __future__ import annotations

import os

from deckdoctor.context import DiagnosticContext
from deckdoctor.fixes.executor import FixExecutor
from deckdoctor.models import FixPlan, FixResult, Report

ID = "pluginloader-exec"


def plan(ctx: DiagnosticContext, report: Report) -> FixPlan | None:
    del report
    loader = ctx.plugin_loader
    if not ctx.exists(loader):
        return None
    if os.access(loader, os.X_OK):
        return None
    path = str(loader)
    return FixPlan(
        id=ID,
        title=ctx.tr("fix.pluginloader.title"),
        summary=ctx.tr("fix.pluginloader.summary"),
        mutation=ctx.tr("fix.pluginloader.mutation", path=path),
        reversible=ctx.tr("fix.pluginloader.undo", path=path),
        related_checks=["DECKY-INSTALL"],
        risk="low",
    )


def apply(ctx: DiagnosticContext, executor: FixExecutor) -> FixResult:
    path = ctx.plugin_loader
    result = executor.chmod_plus_x(ctx, path)
    if result.ok and os.access(path, os.X_OK):
        return FixResult(ID, True, ctx.tr("fix.exec.ok"), [str(path)])
    return FixResult(ID, False, ctx.tr("fix.exec.fail"), [result.stderr or result.error or str(path)])
