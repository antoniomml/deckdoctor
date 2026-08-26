from __future__ import annotations

from pathlib import Path
from typing import Any

from deckdoctor.checks._util import flatpak_remote_from_stderr, result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "AUTOFLATPAKS"
TITLE = "AutoFlatpaks"

_NAME_HINTS = ("autoflatpaks", "auto-flatpaks", "decky-autoflatpaks")


def _find_plugin(ctx: DiagnosticContext) -> dict[str, Any] | None:
    for plugin in ctx.facts.plugins:
        blob = f"{plugin.get('name', '')} {plugin.get('dir', '')}".lower()
        if any(h in blob for h in _NAME_HINTS):
            return plugin
    plugins_dir = ctx.plugins_dir
    if ctx.exists(plugins_dir):
        try:
            for entry in plugins_dir.iterdir():
                if entry.is_dir() and any(h in entry.name.lower() for h in _NAME_HINTS):
                    return {"name": entry.name, "dir": entry.name, "path": str(entry)}
        except OSError:
            return None
    return None


def run(ctx: DiagnosticContext) -> CheckResult:
    plugin = _find_plugin(ctx)
    title = ctx.tr(f"title.{ID}")
    if not plugin:
        ctx.facts.autoflatpaks_installed = False
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("auto.missing"),
            explanation=ctx.tr("auto.missing.explain"),
            source=EvidenceSource.FLATPAK,
        )

    ctx.facts.autoflatpaks_installed = True
    evidence = [f"plugin: {plugin.get('name')} ({plugin.get('dir')})"]
    log_path = Path(ctx.logs_dir) / plugin["dir"] / "backend.log"
    alt_log = Path(ctx.logs_dir) / plugin["dir"] / "plugin.log"
    log_text = (ctx.read_text(log_path) or "") + "\n" + (ctx.read_text(alt_log) or "")
    if log_text.strip():
        evidence.append(f"read logs under {ctx.logs_dir / plugin['dir']}")

    if ctx.facts.flatpak_available is False:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("auto.no_flatpak"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )

    log_fail = any(
        s in log_text.lower()
        for s in ("getremotepackagelist", "failed to digest", "returncode: 1", "unable to", "degraded")
    )

    if not ctx.network_enabled:
        return result(
            ID,
            title,
            Status.INFO,
            ctx.tr("auto.no_network"),
            explanation=ctx.tr("auto.no_network.explain"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )

    if ctx.facts.flatpak_failed_remotes:
        remote = ", ".join(ctx.facts.flatpak_failed_remotes)
        ctx.facts.autoflatpaks_remote_list_failed = True
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("auto.remote_fail.named", remote=remote),
            explanation=ctx.tr("auto.remote_fail.explain"),
            recommendation=ctx.tr("auto.remote_fail.named.rec", remote=remote),
            evidence=evidence + [f"failed remotes from FP-UPDATES: {remote}"],
            source=EvidenceSource.FLATPAK,
            extra={"remote_hint": remote, "log_fail": log_fail},
        )

    listing = ctx.probe_flatpak_listing()
    evidence.append(f"flatpak remote-ls -a exit {listing.exit_code}")
    if listing.stderr.strip():
        evidence.append(listing.stderr.strip()[:500])

    if listing.timed_out:
        ctx.facts.autoflatpaks_remote_list_failed = True
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("auto.timeout"),
            explanation=ctx.tr("auto.timeout.explain"),
            recommendation=ctx.tr("auto.timeout.rec"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )

    stderr_l = listing.stderr.lower()
    broken = any(tok in stderr_l for tok in ("error", "not found", "invalid", "couldn't", "no such", "failed"))
    if not listing.ok or broken:
        remote_hint = flatpak_remote_from_stderr(listing.stderr)
        ctx.facts.autoflatpaks_remote_list_failed = True
        finding = ctx.tr("auto.remote_fail.named", remote=remote_hint) if remote_hint else ctx.tr("auto.remote_fail")
        rec = ctx.tr("auto.remote_fail.named.rec", remote=remote_hint) if remote_hint else ctx.tr("auto.remote_fail.rec")
        return result(
            ID,
            title,
            Status.FAIL,
            finding,
            explanation=ctx.tr("auto.remote_fail.explain"),
            recommendation=rec,
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
            extra={"remote_hint": remote_hint, "log_fail": log_fail},
        )

    if log_fail:
        return result(
            ID,
            title,
            Status.WARNING,
            ctx.tr("auto.logs"),
            explanation=ctx.tr("auto.logs.explain"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )

    return result(
        ID,
        title,
        Status.PASS,
        ctx.tr("auto.ok"),
        explanation=ctx.tr("auto.ok.explain"),
        evidence=evidence,
        source=EvidenceSource.FLATPAK,
    )
