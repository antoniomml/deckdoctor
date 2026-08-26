from __future__ import annotations

from deckdoctor.context import DiagnosticContext
from deckdoctor.fixes.executor import FixExecutor
from deckdoctor.models import FixPlan, FixResult, Report

ID = "decky-service"

_UNIT = "plugin_loader.service"


def plan(ctx: DiagnosticContext, report: Report) -> FixPlan | None:
    del report
    if not ctx.facts.plugin_loader_present:
        return None
    if ctx.facts.plugin_loader_executable is False:
        return None
    if ctx.facts.decky_unit_is_429:
        return None
    active = ctx.facts.decky_service_active
    if active == "active":
        return None
    if active == "masked" or (ctx.facts.decky_service_enabled or "").startswith("masked"):
        return None
    if active is None:
        return None
    return FixPlan(
        id=ID,
        title=ctx.tr("fix.decky.title"),
        summary=ctx.tr("fix.decky.summary"),
        mutation=ctx.tr("fix.decky.mutation"),
        reversible=ctx.tr("fix.decky.undo"),
        related_checks=["DECKY-SERVICE"],
        risk="medium",
        needs_root=True,
    )


def apply(ctx: DiagnosticContext, executor: FixExecutor) -> FixResult:
    timeout = ctx.remaining_timeout(30.0)
    attempts = [
        ["systemctl", "enable", "--now", _UNIT],
        ["systemctl", "--user", "enable", "--now", _UNIT],
        ["systemctl", "start", _UNIT],
    ]
    evidence: list[str] = []
    denied = False
    for argv in attempts:
        proc = executor.run(argv, timeout=timeout)
        evidence.append(f"{' '.join(argv)} → exit {proc.exit_code} {proc.stderr.strip()[:200]}")
        blob = f"{proc.stdout}\n{proc.stderr}".lower()
        if proc.ok:
            return FixResult(ID, True, ctx.tr("fix.decky.ok"), evidence)
        if "permission denied" in blob or "interactive authentication" in blob or proc.exit_code in {1, 4}:
            if "denied" in blob or "polkit" in blob or "auth" in blob:
                denied = True
        if proc.error == "not_found":
            continue
    if denied:
        return FixResult(ID, False, ctx.tr("fix.decky.denied"), evidence)
    return FixResult(ID, False, ctx.tr("fix.decky.fail"), evidence)
