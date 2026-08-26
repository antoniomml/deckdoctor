from __future__ import annotations

from collections import defaultdict
from typing import Any

from deckdoctor.checks._util import result, version_is_newer
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "PLUGIN-STORE-UPDATES"
TITLE = "Plugin Store updates"


def _norm(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _catalog_index(entries: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in entries:
        name = _norm(item.get("name") or "")
        if not name:
            continue
        index[name].append(item)
    return index


def _unique_match(local: dict[str, Any], index: dict[str, list[dict[str, str]]]) -> dict[str, str] | None:
    keys: list[str] = []
    for raw in (local.get("name"), local.get("dir")):
        key = _norm(str(raw or ""))
        if key and key not in keys:
            keys.append(key)
    hits: list[dict[str, str]] = []
    seen: set[str] = set()
    for key in keys:
        for item in index.get(key, ()):
            ident = item.get("id") or item.get("name") or ""
            if ident in seen:
                continue
            seen.add(ident)
            hits.append(item)
    if len(hits) != 1:
        return None
    return hits[0]


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
    if ctx.facts.decky_installed is False:
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("skip.decky_missing"),
            source=EvidenceSource.DECKY_METADATA,
        )
    if ctx.facts.store_ok is False:
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("plugin.store.unreachable"),
            source=EvidenceSource.NETWORK,
        )

    plugins = list(ctx.facts.plugins)
    catalog = list(ctx.facts.store_plugins)
    if not plugins:
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("plugin.store.no_plugins"),
            source=EvidenceSource.DECKY_METADATA,
        )
    if not catalog:
        return result(
            ID,
            title,
            Status.INFO,
            ctx.tr("plugin.store.empty"),
            explanation=ctx.tr("plugin.store.empty.explain"),
            source=EvidenceSource.NETWORK,
        )

    index = _catalog_index(catalog)
    matched = 0
    updates: list[str] = []
    evidence: list[str] = [f"local={len(plugins)} store={len(catalog)}"]
    for plugin in plugins:
        hit = _unique_match(plugin, index)
        if hit is None:
            evidence.append(f"unmatched: {plugin.get('name')} ({plugin.get('dir')})")
            continue
        matched += 1
        local_ver = str(plugin.get("version") or "")
        store_ver = str(hit.get("version") or "")
        newer = version_is_newer(store_ver, local_ver)
        if newer is None:
            evidence.append(f"skipped versions: {plugin.get('name')} local={local_ver} store={store_ver}")
            continue
        if newer:
            line = f"{plugin.get('name')} {local_ver} → {store_ver}"
            updates.append(line)
            evidence.append(line)
        else:
            evidence.append(f"current: {plugin.get('name')} {local_ver}")

    ctx.facts.store_updates = updates
    if updates:
        return result(
            ID,
            title,
            Status.WARNING,
            ctx.tr("plugin.store.updates", count=len(updates)),
            explanation=ctx.tr("plugin.store.updates.explain"),
            recommendation=ctx.tr("plugin.store.updates.rec"),
            evidence=evidence[:40],
            source=EvidenceSource.NETWORK,
            severity=Severity.LOW,
            extra={"updates": updates, "matched": matched},
        )
    if matched == 0:
        return result(
            ID,
            title,
            Status.INFO,
            ctx.tr("plugin.store.unmatched"),
            explanation=ctx.tr("plugin.store.unmatched.explain"),
            evidence=evidence[:40],
            source=EvidenceSource.NETWORK,
            extra={"matched": 0},
        )
    return result(
        ID,
        title,
        Status.PASS,
        ctx.tr("plugin.store.ok", matched=matched),
        explanation=ctx.tr("plugin.store.ok.explain"),
        evidence=evidence[:40],
        source=EvidenceSource.NETWORK,
        extra={"matched": matched, "updates": []},
    )
