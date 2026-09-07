from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import replace

from deckdoctor.context import DiagnosticContext
from deckdoctor.facts import Facts
from deckdoctor.fixes import cef_debug, decky_service, flatpak_update, pluginloader_exec
from deckdoctor.fixes.executor import FakeFixExecutor, FixExecutor
from deckdoctor.models import FixPlan, FixResult, Report, Status

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
    planners = {fid: planner for fid, planner, _apply in FIXES}
    results: list[FixResult] = []
    for plan in plans:
        fn = appliers.get(plan.id)
        if fn is None:
            results.append(FixResult(plan.id, False, f"unknown fix {plan.id}"))
            continue
        # Consent applies to the printed plan; recheck before each mutation.
        from deckdoctor.runner import diagnose

        fresh = replace(ctx, facts=Facts(), _cmd_cache={}, deadline=time.monotonic() + 60, progress=None)
        current = planners[plan.id](fresh, diagnose(fresh))
        if current is None or current != plan:
            results.append(FixResult(plan.id, False, ctx.tr("fix.preconditions_changed")))
            continue
        results.append(fn(fresh, runner))
    return results


__all__ = [
    "KNOWN_FIX_IDS",
    "FakeFixExecutor",
    "FixExecutor",
    "apply_plans",
    "collect_plans",
]


def verify_results(plans: list[FixPlan], results: list[FixResult], after: Report) -> None:
    """Separate command completion from resolution observed by diagnosis."""
    checks = {row.check_id: row for row in after.results}
    by_plan = {plan.id: plan for plan in plans}
    for item in results:
        plan = by_plan[item.id]
        observed = [checks.get(key) for key in plan.related_checks]
        if not item.ok:
            item.verified = False
        elif not observed or any(row is None or row.status in {Status.UNKNOWN, Status.SKIPPED} for row in observed):
            item.verified = None
        else:
            item.verified = all(row is not None and row.status in {Status.PASS, Status.INFO} for row in observed)
