from __future__ import annotations

from datetime import datetime, timezone

from deckdoctor import __version__
from deckdoctor.checks import ALL_CHECKS, NETWORK_CHECK_IDS
from deckdoctor.context import DiagnosticContext
from deckdoctor.correlator import correlate
from deckdoctor.models import CheckResult, Report, Status

SKIP_WITHOUT_NETWORK = NETWORK_CHECK_IDS | {"SYS-OS-UPDATER", "FP-UPDATES", "AUTOFLATPAKS"}


def run_checks(ctx: DiagnosticContext) -> list[CheckResult]:
    results: list[CheckResult] = []
    for fn in ALL_CHECKS:
        # Peek id via a dummy? functions have matching module ID constants; call them.
        result = _maybe_skip(ctx, fn)
        if result is not None:
            results.append(result)
            continue
        results.append(fn(ctx))
    return results


def _maybe_skip(ctx: DiagnosticContext, fn) -> CheckResult | None:
    if ctx.network_enabled:
        return None
    # Import IDs from the function's module
    module = __import__(fn.__module__, fromlist=["ID", "TITLE"])
    check_id = getattr(module, "ID", "")
    title = getattr(module, "TITLE", check_id)
    if check_id in SKIP_WITHOUT_NETWORK:
        from deckdoctor.checks._util import result
        from deckdoctor.models import EvidenceSource

        return result(
            check_id,
            title,
            Status.SKIPPED,
            "Skipped (--no-network)",
            explanation="This check needs the network or a remote query.",
            source=EvidenceSource.NETWORK,
        )
    return None


def diagnose(ctx: DiagnosticContext) -> Report:
    results = run_checks(ctx)
    diagnoses = correlate(results, ctx.facts)
    return Report(
        version=__version__,
        generated_at=ctx.now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        results=results,
        diagnoses=diagnoses,
        facts=dict(ctx.facts),
    )
