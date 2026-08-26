from __future__ import annotations

from datetime import UTC

from deckdoctor import __version__
from deckdoctor.checks import ALL_CHECKS
from deckdoctor.checks._util import result
from deckdoctor.checks.protocol import FnCheck
from deckdoctor.context import DiagnosticContext
from deckdoctor.correlator import correlate
from deckdoctor.models import CheckResult, EvidenceSource, Report, Status

DEFAULT_TIMEOUT_SECONDS = 60.0


def run_checks(ctx: DiagnosticContext) -> list[CheckResult]:
    results: list[CheckResult] = []
    timed_out = False
    for check in ALL_CHECKS:
        skip = _maybe_skip(ctx, check, timed_out=timed_out)
        if skip is not None:
            results.append(skip)
            continue
        if ctx.timed_out():
            timed_out = True
            ctx.facts.partial = True
            ctx.facts.checks_timed_out.append(check.id)
            results.append(_skip_timeout(ctx, check))
            continue
        results.append(check.run(ctx))
        if ctx.timed_out():
            timed_out = True
            ctx.facts.partial = True
    return results


def _skip_timeout(ctx: DiagnosticContext, check: FnCheck) -> CheckResult:
    return result(
        check.id,
        check.title,
        Status.SKIPPED,
        ctx.tr("skip.timeout"),
        explanation=ctx.tr("skip.timeout.explain"),
        source=EvidenceSource.OS_METADATA,
    )


def _maybe_skip(ctx: DiagnosticContext, check: FnCheck, *, timed_out: bool) -> CheckResult | None:
    if timed_out:
        ctx.facts.checks_timed_out.append(check.id)
        return _skip_timeout(ctx, check)
    if ctx.only_ids is not None and check.id not in ctx.only_ids:
        return result(
            check.id,
            check.title,
            Status.SKIPPED,
            ctx.tr("skip.only"),
            explanation=ctx.tr("skip.only.explain"),
            source=EvidenceSource.OS_METADATA,
        )
    if not ctx.network_enabled and check.requires_network:
        return result(
            check.id,
            check.title,
            Status.SKIPPED,
            ctx.tr("skip.no_network"),
            explanation=ctx.tr("skip.no_network.explain"),
            source=EvidenceSource.NETWORK,
        )
    return None


def diagnose(ctx: DiagnosticContext) -> Report:
    results = run_checks(ctx)
    diagnoses = correlate(results, ctx.facts, locale=ctx.locale)
    return Report(
        version=__version__,
        generated_at=ctx.now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        results=results,
        diagnoses=diagnoses,
        facts=ctx.facts.to_dict(),
        locale=ctx.locale,
        ascii_mode=ctx.ascii_mode,
        partial=ctx.facts.partial,
        verbose=ctx.verbose,
        color=ctx.color,
    )
