from __future__ import annotations

import json

from deckdoctor.checks._util import result, skip_no_decky
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


def _cef_excerpt(body: str, *, limit: int = 8, width: int = 160) -> list[str]:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    lines: list[str] = []
    for item in data[:limit]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip() or "(untitled)"
        url = str(item.get("url") or item.get("webSocketDebuggerUrl") or "").strip()
        line = f"{title} {url}".strip()
        if len(line) > width:
            line = line[: width - 1] + "…"
        lines.append(line)
    return lines


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
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

    skipped = skip_no_decky(ctx, ID, title, source=EvidenceSource.LOCALHOST)
    if skipped:
        skipped.evidence = evidence
        return skipped

    if not cef_enabled:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("decky.front.no_cef"),
            explanation=ctx.tr("decky.front.no_cef.explain"),
            recommendation=ctx.tr("decky.front.no_cef.rec"),
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            severity=Severity.HIGH,
        )

    http = ctx.http.request("GET", "http://127.0.0.1:8080/json", timeout=3.0, follow_redirects=True)
    evidence.append(f"GET 127.0.0.1:8080/json → status={http.status} error={http.error}")
    if http.body:
        excerpt = _cef_excerpt(http.body)
        ctx.facts.cef_excerpt = excerpt
        if excerpt:
            evidence.extend(excerpt)
        else:
            evidence.append(http.body[:300])

    conflict = bool(ctx.facts.port_8080_conflict)
    if http.status == 404 or (http.body and "page not found" in http.body.lower()):
        ctx.facts.cef_json_ok = False
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("decky.front.not_cef"),
            explanation=ctx.tr("decky.front.not_cef.explain"),
            recommendation=ctx.tr("decky.front.not_cef.rec"),
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
            severity=Severity.HIGH,
            extra={"cef_json": False},
        )

    if conflict:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("decky.front.conflict"),
            explanation=ctx.tr("decky.front.conflict.explain"),
            recommendation=ctx.tr("decky.front.conflict.rec"),
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
            severity=Severity.HIGH,
        )

    if http.error and not http.ok:
        ctx.facts.cef_json_ok = False
        return result(
            ID,
            title,
            Status.WARNING,
            ctx.tr("decky.front.unreachable"),
            explanation=ctx.tr("decky.front.unreachable.explain"),
            recommendation=ctx.tr("decky.front.unreachable.rec"),
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
            title,
            Status.WARNING,
            ctx.tr("decky.front.beta"),
            explanation=ctx.tr("decky.front.beta.explain"),
            recommendation=ctx.tr("decky.front.beta.rec"),
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
            severity=Severity.MEDIUM,
            extra={"cef_json": True, "steam_beta": True},
        )

    if looks:
        return result(
            ID,
            title,
            Status.PASS,
            ctx.tr("decky.front.ok"),
            explanation=ctx.tr("decky.front.ok.explain"),
            evidence=evidence,
            source=EvidenceSource.LOCALHOST,
            extra={"cef_json": True},
        )

    return result(
        ID,
        title,
        Status.UNKNOWN,
        ctx.tr("decky.front.unknown"),
        evidence=evidence,
        source=EvidenceSource.LOCALHOST,
        extra={"cef_json": False},
    )
