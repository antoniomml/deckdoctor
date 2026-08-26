from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "NET-GITHUB"
TITLE = "GitHub"

RATE_URL = "https://api.github.com/rate_limit"
HEAD_URL = "https://github.com/"


def run(ctx: DiagnosticContext) -> CheckResult:
    if not ctx.network_enabled:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Network checks disabled",
            source=EvidenceSource.NETWORK,
        )

    head = ctx.http.request("HEAD", HEAD_URL, timeout=8.0)
    evidence = [f"HEAD {HEAD_URL} → status={head.status} error={head.error}"]
    if not head.ok and head.status is None:
        ctx.facts.github_reachable = False
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "github.com is not reachable",
            explanation="Decky installs and many plugin remote binaries come from GitHub.",
            recommendation="Check DNS and connectivity. DeckDoctor does not run speed tests.",
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
            TITLE,
            Status.WARNING,
            "GitHub is up but the rate-limit API could not be read",
            explanation="GET /rate_limit does not consume the primary REST quota. This failure is separate from remaining=0.",
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
            TITLE,
            Status.UNKNOWN,
            "Could not parse GitHub rate-limit JSON",
            evidence=evidence + [api.body[:300]],
            source=EvidenceSource.NETWORK,
        )

    ctx.facts.github_remaining = remaining
    ctx.facts.github_limit = limit
    ctx.facts.github_reset = reset
    reset_in = ""
    if reset:
        delta = max(0, reset - int(ctx.now.timestamp()))
        reset_in = f"; reset in {delta // 60} min"
    finding = f"GitHub reachable; API {remaining}/{limit} remaining{reset_in}"

    if remaining <= 0:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "GitHub API rate limit exhausted",
            explanation=(
                "Unauthenticated GitHub REST allows 60 requests per hour per IP (CGNAT shares that quota). "
                "The Decky GUI installer historically failed in this state and could skip downloading PluginLoader."
            ),
            recommendation="Wait for the reset time, switch to a different network (phone hotspot), then reinstall. DeckDoctor does not use your GitHub credentials.",
            evidence=evidence,
            source=EvidenceSource.NETWORK,
            severity=Severity.HIGH,
            extra={"remaining": remaining, "limit": limit, "reset": reset},
        )
    if remaining < 10:
        return result(
            ID,
            TITLE,
            Status.WARNING,
            finding,
            explanation="Low remaining quota can still break the installer if it lists releases via the API.",
            recommendation="Avoid re-running the installer until the quota resets if install already failed.",
            evidence=evidence,
            source=EvidenceSource.NETWORK,
            extra={"remaining": remaining, "limit": limit},
        )
    return result(
        ID,
        TITLE,
        Status.PASS,
        finding,
        explanation="Rate-limit lookup uses GET /rate_limit, which does not consume the primary quota.",
        evidence=evidence,
        source=EvidenceSource.NETWORK,
        extra={"remaining": remaining, "limit": limit},
    )
