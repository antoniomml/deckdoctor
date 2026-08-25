from __future__ import annotations

from deckdoctor.checks._util import first_line, result
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


def _combined(proc) -> str:
    return f"{proc.stdout}\n{proc.stderr}".lower()


def run(ctx: DiagnosticContext) -> CheckResult:
    if ctx.facts.get("is_steamos") is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Not SteamOS",
            source=EvidenceSource.OS_METADATA,
        )

    attempts: list[str] = []
    commands = (
        (["atomupd-manager", "get-update-status"], 20.0),
        (["atomupd-manager", "check"], 30.0),
        (["steamos-update", "check"], 30.0),
        (["steamos-atomupd-client", "--query-only"], 30.0),
    )

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
            ctx.facts["os_updater"] = "timeout"
            return result(
                ID,
                TITLE,
                Status.FAIL,
                "SteamOS updater timed out while checking for updates",
                explanation=(
                    "The updater did not finish a read-only check in time. "
                    "This is not the same as being up to date."
                ),
                recommendation="Retry from Desktop Mode. If it keeps timing out, the atomupd service or network path to steamdeck-atomupd.steamos.cloud may be failing.",
                evidence=attempts + [proc.stderr.strip()[:500]],
                source=EvidenceSource.OS_METADATA,
                severity=Severity.HIGH,
            )

        if any(m in blob for m in _ERROR_MARKERS) and not proc.ok:
            ctx.facts["os_updater"] = "error"
            return result(
                ID,
                TITLE,
                Status.FAIL,
                "SteamOS updater could not check for updates",
                explanation="A local update query failed. DeckDoctor will not assume the system is current.",
                recommendation="Inspect atomupd/rauc journals. Do not treat this as 'up to date'.",
                evidence=attempts,
                source=EvidenceSource.OS_METADATA,
                severity=Severity.HIGH,
            )

        if any(m in blob for m in _UPDATE_MARKERS) or (proc.ok and "update available" in blob):
            ctx.facts["os_updater"] = "update_available"
            return result(
                ID,
                TITLE,
                Status.WARNING,
                "A SteamOS update appears to be available",
                explanation="The local updater reported an update. DeckDoctor did not install it.",
                recommendation="Apply the update from SteamOS Settings when you are ready. Reboot if the updater asks.",
                evidence=attempts,
                source=EvidenceSource.OS_METADATA,
                severity=Severity.LOW,
                extra={"update_available": True},
            )

        if proc.ok and (any(m in blob for m in _UP_TO_DATE_MARKERS) or not blob.strip()):
            # empty successful check is treated cautiously as unknown unless markers match
            if any(m in blob for m in _UP_TO_DATE_MARKERS):
                ctx.facts["os_updater"] = "up_to_date"
                return result(
                    ID,
                    TITLE,
                    Status.PASS,
                    "SteamOS updater reports no update available",
                    explanation="Based on a local query-only check, not a web scrape.",
                    evidence=attempts,
                    source=EvidenceSource.OS_METADATA,
                    extra={"update_available": False},
                )

        if not proc.ok:
            ctx.facts["os_updater"] = "error"
            return result(
                ID,
                TITLE,
                Status.FAIL,
                "SteamOS updater returned an error",
                explanation="Non-zero exit while querying updates. This is not interpreted as 'up to date'.",
                evidence=attempts,
                source=EvidenceSource.OS_METADATA,
                severity=Severity.HIGH,
            )

    if not ran_any:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "No SteamOS updater tools found",
            explanation="atomupd-manager, steamos-update, and steamos-atomupd-client are all missing.",
            evidence=attempts,
            source=EvidenceSource.OS_METADATA,
        )

    ctx.facts["os_updater"] = "unknown"
    return result(
        ID,
        TITLE,
        Status.UNKNOWN,
        "Could not determine SteamOS update state",
        explanation="A query ran but the output was not a known 'up to date' or 'update available' message.",
        evidence=attempts,
        source=EvidenceSource.OS_METADATA,
    )
