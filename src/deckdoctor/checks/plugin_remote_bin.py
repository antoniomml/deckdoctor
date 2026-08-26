from __future__ import annotations

from pathlib import Path

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "PLUGIN-REMOTE-BIN"
TITLE = "Plugin remote binaries"

SIGNATURE = "Failed Downloading Remote Binaries"


def run(ctx: DiagnosticContext) -> CheckResult:
    plugins = ctx.facts.plugins or []
    if ctx.facts.decky_installed is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Decky is not installed",
            source=EvidenceSource.DECKY_METADATA,
        )

    issues: list[str] = []
    evidence: list[str] = []
    log_text = (ctx.facts.decky_log_text or "") + "\n"
    # plugin logs
    for plugin in plugins:
        log_file = Path(ctx.logs_dir) / plugin["dir"] / "plugin.log"
        extra = ctx.read_text(log_file, max_bytes=200_000)
        if extra:
            log_text += extra + "\n"
        backend_log = Path(ctx.logs_dir) / plugin["dir"] / "backend.log"
        extra_b = ctx.read_text(backend_log, max_bytes=200_000)
        if extra_b:
            log_text += extra_b + "\n"

        remotes = plugin.get("remote_binary") or []
        if not remotes:
            continue
        bin_dir = Path(plugin["path"]) / "bin"
        for item in remotes:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            dest = bin_dir / str(name)
            present = dest.is_file()
            evidence.append(f"{plugin['name']}: remote {name} → {'present' if present else 'MISSING'} ({dest})")
            if not present:
                issues.append(f"{plugin['name']}: missing remote binary {name}")

    log_hit = SIGNATURE in log_text
    ctx.facts.remote_binary_log_hit = log_hit
    if log_hit:
        evidence.append(f"log signature: {SIGNATURE}")

    if issues or log_hit:
        finding = issues[0] if issues else f"Decky logged: {SIGNATURE}"
        return result(
            ID,
            TITLE,
            Status.FAIL,
            finding,
            explanation=(
                "Plugins can declare extra GitHub/HTTP assets in package.json remote_binary. "
                "A failed download leaves the plugin installed but non-functional. DeckDoctor did not download anything."
            ),
            recommendation="Fix network/GitHub access, then reinstall the affected plugin from the Decky store. Do not chmod 777.",
            evidence=evidence[:20],
            source=EvidenceSource.DECKY_METADATA,
            severity=Severity.HIGH,
            extra={"missing": issues, "log_hit": log_hit},
        )

    declared = sum(1 for p in plugins if p.get("remote_binary"))
    return result(
        ID,
        TITLE,
        Status.PASS,
        f"No missing remote binaries ({declared} plugin(s) declare them)" if declared else "No plugins declare remote binaries",
        evidence=evidence or ["no remote_binary entries"],
        source=EvidenceSource.DECKY_METADATA,
    )
