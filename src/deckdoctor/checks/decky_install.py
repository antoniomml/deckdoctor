from __future__ import annotations

import json
import os

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "DECKY-INSTALL"
TITLE = "Decky installation"

_GITHUB_429_MARKERS = ("429: Too Many Requests", "API rate limit exceeded", "documentation_url")


def _read_branch(ctx: DiagnosticContext) -> str | None:
    settings = ctx.settings_dir
    if not ctx.exists(settings):
        return None
    try:
        files = list(settings.glob("*.json"))
    except OSError:
        return None
    for path in files:
        text = ctx.read_text(path)
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if "branch" in data:
            try:
                value = int(data["branch"])
            except (TypeError, ValueError):
                continue
            ctx.facts.decky_settings_file = str(path)
            return {0: "stable", 1: "prerelease", 2: "testing"}.get(value, str(value))
    return None


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    home = ctx.decky_home
    loader = ctx.plugin_loader
    evidence: list[str] = []
    ctx.facts.decky_home = str(home)

    if not ctx.exists(home):
        ctx.facts.decky_installed = False
        ctx.facts.plugin_loader_present = False
        return result(
            ID,
            title,
            Status.INFO,
            ctx.tr("decky.install.absent"),
            explanation=ctx.tr("decky.install.absent.explain", home=home),
            recommendation=ctx.tr("decky.install.absent.rec"),
            evidence=[f"missing {home}"],
            source=EvidenceSource.DECKY_METADATA,
            extra={"installed": False},
        )

    evidence.append(f"present {home}")
    version_text = (ctx.read_text(ctx.loader_version_file) or "").strip()
    if version_text:
        ctx.facts.decky_version = version_text
        evidence.append(f"version file: {version_text}")

    branch = _read_branch(ctx)
    if branch:
        ctx.facts.decky_channel = branch
        evidence.append(f"channel: {branch}")
    elif version_text and "-pre" in version_text:
        branch = "prerelease"
        ctx.facts.decky_channel = branch

    unit_text = ctx.read_text(ctx.systemd_unit_path)
    if unit_text is None:
        evidence.append(f"unit file not readable: {ctx.systemd_unit_path}")
        ctx.facts.decky_unit_readable = False
    else:
        ctx.facts.decky_unit_readable = True
        if any(m in unit_text for m in _GITHUB_429_MARKERS):
            ctx.facts.decky_unit_is_429 = True
            ctx.facts.plugin_loader_present = ctx.exists(loader)
            return result(
                ID,
                title,
                Status.FAIL,
                ctx.tr("decky.install.unit429"),
                explanation=ctx.tr("decky.install.unit429.explain"),
                recommendation=ctx.tr("decky.install.unit429.rec"),
                evidence=evidence + [f"{ctx.systemd_unit_path} starts with: {unit_text[:120]!r}"],
                source=EvidenceSource.DECKY_METADATA,
                severity=Severity.HIGH,
                extra={"unit_429": True},
            )
        if "ExecStart=" in unit_text:
            evidence.append("systemd unit has ExecStart")

    loader_present = ctx.exists(loader)
    ctx.facts.plugin_loader_present = loader_present
    ctx.facts.decky_installed = True

    if not loader_present:
        ctx.facts.decky_incomplete = True
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("decky.install.incomplete"),
            explanation=ctx.tr("decky.install.incomplete.explain", home=home, loader=loader),
            recommendation=ctx.tr("decky.install.incomplete.rec"),
            evidence=evidence + [f"missing {loader}"],
            source=EvidenceSource.DECKY_METADATA,
            severity=Severity.HIGH,
            extra={"incomplete": True},
        )

    executable = os.access(loader, os.X_OK)
    ctx.facts.plugin_loader_executable = executable
    evidence.append(f"PluginLoader present executable={executable}")
    if not executable:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("decky.install.not_exec"),
            explanation=ctx.tr("decky.install.not_exec.explain"),
            recommendation=ctx.tr("decky.install.not_exec.rec"),
            evidence=evidence,
            source=EvidenceSource.DECKY_METADATA,
            severity=Severity.HIGH,
        )

    finding = ctx.tr("decky.install.ok")
    if version_text:
        finding += f" {version_text}"
    if branch:
        finding += f" ({branch})"

    latest = None
    if ctx.network_enabled:
        http = ctx.http.request(
            "HEAD",
            "https://github.com/SteamDeckHomebrew/decky-loader/releases/latest",
            follow_redirects=True,
            timeout=10.0,
        )
        loc = http.final_url or http.headers.get("location") or ""
        if "/tag/" in loc:
            latest = loc.rstrip("/").split("/tag/")[-1]
            ctx.facts.decky_latest_stable = latest
            evidence.append(f"latest stable redirect: {latest}")

    extra = {"version": version_text, "channel": branch, "latest_stable": latest}
    if latest and version_text and latest.lstrip("v") not in version_text.lstrip("v") and version_text not in ("dev", "unknown"):
        if latest != version_text and not version_text.startswith(latest):
            return result(
                ID,
                title,
                Status.INFO,
                ctx.tr("decky.install.newer", finding=finding, latest=latest),
                explanation=ctx.tr("decky.install.newer.explain"),
                recommendation=ctx.tr("decky.install.newer.rec"),
                evidence=evidence,
                source=EvidenceSource.DECKY_METADATA,
                extra=extra,
            )

    return result(
        ID,
        title,
        Status.PASS,
        finding,
        explanation=ctx.tr("decky.install.ok.explain"),
        evidence=evidence,
        source=EvidenceSource.DECKY_METADATA,
        extra=extra,
    )
