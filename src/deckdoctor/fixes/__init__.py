from __future__ import annotations

from collections.abc import Callable

from deckdoctor.context import DiagnosticContext
from deckdoctor.fixes import cef_debug, decky_service, flatpak_update, pluginloader_exec
from deckdoctor.fixes.executor import FakeFixExecutor, FixExecutor
from deckdoctor.models import FixPlan, FixResult, Report

FixFn = Callable[[DiagnosticContext, Report], FixPlan | None]
ApplyFn = Callable[[DiagnosticContext, FixExecutor], FixResult]

FIXES: tuple[tuple[str, FixFn, ApplyFn], ...] = (
    (pluginloader_exec.ID, pluginloader_exec.plan, pluginloader_exec.apply),
    (cef_debug.ID, cef_debug.plan, cef_debug.apply),
    (decky_service.ID, decky_service.plan, decky_service.apply),
    (flatpak_update.ID, flatpak_update.plan, flatpak_update.apply),
)

KNOWN_FIX_IDS = tuple(item[0] for item in FIXES)


def collect_plans(ctx: DiagnosticContext, report: Report) -> list[FixPlan]:
    plans: list[FixPlan] = []
    for _fid, planner, _apply in FIXES:
        planned = planner(ctx, report)
        if planned is not None:
            plans.append(planned)
    return plans


def apply_plans(
    ctx: DiagnosticContext,
    plans: list[FixPlan],
    executor: FixExecutor | None = None,
) -> list[FixResult]:
    runner = executor or FixExecutor()
    appliers = {fid: apply for fid, _plan, apply in FIXES}
    results: list[FixResult] = []
    for plan in plans:
        fn = appliers.get(plan.id)
        if fn is None:
            results.append(FixResult(plan.id, False, f"unknown fix {plan.id}"))
            continue
        results.append(fn(ctx, runner))
    return results


__all__ = [
    "KNOWN_FIX_IDS",
    "FakeFixExecutor",
    "FixExecutor",
    "apply_plans",
    "collect_plans",
]
