from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "FP-UPDATES"
TITLE = "Flatpak updates"


def run(ctx: DiagnosticContext) -> CheckResult:
    if ctx.facts.get("flatpak_available") is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "flatpak is not available",
            source=EvidenceSource.FLATPAK,
        )

    proc = ctx.run(
        ["flatpak", "remote-ls", "--updates", "--columns=application,branch,origin"],
        timeout=45.0,
    )
    evidence = [f"exit {proc.exit_code}"]
    if proc.timed_out:
        ctx.facts["flatpak_update_check"] = "timeout"
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "Flatpak update check timed out",
            explanation="A failed or timed-out check is not the same as zero updates.",
            evidence=[proc.stderr.strip()[:400]],
            source=EvidenceSource.FLATPAK,
        )
    if proc.error == "not_found":
        return result(ID, TITLE, Status.SKIPPED, "flatpak is not available", source=EvidenceSource.FLATPAK)

    stderr = proc.stderr.strip()
    stdout = proc.stdout.strip()
    if stderr:
        evidence.append(stderr[:500])
    errorish = any(
        token in stderr.lower()
        for token in ("error", "failed", "not found", "couldn't", "could not", "invalid", "no such")
    )
    if not proc.ok or errorish:
        ctx.facts["flatpak_update_check"] = "failed"
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "Flatpak could not check for updates",
            explanation=(
                "The remote query exited unsuccessfully or reported an error. "
                "DeckDoctor will not report this as '0 updates'."
            ),
            recommendation="Inspect remotes (`flatpak remotes`) and stderr below. Stale remotes (refs that no longer exist) are a common cause. Do not run `flatpak update` from DeckDoctor.",
            evidence=evidence + ([stdout[:400]] if stdout else []),
            source=EvidenceSource.FLATPAK,
            extra={"stderr": stderr[:1000]},
        )

    rows = [ln for ln in stdout.splitlines() if ln.strip() and not ln.lower().startswith("application")]
    ctx.facts["flatpak_updates"] = rows
    ctx.facts["flatpak_update_check"] = "ok"
    if not rows:
        return result(
            ID,
            TITLE,
            Status.PASS,
            "No Flatpak updates reported",
            explanation="remote-ls --updates succeeded with an empty list.",
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
            extra={"count": 0},
        )
    return result(
        ID,
        TITLE,
        Status.WARNING,
        f"{len(rows)} Flatpak update(s) available",
        explanation="Listed only. DeckDoctor did not apply updates.",
        recommendation="Update from Discover/AutoFlatpaks/Desktop when convenient: `flatpak update` is a user action, not a DeckDoctor action.",
        evidence=evidence + rows[:20],
        source=EvidenceSource.FLATPAK,
        extra={"count": len(rows)},
    )
