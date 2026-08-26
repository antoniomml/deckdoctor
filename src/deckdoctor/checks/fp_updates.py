from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "FP-UPDATES"
TITLE = "Flatpak updates"


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    if ctx.facts.flatpak_available is False:
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("skip.flatpak_missing"),
            source=EvidenceSource.FLATPAK,
        )

    listing = ctx.probe_flatpak_listing()
    evidence = [f"remote-ls -a exit {listing.exit_code}"]
    if listing.timed_out:
        ctx.facts.flatpak_update_check = "timeout"
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("fp.upd.timeout"),
            explanation=ctx.tr("fp.upd.timeout.explain"),
            evidence=[listing.stderr.strip()[:400]],
            source=EvidenceSource.FLATPAK,
        )
    if listing.error == "not_found":
        return result(ID, title, Status.SKIPPED, ctx.tr("skip.flatpak_missing"), source=EvidenceSource.FLATPAK)

    stderr = listing.stderr.strip()
    if stderr:
        evidence.append(stderr[:500])
    errorish = any(
        token in stderr.lower()
        for token in ("error", "failed", "not found", "couldn't", "could not", "invalid", "no such")
    )
    if not listing.ok or errorish:
        ctx.facts.flatpak_update_check = "failed"
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("fp.upd.fail"),
            explanation=ctx.tr("fp.upd.fail.explain"),
            recommendation=ctx.tr("fp.upd.fail.rec"),
            evidence=evidence + ([listing.stdout.strip()[:400]] if listing.stdout.strip() else []),
            source=EvidenceSource.FLATPAK,
            extra={"stderr": stderr[:1000]},
        )

    proc = ctx.run(
        ["flatpak", "remote-ls", "--updates", "--columns=application,branch,origin"],
        timeout=20.0,
    )
    evidence.append(f"remote-ls --updates exit {proc.exit_code}")
    if proc.timed_out:
        ctx.facts.flatpak_update_check = "timeout"
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("fp.upd.timeout"),
            explanation=ctx.tr("fp.upd.timeout.explain"),
            evidence=evidence + [proc.stderr.strip()[:400]],
            source=EvidenceSource.FLATPAK,
        )
    upd_err = proc.stderr.strip()
    if upd_err:
        evidence.append(upd_err[:500])
    upd_errorish = any(
        token in upd_err.lower()
        for token in ("error", "failed", "not found", "couldn't", "could not", "invalid", "no such")
    )
    if not proc.ok or upd_errorish:
        ctx.facts.flatpak_update_check = "failed"
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("fp.upd.fail"),
            explanation=ctx.tr("fp.upd.fail.explain"),
            recommendation=ctx.tr("fp.upd.fail.rec"),
            evidence=evidence + ([proc.stdout.strip()[:400]] if proc.stdout.strip() else []),
            source=EvidenceSource.FLATPAK,
            extra={"stderr": upd_err[:1000]},
        )

    stdout = proc.stdout.strip()
    rows = [ln for ln in stdout.splitlines() if ln.strip() and not ln.lower().startswith("application")]
    ctx.facts.flatpak_updates = rows
    ctx.facts.flatpak_update_check = "ok"
    if not rows:
        return result(
            ID,
            title,
            Status.PASS,
            ctx.tr("fp.upd.none"),
            explanation=ctx.tr("fp.upd.none.explain"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
            extra={"count": 0},
        )
    return result(
        ID,
        title,
        Status.WARNING,
        ctx.tr("fp.upd.some", count=len(rows)),
        explanation=ctx.tr("fp.upd.some.explain"),
        recommendation=ctx.tr("fp.upd.some.rec"),
        evidence=evidence + rows[:20],
        source=EvidenceSource.FLATPAK,
        extra={"count": len(rows)},
    )
