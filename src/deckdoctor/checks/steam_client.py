from __future__ import annotations

import re

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "STEAM-CLIENT"
TITLE = "Steam client"

_VERSION_RE = re.compile(r"version\s*\(?\s*(\d{9,12})", re.I)
_BUILD_RE = re.compile(r"\bbuildid[=:]?\s*(\d{9,12})", re.I)


def _scan_version(text: str) -> str | None:
    m = _VERSION_RE.search(text) or _BUILD_RE.search(text)
    return m.group(1) if m else None


def _looks_beta(text: str) -> bool | None:
    lowered = text.lower()
    if "steam deck beta" in lowered or "steamdeck beta" in lowered:
        return True
    if '"betaname"' in lowered or "betakey" in lowered:
        return True
    # Avoid treating random "beta" plugin names as the Steam client channel.
    if "clientbeta" in lowered or "wantbeta" in lowered:
        return True
    return None


def run(ctx: DiagnosticContext) -> CheckResult:
    steam = ctx.steam_root
    evidence: list[str] = [f"steam root candidate: {steam}"]
    version: str | None = None
    channel = "unknown"

    installed = steam / "package" / "steam_client_ubuntu12.installed"
    text = ctx.read_text(installed)
    if text:
        version = _scan_version(text) or version
        evidence.append(f"read {installed}")

    logs_dir = steam / "logs"
    for name in ("console_log.txt", "bootstrap_log.txt", "cef_log.txt"):
        log_path = logs_dir / name
        log_text = ctx.read_text(log_path, max_bytes=200_000)
        if not log_text:
            continue
        version = version or _scan_version(log_text)
        beta = _looks_beta(log_text)
        if beta:
            channel = "beta"
        evidence.append(f"scanned {log_path}")
        if version:
            break

    config = steam / "config" / "config.vdf"
    cfg_text = ctx.read_text(config, max_bytes=200_000)
    if cfg_text:
        beta = _looks_beta(cfg_text)
        if beta:
            channel = "beta"
        elif 'UpdateChannel' in cfg_text or "SteamDeck" in cfg_text:
            if re.search(r'"UpdateChannel"\s+"0"', cfg_text):
                channel = "stable"
        evidence.append(f"scanned {config}")

    # Desktop Steam stores the beta name here when opted in.
    beta_file = steam / "package" / "beta"
    if ctx.exists(beta_file):
        channel = "beta"
        evidence.append(f"present {beta_file}")

    ctx.facts["steam_version"] = version
    ctx.facts["steam_channel"] = channel

    if version is None and channel == "unknown" and not ctx.exists(steam):
        return result(
            ID,
            TITLE,
            Status.UNKNOWN,
            "Steam client metadata not found",
            explanation="No ~/.steam/steam or ~/.local/share/Steam tree was readable.",
            evidence=evidence,
            source=EvidenceSource.STEAM_METADATA,
        )

    finding_parts = []
    if version:
        finding_parts.append(f"build {version}")
    finding_parts.append(f"channel {channel}")
    finding = ", ".join(finding_parts)

    if channel == "beta":
        return result(
            ID,
            TITLE,
            Status.INFO,
            finding,
            explanation=(
                "Steam client Beta is a correlation factor for Decky QAM issues, "
                "not proof that Beta is broken. DeckDoctor does not keep a build×Decky matrix."
            ),
            recommendation="If Decky vanished from the QAM after a client update, try Steam Deck Stable as a test, then update Decky.",
            evidence=evidence,
            source=EvidenceSource.STEAM_METADATA,
            severity=Severity.LOW,
            extra={"version": version, "channel": channel},
        )

    status = Status.PASS if version else Status.UNKNOWN
    return result(
        ID,
        TITLE,
        status,
        finding,
        explanation="Parsed from local Steam files only.",
        evidence=evidence,
        source=EvidenceSource.STEAM_METADATA,
        extra={"version": version, "channel": channel},
    )
