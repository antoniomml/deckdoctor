from __future__ import annotations

from pathlib import Path

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "AUTOFLATPAKS"
TITLE = "AutoFlatpaks"

_NAME_HINTS = ("autoflatpaks", "auto-flatpaks", "decky-autoflatpaks")


def _find_plugin(ctx: DiagnosticContext) -> dict | None:
    for plugin in ctx.facts.get("plugins") or []:
        blob = f"{plugin.get('name','')} {plugin.get('dir','')}".lower()
        if any(h in blob for h in _NAME_HINTS):
            return plugin
    # Directory probe if inventory did not run
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
    if not plugin:
        ctx.facts["autoflatpaks_installed"] = False
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "AutoFlatpaks is not installed",
            explanation="Optional plugin. No extra Flatpak package-list check was added.",
            source=EvidenceSource.FLATPAK,
        )

    ctx.facts["autoflatpaks_installed"] = True
    evidence = [f"plugin: {plugin.get('name')} ({plugin.get('dir')})"]
    log_path = Path(ctx.logs_dir) / plugin["dir"] / "backend.log"
    alt_log = Path(ctx.logs_dir) / plugin["dir"] / "plugin.log"
    log_text = (ctx.read_text(log_path) or "") + "\n" + (ctx.read_text(alt_log) or "")
    if log_text.strip():
        evidence.append(f"read logs under {ctx.logs_dir / plugin['dir']}")

    if ctx.facts.get("flatpak_available") is False:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "AutoFlatpaks is installed but the Flatpak CLI is not working",
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )

    # Current AutoFlatpaks getRemotePackageList uses remote-ls (read-only).
    listing = ctx.run(
        ["flatpak", "remote-ls", "--columns=ref,origin", "-a"],
        timeout=45.0,
    )
    evidence.append(f"flatpak remote-ls -a exit {listing.exit_code}")
    if listing.stderr.strip():
        evidence.append(listing.stderr.strip()[:500])

    log_fail = any(
        s in log_text.lower()
        for s in ("getremotepackagelist", "failed to digest", "returncode: 1", "unable to", "degraded")
    )

    if listing.timed_out:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "AutoFlatpaks cannot generate a remote package list (flatpak remote-ls timed out)",
            explanation="The plugin itself appears installed; Flatpak did not return a remote list in time.",
            recommendation="Check network and remotes. DeckDoctor will not delete remotes.",
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )

    stderr_l = listing.stderr.lower()
    broken = any(
        tok in stderr_l for tok in ("error", "not found", "invalid", "couldn't", "no such", "failed")
    )
    if not listing.ok or broken:
        remote_hint = ""
        for token in listing.stderr.replace(",", " ").split():
            if token.lower() in {"kdeapps", "flathub", "fedora", "gnome-nightly"} or "." in token and "/" not in token:
                remote_hint = token
                break
        ctx.facts["autoflatpaks_remote_list_failed"] = True
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "AutoFlatpaks cannot generate its remote package list",
            explanation=(
                "AutoFlatpaks is installed. Current versions call `flatpak remote-ls` (not `flatpak update`) "
                "to build the remote package list. Flatpak reported an error, so the plugin cannot show available packages. "
                + (f"Stderr mentions {remote_hint}. " if remote_hint else "")
                + "A stale remote (historically kdeapps / distribute.kde.org NX) is a known cause."
            ),
            recommendation=(
                "Inspect `flatpak remotes`. If a remote you do not need is failing, you can remove it yourself "
                "(`flatpak remote-delete NAME`). Custom remotes are not automatically wrong. DeckDoctor will not delete them."
            ),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
            extra={"remote_hint": remote_hint, "log_fail": log_fail},
        )

    if log_fail:
        return result(
            ID,
            TITLE,
            Status.WARNING,
            "AutoFlatpaks logs look unhappy even though remote-ls succeeded now",
            explanation="The plugin may have failed earlier. Current Flatpak listing works.",
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )

    return result(
        ID,
        TITLE,
        Status.PASS,
        "AutoFlatpaks installed; Flatpak remote listing succeeded",
        explanation="This does not execute AutoFlatpaks' regex parser; it checks the same Flatpak operation the plugin needs.",
        evidence=evidence,
        source=EvidenceSource.FLATPAK,
    )
