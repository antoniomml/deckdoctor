from __future__ import annotations

from deckdoctor.checks._util import first_line, result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "FP-BASIC"
TITLE = "Flatpak basics"


def run(ctx: DiagnosticContext) -> CheckResult:
    version = ctx.run(["flatpak", "--version"])
    if version.error == "not_found":
        ctx.facts.flatpak_available = False
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "flatpak is not installed or not on PATH",
            explanation="AutoFlatpaks and Desktop software management need the Flatpak CLI.",
            source=EvidenceSource.FLATPAK,
        )
    if not version.ok:
        ctx.facts.flatpak_available = False
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "flatpak --version failed",
            evidence=[version.stderr.strip() or version.stdout.strip()],
            source=EvidenceSource.FLATPAK,
        )

    ctx.facts.flatpak_available = True
    ctx.facts.flatpak_version = first_line(version.stdout)
    remotes = ctx.run(["flatpak", "remotes", "--columns=name,options,url"], timeout=20.0)
    evidence = [first_line(version.stdout)]
    if remotes.timed_out:
        return result(
            ID,
            TITLE,
            Status.UNKNOWN,
            "flatpak remotes timed out",
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )
    if not remotes.ok:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "Could not list Flatpak remotes",
            explanation="The CLI exists but listing remotes failed. Custom remotes are not treated as errors when listing succeeds.",
            evidence=evidence + [remotes.stderr.strip()[:400] or remotes.stdout[:400]],
            source=EvidenceSource.FLATPAK,
        )

    lines = [ln for ln in remotes.stdout.splitlines() if ln.strip() and not ln.lower().startswith("name")]
    ctx.facts.flatpak_remotes_raw = remotes.stdout
    ctx.facts.flatpak_remote_count = len(lines)
    evidence.append(f"{len(lines)} remote(s)")
    evidence.extend(lines[:15])
    return result(
        ID,
        TITLE,
        Status.PASS,
        f"Flatpak working, {len(lines)} remote(s) configured",
        explanation="Custom remotes are allowed. Disabled or extra remotes are not automatically failures.",
        evidence=evidence,
        source=EvidenceSource.FLATPAK,
        extra={"remotes": len(lines)},
    )
