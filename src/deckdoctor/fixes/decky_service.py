from __future__ import annotations

from deckdoctor.context import DiagnosticContext
from deckdoctor.fixes.executor import FixExecutor
from deckdoctor.models import FixPlan, FixResult, Report, Status

ID = "decky-service"

_UNIT = "plugin_loader.service"


def plan(ctx: DiagnosticContext, report: Report) -> FixPlan | None:
    if not any(r.check_id == "DECKY-SERVICE" and r.status == Status.FAIL for r in report.results):
        return None
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
    if active not in {"inactive", "failed"}:
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
    proc = executor.run(["systemctl", "enable", "--now", _UNIT], timeout=30.0)
    evidence = [f"systemctl enable --now {_UNIT} → exit {proc.exit_code} {proc.stderr.strip()[:200]}"]
    return FixResult(ID, proc.ok, ctx.tr("fix.decky.ok" if proc.ok else "fix.decky.fail"), evidence)
