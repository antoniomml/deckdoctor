from __future__ import annotations

from deckdoctor.checks._util import (
    flatpak_remote_from_stderr,
    parse_flatpak_remotes,
    result,
)
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "FP-UPDATES"
TITLE = "Flatpak updates"

_ERR_TOKENS = ("error", "failed", "not found", "couldn't", "could not", "invalid", "no such")
_MAX_REMOTE_PROBES = 10


def _errorish(stderr: str) -> bool:
    low = stderr.lower()
    return any(token in low for token in _ERR_TOKENS)


def _update_rows(stdout: str) -> list[str]:
    return [ln for ln in stdout.splitlines() if ln.strip() and not ln.lower().startswith("application")]


def _probe_other_remotes(
    ctx: DiagnosticContext,
    *,
    skip: set[str],
    evidence: list[str],
) -> tuple[list[str], list[str]]:
    """When ``remote-ls -a`` dies on one remote, list the others individually."""
    rows: list[str] = []
    failed: list[str] = []
    remotes = parse_flatpak_remotes(ctx.facts.flatpak_remotes_raw or "")[:_MAX_REMOTE_PROBES]
    for name, scope in remotes:
        if name in skip:
            continue
        argv = ["flatpak", "remote-ls", scope, name, "--updates", "--columns=application,branch,origin"]
        proc = ctx.run(argv, timeout=20.0)
        evidence.append(f"{' '.join(argv)} exit {proc.exit_code}")
        if proc.timed_out or proc.error == "not_found":
            continue
        if proc.stderr.strip():
            evidence.append(proc.stderr.strip()[:300])
        if proc.ok and not _errorish(proc.stderr):
            rows.extend(_update_rows(proc.stdout))
            continue
        remote = flatpak_remote_from_stderr(proc.stderr) or name
        if remote not in failed:
            failed.append(remote)
    return rows, failed


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

    listing_bad = (not listing.ok) or _errorish(stderr)
    failed: list[str] = []
    if listing_bad:
        remote = flatpak_remote_from_stderr(stderr)
        if remote:
            failed.append(remote)

    rows: list[str] = []
    updates_bad = listing_bad
    upd_err = ""
    if listing_bad:
        extra_rows, extra_failed = _probe_other_remotes(ctx, skip=set(failed), evidence=evidence)
        rows.extend(extra_rows)
        for name in extra_failed:
            if name not in failed:
                failed.append(name)
    else:
        proc = ctx.run(
            ["flatpak", "remote-ls", "--updates", "--columns=application,branch,origin"],
            timeout=20.0,
        )
        evidence.append(f"remote-ls --updates exit {proc.exit_code}")
        if proc.timed_out:
            ctx.facts.flatpak_update_check = "timeout"
            ctx.facts.flatpak_failed_remotes = failed
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
        updates_bad = (not proc.ok) or _errorish(upd_err)
        if updates_bad:
            remote = flatpak_remote_from_stderr(upd_err)
            if remote and remote not in failed:
                failed.append(remote)
            extra_rows, extra_failed = _probe_other_remotes(ctx, skip=set(failed), evidence=evidence)
            rows.extend(extra_rows)
            for name in extra_failed:
                if name not in failed:
                    failed.append(name)
        else:
            rows = _update_rows(proc.stdout)

    ctx.facts.flatpak_failed_remotes = failed
    ctx.facts.flatpak_updates = rows

    if rows:
        ctx.facts.flatpak_update_check = "partial" if failed else "ok"
        finding = ctx.tr("fp.upd.some", count=len(rows))
        if failed:
            finding = ctx.tr("fp.upd.some_and_remote", count=len(rows), remote=", ".join(failed))
        return result(
            ID,
            title,
            Status.WARNING,
            finding,
            explanation=ctx.tr("fp.upd.some.explain") if not failed else ctx.tr("fp.upd.partial.explain"),
            recommendation=ctx.tr("fp.upd.some.rec"),
            evidence=evidence + rows[:20],
            source=EvidenceSource.FLATPAK,
            severity=Severity.MEDIUM,
            extra={"count": len(rows), "failed_remotes": failed},
        )

    if failed:
        probed_ok = any(line.endswith("exit 0") and "remote-ls --" in line for line in evidence)
        ctx.facts.flatpak_update_check = "partial" if probed_ok else "failed"
        remote = ", ".join(failed)
        if probed_ok:
            return result(
                ID,
                title,
                Status.WARNING,
                ctx.tr("fp.upd.fail.remote", remote=remote),
                explanation=ctx.tr("fp.upd.partial.explain"),
                recommendation=ctx.tr("fp.upd.fail.remote.rec", remote=remote),
                evidence=evidence,
                source=EvidenceSource.FLATPAK,
                severity=Severity.MEDIUM,
                extra={"count": 0, "failed_remotes": failed},
            )
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("fp.upd.fail.remote", remote=remote) if remote else ctx.tr("fp.upd.fail"),
            explanation=ctx.tr("fp.upd.fail.explain"),
            recommendation=ctx.tr("fp.upd.fail.remote.rec", remote=remote) if remote else ctx.tr("fp.upd.fail.rec"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
            extra={"stderr": (upd_err or stderr)[:1000], "failed_remotes": failed},
        )

    ctx.facts.flatpak_update_check = "ok"
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
