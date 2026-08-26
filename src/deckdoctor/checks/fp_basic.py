from __future__ import annotations

from deckdoctor.checks._util import first_line, result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "FP-BASIC"
TITLE = "Flatpak basics"


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    version = ctx.run(["flatpak", "--version"])
    if version.error == "not_found":
        ctx.facts.flatpak_available = False
        on_steamos = ctx.facts.is_steamos is True
        return result(
            ID,
            title,
            Status.FAIL if on_steamos else Status.INFO,
            ctx.tr("fp.basic.missing"),
            explanation=ctx.tr("fp.basic.missing.explain" if on_steamos else "fp.basic.missing.info.explain"),
            source=EvidenceSource.FLATPAK,
        )
    if not version.ok:
        ctx.facts.flatpak_available = False
        detail = first_line(version.stderr) or first_line(version.stdout)
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("fp.basic.version_fail"),
            explanation=ctx.tr("fp.basic.version_fail.explain"),
            evidence=[detail] if detail else [version.stderr.strip() or version.stdout.strip()],
            source=EvidenceSource.FLATPAK,
        )

    ctx.facts.flatpak_available = True
    ctx.facts.flatpak_version = first_line(version.stdout)
    remotes = ctx.run(["flatpak", "remotes", "--columns=name,options,url"], timeout=20.0)
    evidence = [first_line(version.stdout)]
    if remotes.timed_out:
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("fp.basic.timeout"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )
    if not remotes.ok:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("fp.basic.list_fail"),
            explanation=ctx.tr("fp.basic.list_fail.explain"),
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
        title,
        Status.PASS,
        ctx.tr("fp.basic.ok", count=len(lines)),
        explanation=ctx.tr("fp.basic.ok.explain"),
        evidence=evidence,
        source=EvidenceSource.FLATPAK,
        extra={"remotes": len(lines)},
    )
