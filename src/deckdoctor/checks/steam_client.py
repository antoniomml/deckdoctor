from __future__ import annotations

import re

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "STEAM-CLIENT"
TITLE = "Steam client"

_VERSION_RE = re.compile(r'version["\'\s:=(]*(\d{9,12})', re.I)
_BUILD_RE = re.compile(r'\bbuildid["\'\s:=]*(\d{9,12})', re.I)


def _scan_version(text: str) -> str | None:
    m = _VERSION_RE.search(text) or _BUILD_RE.search(text)
    return m.group(1) if m else None


def _looks_beta(text: str) -> bool | None:
    lowered = text.lower()
    if "steam deck beta" in lowered or "steamdeck beta" in lowered:
        return True
    if '"betaname"' in lowered or "betakey" in lowered:
        return True
    if "clientbeta" in lowered or "wantbeta" in lowered:
        return True
    return None


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
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
        elif "UpdateChannel" in cfg_text or "SteamDeck" in cfg_text:
            if re.search(r'"UpdateChannel"\s+"0"', cfg_text):
                channel = "stable"
        evidence.append(f"scanned {config}")

    beta_file = steam / "package" / "beta"
    if ctx.exists(beta_file):
        channel = "beta"
        evidence.append(f"present {beta_file}")

    ctx.facts.steam_version = version
    ctx.facts.steam_channel = channel

    if version is None and channel == "unknown" and not ctx.exists(steam):
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("steam.missing"),
            explanation=ctx.tr("steam.missing.explain"),
            evidence=evidence,
            source=EvidenceSource.STEAM_METADATA,
        )

    parts: list[str] = []
    if version:
        parts.append(f"build {version}")
    if channel != "unknown":
        parts.append(f"channel {channel}")
    elif not version:
        parts.append(f"channel {channel}")
    finding = ", ".join(parts) if parts else f"channel {channel}"

    if channel == "beta":
        return result(
            ID,
            title,
            Status.INFO,
            finding,
            explanation=ctx.tr("steam.beta.explain"),
            recommendation=ctx.tr("steam.beta.rec"),
            evidence=evidence,
            source=EvidenceSource.STEAM_METADATA,
            severity=Severity.LOW,
            extra={"version": version, "channel": channel},
        )

    status = Status.PASS if version else Status.UNKNOWN
    return result(
        ID,
        title,
        status,
        finding,
        explanation=ctx.tr("steam.ok.explain"),
        evidence=evidence,
        source=EvidenceSource.STEAM_METADATA,
        extra={"version": version, "channel": channel},
    )
