from __future__ import annotations

import json

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "DECKY-FRONTEND"
TITLE = "Decky frontend / CEF"


def _json_looks_like_cef(body: str) -> bool:
    text = body.strip()
    if not text:
        return False
    if "404" in text.lower() and "page not found" in text.lower():
        return False
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and (
            "webSocketDebuggerUrl" in first or "devtoolsFrontendUrl" in first or "title" in first
        ):
            return True
    return False


def run(ctx: DiagnosticContext) -> CheckResult:
    steam = ctx.steam_root
    cef_file = steam / ".cef-enable-remote-debugging"
    flatpak_cef = (
        ctx.home / ".var" / "app" / "com.valvesoftware.Steam" / "data" / "Steam" / ".cef-enable-remote-debugging"
    )
    cef_enabled = ctx.exists(cef_file) or ctx.exists(flatpak_cef)
    ctx.facts.cef_enable_file = cef_enabled
    evidence = [
        f"{cef_file}: {'present' if ctx.exists(cef_file) else 'missing'}",
    ]
    if ctx.exists(flatpak_cef):
        evidence.append(f"flatpak steam cef file present: {flatpak_cef}")

    if ctx.facts.decky_installed is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Decky is not installed",
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
        )

    if not cef_enabled:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "CEF remote debugging is not enabled",
            explanation=(
                "Decky injects into Steam through the CEF debugger. "
                "The installer normally creates ~/.steam/steam/.cef-enable-remote-debugging."
            ),
            recommendation="Re-run the official Decky installer, which touches that file. Do not expose CEF to the LAN unless you understand the risk.",
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            severity=Severity.HIGH,
        )

    http = ctx.http.request("GET", "http://127.0.0.1:8080/json", timeout=3.0, follow_redirects=True)
    evidence.append(f"GET 127.0.0.1:8080/json → status={http.status} error={http.error}")
    if http.body:
        evidence.append(http.body[:300])

    conflict = bool(ctx.facts.port_8080_conflict)
    if http.status == 404 or (http.body and "page not found" in http.body.lower()):
        ctx.facts.cef_json_ok = False
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "Port 8080 answered but is not Steam's CEF debugger",
            explanation=(
                "Decky expected Chrome DevTools JSON at http://127.0.0.1:8080/json. "
                "A 404 usually means another program (often Syncthing) owns 8080."
            ),
            recommendation="Move the conflicting app off port 8080. Syncthing's recommended port is 8384.",
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
            severity=Severity.HIGH,
            extra={"cef_json": False},
        )

    if conflict:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "Steam CEF port 8080 is in conflict",
            explanation="A non-Steam process is listening on 8080, so Decky cannot inject into Game Mode.",
            recommendation="Change the conflicting application's port. DeckDoctor will not kill it.",
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
            severity=Severity.HIGH,
        )

    if http.error and not http.ok:
        ctx.facts.cef_json_ok = False
        return result(
            ID,
            TITLE,
            Status.WARNING,
            "Could not reach Steam CEF debugger on localhost:8080",
            explanation=(
                "This is expected in Desktop Mode if Game Mode Steam is not running. "
                "If you are in Gaming Mode and Decky is missing from the QAM, CEF may be down or blocked."
            ),
            recommendation="Re-test from Gaming Mode. Confirm .cef-enable-remote-debugging still exists after Steam updates.",
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
            extra={"cef_json": False},
        )

    looks = _json_looks_like_cef(http.body)
    ctx.facts.cef_json_ok = looks
    backend_ok = ctx.facts.decky_service_active == "active" and ctx.facts.plugin_loader_present
    steam_beta = ctx.facts.steam_channel == "beta"

    if looks and backend_ok and steam_beta:
        return result(
            ID,
            TITLE,
            Status.WARNING,
            "Backend looks healthy and CEF is Steam; Steam client is on Beta",
            explanation=(
                "FACT: PluginLoader is present, the service is active, and :8080/json looks like Steam CEF. "
                "LIKELY CAUSE (medium): a Steam client Beta/UI change can hide Decky from the QAM even when the backend is fine. "
                "DeckDoctor cannot see the QAM itself from here."
            ),
            recommendation="Try Steam Deck Stable as a contrast, update Decky (stable or prerelease), and disable plugins one by one if React errors persist.",
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
            severity=Severity.MEDIUM,
            extra={"cef_json": True, "steam_beta": True},
        )

    if looks:
        return result(
            ID,
            TITLE,
            Status.PASS,
            "CEF debugger looks like Steam",
            explanation="localhost:8080/json returned DevTools targets. This does not prove the QAM tab is visible.",
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
            extra={"cef_json": True},
        )

    return result(
        ID,
        TITLE,
        Status.UNKNOWN,
        "CEF endpoint responded but was not recognized as Steam DevTools JSON",
        evidence=evidence,
        source=EvidenceSource.LOCALHOST,
        extra={"cef_json": False},
    )
