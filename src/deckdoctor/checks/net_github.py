from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "NET-GITHUB"
TITLE = "GitHub"

RATE_URL = "https://api.github.com/rate_limit"
HEAD_URL = "https://github.com/"


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    if not ctx.network_enabled:
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("skip.no_network"),
            source=EvidenceSource.NETWORK,
        )

    head = ctx.http.request("HEAD", HEAD_URL, timeout=8.0)
    evidence = [f"HEAD {HEAD_URL} → status={head.status} error={head.error}"]
    if not head.ok and head.status is None:
        ctx.facts.github_reachable = False
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("net.gh.down"),
            explanation=ctx.tr("net.gh.down.explain"),
            recommendation=ctx.tr("net.gh.down.rec"),
            evidence=evidence,
            source=EvidenceSource.NETWORK,
            severity=Severity.HIGH,
        )

    ctx.facts.github_reachable = True
    api = ctx.http.request("GET", RATE_URL, timeout=8.0)
    evidence.append(f"GET {RATE_URL} → status={api.status} error={api.error}")
    if not api.ok:
        return result(
            ID,
            title,
            Status.WARNING,
            ctx.tr("net.gh.api_fail"),
            explanation=ctx.tr("net.gh.api_fail.explain"),
            evidence=evidence + [api.body[:200]],
            source=EvidenceSource.NETWORK,
        )

    try:
        payload = api.json() or {}
        core = (payload.get("resources") or {}).get("core") or {}
        remaining_raw = core.get("remaining")
        if remaining_raw is None:
            raise TypeError("missing remaining")
        remaining = int(remaining_raw)
        limit = int(core.get("limit", 60))
        reset = int(core.get("reset", 0))
    except (TypeError, ValueError, AttributeError):
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("net.gh.parse"),
            evidence=evidence + [api.body[:300]],
            source=EvidenceSource.NETWORK,
        )

    ctx.facts.github_remaining = remaining
    ctx.facts.github_limit = limit
    ctx.facts.github_reset = reset
    reset_in = ""
    if reset:
        delta = max(0, reset - int(ctx.now.timestamp()))
        reset_in = ctx.tr("net.gh.reset", minutes=delta // 60)
    finding = ctx.tr("net.gh.ok", remaining=remaining, limit=limit, reset=reset_in)

    if remaining <= 0:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("net.gh.exhausted"),
            explanation=ctx.tr("net.gh.exhausted.explain"),
            recommendation=ctx.tr("net.gh.exhausted.rec"),
            evidence=evidence,
            source=EvidenceSource.NETWORK,
            severity=Severity.HIGH,
            extra={"remaining": remaining, "limit": limit, "reset": reset},
        )
    if remaining < 10:
        return result(
            ID,
            title,
            Status.WARNING,
            finding,
            explanation=ctx.tr("net.gh.low.explain"),
            recommendation=ctx.tr("net.gh.low.rec"),
            evidence=evidence,
            source=EvidenceSource.NETWORK,
            extra={"remaining": remaining, "limit": limit},
        )
    return result(
        ID,
        title,
        Status.PASS,
        finding,
        explanation=ctx.tr("net.gh.ok.explain"),
        evidence=evidence,
        source=EvidenceSource.NETWORK,
        extra={"remaining": remaining, "limit": limit},
    )
