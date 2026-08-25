from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "PLUGIN-INVENTORY"
TITLE = "Plugin inventory"


def _load_json(ctx: DiagnosticContext, path: Path) -> dict[str, Any] | None:
    text = ctx.read_text(path)
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def collect_plugins(ctx: DiagnosticContext) -> list[dict[str, Any]]:
    plugins_dir = ctx.plugins_dir
    collected: list[dict[str, Any]] = []
    if not ctx.exists(plugins_dir):
        return collected
    try:
        entries = sorted(plugins_dir.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return collected
    for entry in entries:
        if not entry.is_dir():
            continue
        plugin_json = _load_json(ctx, entry / "plugin.json") or {}
        package_json = _load_json(ctx, entry / "package.json") or {}
        name = plugin_json.get("name") or entry.name
        version = package_json.get("version") or plugin_json.get("version") or "unknown"
        remote = package_json.get("remote_binary") if isinstance(package_json.get("remote_binary"), list) else []
        collected.append(
            {
                "dir": entry.name,
                "path": str(entry),
                "name": name,
                "version": str(version),
                "author": plugin_json.get("author"),
                "flags": plugin_json.get("flags") or [],
                "remote_binary": remote,
                "has_main": (entry / "main.py").is_file(),
            }
        )
    return collected


def run(ctx: DiagnosticContext) -> CheckResult:
    if ctx.facts.get("decky_installed") is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Decky is not installed",
            source=EvidenceSource.DECKY_METADATA,
        )

    plugins = collect_plugins(ctx)
    ctx.facts["plugins"] = plugins
    names = [f"{p['name']} {p['version']}" for p in plugins]
    if not ctx.exists(ctx.plugins_dir):
        return result(
            ID,
            TITLE,
            Status.INFO,
            "No plugins directory yet",
            evidence=[str(ctx.plugins_dir)],
            source=EvidenceSource.DECKY_METADATA,
            extra={"count": 0},
        )
    if not plugins:
        return result(
            ID,
            TITLE,
            Status.INFO,
            "0 plugins detected",
            explanation="Only ~/homebrew/plugins was scanned.",
            evidence=[str(ctx.plugins_dir)],
            source=EvidenceSource.DECKY_METADATA,
            extra={"count": 0},
        )
    return result(
        ID,
        TITLE,
        Status.PASS,
        f"{len(plugins)} plugin(s) detected",
        explanation="Inventory from plugin.json / package.json only. Load success is covered by logs.",
        evidence=names[:30],
        source=EvidenceSource.DECKY_METADATA,
        extra={"count": len(plugins), "plugins": names},
    )
