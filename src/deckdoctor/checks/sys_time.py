from __future__ import annotations

from datetime import UTC

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "SYS-TIME"
TITLE = "System time"


def _parse_show(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            data[k.strip()] = v.strip()
    return data


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    now = ctx.now
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    year = now.year
    evidence = [f"Clock (tool): {now.isoformat()}"]

    if year < 2024:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("sys.time.past", year=year),
            explanation=ctx.tr("sys.time.past.explain"),
            recommendation=ctx.tr("sys.time.past.rec"),
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
            severity=Severity.HIGH,
        )

    proc = ctx.run(["timedatectl", "show"])
    if proc.error == "not_found":
        return result(
            ID,
            title,
            Status.PASS,
            ctx.tr("sys.time.no_timedatectl", year=year),
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
        )
    if proc.timed_out or not proc.ok:
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("sys.time.unknown"),
            evidence=evidence + [proc.stderr.strip()[:300]],
            source=EvidenceSource.OS_METADATA,
        )

    show = _parse_show(proc.stdout)
    ntp = show.get("NTP", "")
    synced = show.get("NTPSynchronized", "")
    ntp_enabled = show.get("NTPEnabled", ntp)
    evidence.append(proc.stdout.strip()[:400])
    ctx.facts.ntp_synchronized = synced.lower() == "yes"

    if synced.lower() == "no" and ntp_enabled.lower() == "yes":
        return result(
            ID,
            title,
            Status.WARNING,
            ctx.tr("sys.time.unsynced"),
            explanation=ctx.tr("sys.time.unsynced.explain"),
            recommendation=ctx.tr("sys.time.unsynced.rec"),
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
            severity=Severity.LOW,
        )
    return result(
        ID,
        title,
        Status.PASS,
        ctx.tr("sys.time.ok"),
        evidence=evidence,
        source=EvidenceSource.OS_METADATA,
        extra={"NTPSynchronized": synced},
    )
