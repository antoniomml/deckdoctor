from __future__ import annotations

from datetime import datetime, timezone

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
    now = ctx.now
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    year = now.year
    evidence = [f"Clock (tool): {now.isoformat()}"]

    if year < 2024:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            f"System clock year is {year}",
            explanation="A clock this far in the past commonly breaks TLS and update checks.",
            recommendation="Connect to the internet and wait for NTP, or set the time in Desktop Mode. Do not disable TLS verification.",
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
            severity=Severity.HIGH,
        )

    proc = ctx.run(["timedatectl", "show"])
    if proc.error == "not_found":
        return result(
            ID,
            TITLE,
            Status.PASS,
            f"Clock year {year} looks sane (timedatectl not available)",
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
        )
    if proc.timed_out or not proc.ok:
        return result(
            ID,
            TITLE,
            Status.UNKNOWN,
            "Could not read timedatectl",
            evidence=evidence + [proc.stderr.strip()[:300]],
            source=EvidenceSource.OS_METADATA,
        )

    show = _parse_show(proc.stdout)
    ntp = show.get("NTP", "")
    synced = show.get("NTPSynchronized", "")
    ntp_enabled = show.get("NTPEnabled", ntp)
    evidence.append(proc.stdout.strip()[:400])
    ctx.facts["ntp_synchronized"] = synced.lower() == "yes"

    if synced.lower() == "no" and ntp_enabled.lower() == "yes":
        return result(
            ID,
            TITLE,
            Status.WARNING,
            "NTP is enabled but the clock is not synchronized",
            explanation="Unsynchronized time can cause TLS and GitHub/SteamOS update failures. This is not proof those failed.",
            recommendation="Wait for time sync or check network connectivity.",
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
            severity=Severity.LOW,
        )
    return result(
        ID,
        TITLE,
        Status.PASS,
        "System time looks reasonable",
        evidence=evidence,
        source=EvidenceSource.OS_METADATA,
        extra={"NTPSynchronized": synced},
    )
