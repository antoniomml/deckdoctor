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
    if not ctx.network_enabled:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Network checks disabled",
            source=EvidenceSource.NETWORK,
        )

    resp = ctx.http.request("GET", STORE_URL, timeout=10.0)
    evidence = [f"GET {STORE_URL} → status={resp.status} error={resp.error}"]
    if not resp.ok:
        ctx.facts.store_ok = False
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "Decky Plugin Store is unreachable",
            explanation="Local Decky can still work while the store is down. Installing or updating plugins from the store will fail.",
            recommendation="Retry later. You can still sideload from a zip if you trust the source.",
            evidence=evidence + [resp.body[:200]],
            source=EvidenceSource.NETWORK,
        )

    body = resp.body.lstrip()
    looks_json = body.startswith("[") or body.startswith("{")
    ctx.facts.store_ok = looks_json
    if not looks_json:
        return result(
            ID,
            TITLE,
            Status.WARNING,
            "Plugin Store responded but the body is not JSON",
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
        TITLE,
        Status.PASS,
        "Plugin Store endpoint responded with JSON",
        explanation="This checks plugins.deckbrew.xyz/plugins only, not each plugin artifact CDN.",
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
