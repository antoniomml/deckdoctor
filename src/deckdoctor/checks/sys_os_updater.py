from __future__ import annotations

from deckdoctor.checks._util import first_line, result, skip_not_steamos
from deckdoctor.command import CommandResult
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "SYS-OS-UPDATER"
TITLE = "SteamOS updater"

_UP_TO_DATE_MARKERS = (
    "no update",
    "up to date",
    "already up to date",
    "system is up to date",
    "no updates available",
)
_UPDATE_MARKERS = (
    "update available",
    "updates available",
    "new version",
)
_ERROR_MARKERS = (
    "timed out",
    "timeout",
    "failed",
    "error",
    "traceback",
    "no such file",
    "namehasnoowner",
    "could not activate",
)


def _combined(proc: CommandResult) -> str:
    return f"{proc.stdout}\n{proc.stderr}".lower()


def _looks_up_to_date(blob: str) -> bool:
    return any(m in blob for m in _UP_TO_DATE_MARKERS)


def _looks_update_available(blob: str) -> bool:
    if _looks_up_to_date(blob):
        return False
    return any(m in blob for m in _UPDATE_MARKERS)


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    skipped = skip_not_steamos(ctx, ID, title)
    if skipped:
        return skipped

    attempts: list[str] = []
    local = ((["atomupd-manager", "get-update-status"], 20.0),)
    remote = (
        (["atomupd-manager", "check"], 30.0),
        (["steamos-update", "check"], 30.0),
        (["steamos-atomupd-client", "--query-only"], 30.0),
    )
    commands = local + (remote if ctx.network_enabled else ())

    ran_any = False
    for argv, timeout in commands:
        proc = ctx.run(list(argv), timeout=timeout, cache=True)
        if proc.error == "not_found":
            attempts.append(f"{argv[0]}: not found")
            continue
        ran_any = True
        blob = _combined(proc)
        summary = first_line(proc.stdout or proc.stderr) or f"exit {proc.exit_code}"
        attempts.append(f"{' '.join(argv)} → exit {proc.exit_code}: {summary}")

        if proc.timed_out:
            ctx.facts.os_updater = "timeout"
            return result(
                ID,
                title,
                Status.FAIL,
                ctx.tr("sys.updater.timeout"),
                explanation=ctx.tr("sys.updater.timeout.explain"),
                recommendation=ctx.tr("sys.updater.timeout.rec"),
                evidence=attempts + [proc.stderr.strip()[:500]],
                source=EvidenceSource.OS_METADATA,
                severity=Severity.HIGH,
            )

        if any(m in blob for m in _ERROR_MARKERS) and not proc.ok:
            ctx.facts.os_updater = "error"
            return result(
                ID,
                title,
                Status.FAIL,
                ctx.tr("sys.updater.error"),
                explanation=ctx.tr("sys.updater.error.explain"),
                recommendation=ctx.tr("sys.updater.error.rec"),
                evidence=attempts,
                source=EvidenceSource.OS_METADATA,
                severity=Severity.HIGH,
            )

        if _looks_update_available(blob):
            ctx.facts.os_updater = "update_available"
            return result(
                ID,
                title,
                Status.WARNING,
                ctx.tr("sys.updater.available"),
                explanation=ctx.tr("sys.updater.available.explain"),
                recommendation=ctx.tr("sys.updater.available.rec"),
                evidence=attempts,
                source=EvidenceSource.OS_METADATA,
                severity=Severity.LOW,
                extra={"update_available": True},
            )

        if proc.ok and _looks_up_to_date(blob):
            ctx.facts.os_updater = "up_to_date"
            return result(
                ID,
                title,
                Status.PASS,
                ctx.tr("sys.updater.current"),
                explanation=ctx.tr("sys.updater.current.explain"),
                evidence=attempts,
                source=EvidenceSource.OS_METADATA,
                extra={"update_available": False},
            )

        if not proc.ok:
            ctx.facts.os_updater = "error"
            return result(
                ID,
                title,
                Status.FAIL,
                ctx.tr("sys.updater.nonzero"),
                explanation=ctx.tr("sys.updater.nonzero.explain"),
                evidence=attempts,
                source=EvidenceSource.OS_METADATA,
                severity=Severity.HIGH,
            )

    if not ran_any:
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("sys.updater.missing"),
            explanation=ctx.tr("sys.updater.missing.explain"),
            evidence=attempts,
            source=EvidenceSource.OS_METADATA,
        )

    ctx.facts.os_updater = "unknown"
    return result(
        ID,
        title,
        Status.UNKNOWN,
        ctx.tr("sys.updater.unknown"),
        explanation=ctx.tr("sys.updater.unknown.explain"),
        evidence=attempts,
        source=EvidenceSource.OS_METADATA,
    )
