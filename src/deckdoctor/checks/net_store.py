from __future__ import annotations

import json
from typing import Any

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "NET-STORE"
TITLE = "Decky Plugin Store"

STORE_URL = "https://plugins.deckbrew.xyz/plugins"


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    if not ctx.network_enabled:
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("skip.no_network"),
            source=EvidenceSource.NETWORK,
        )

    resp = ctx.http.request("GET", STORE_URL, timeout=10.0)
    evidence = [f"GET {STORE_URL} → status={resp.status} error={resp.error}"]
    if not resp.ok:
        ctx.facts.store_ok = False
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("net.store.down"),
            explanation=ctx.tr("net.store.down.explain"),
            recommendation=ctx.tr("net.store.down.rec"),
            evidence=evidence + [resp.body[:200]],
            source=EvidenceSource.NETWORK,
        )

    body = resp.body.lstrip()
    looks_json = body.startswith("[") or body.startswith("{")
    ctx.facts.store_ok = looks_json
    if not looks_json:
        return result(
            ID,
            title,
            Status.WARNING,
            ctx.tr("net.store.not_json"),
            evidence=evidence + [body[:200]],
            source=EvidenceSource.NETWORK,
        )
    try:
        parsed = resp.json()
    except json.JSONDecodeError:
        parsed = None
    catalog = _compact_catalog(parsed)
    ctx.facts.store_plugins = catalog
    evidence.append(f"{len(catalog)} catalog entries parsed")
    return result(
        ID,
        title,
        Status.PASS,
        ctx.tr("net.store.ok"),
        explanation=ctx.tr("net.store.ok.explain"),
        evidence=evidence,
        source=EvidenceSource.NETWORK,
        extra={"count": len(catalog)},
    )


def _compact_catalog(raw: Any) -> list[dict[str, str]]:
    items: list[Any]
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        nested = raw.get("plugins") or raw.get("items") or []
        items = nested if isinstance(nested, list) else []
    else:
        items = []
    catalog: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("plugin_name")
        if not name:
            continue
        version = item.get("version") or item.get("plugin_version") or ""
        ident = item.get("id") or item.get("artifact") or name
        catalog.append({"id": str(ident), "name": str(name), "version": str(version)})
    return catalog
