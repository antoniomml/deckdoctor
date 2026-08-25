from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "DECKY-SERVICE"
TITLE = "Decky service"

UNIT = "plugin_loader.service"


def run(ctx: DiagnosticContext) -> CheckResult:
    if ctx.facts.get("decky_installed") is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Decky is not installed",
            source=EvidenceSource.SYSTEMD,
        )

    evidence: list[str] = []
    enabled = ctx.run(["systemctl", "is-enabled", UNIT])
    active = ctx.run(["systemctl", "is-active", UNIT])
    show = ctx.run(
        [
            "systemctl",
            "show",
            UNIT,
            "-p",
            "LoadState,ActiveState,SubState,Result,ExecMainStatus,NRestarts,UnitFileState,InactiveExitTimestamp,ExecMainCode",
        ]
    )

    if enabled.error == "not_found" and active.error == "not_found":
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "systemctl is not available",
            source=EvidenceSource.SYSTEMD,
        )

    enabled_s = (enabled.stdout or enabled.stderr).strip().splitlines()[0] if (enabled.stdout or enabled.stderr) else "unknown"
    active_s = (active.stdout or active.stderr).strip().splitlines()[0] if (active.stdout or active.stderr) else "unknown"
    evidence.append(f"is-enabled: {enabled_s} (exit {enabled.exit_code})")
    evidence.append(f"is-active: {active_s} (exit {active.exit_code})")
    if show.stdout:
        evidence.append(show.stdout.strip()[:600])

    props = {}
    for line in show.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            props[k] = v
    load_state = props.get("LoadState", "")
    result_state = props.get("Result", "")
    main_status = props.get("ExecMainStatus", "")
    nrestarts = props.get("NRestarts", "")
    ctx.facts["decky_service_active"] = active_s
    ctx.facts["decky_service_enabled"] = enabled_s
    ctx.facts["decky_service_result"] = result_state

    if "not-found" in enabled_s or load_state == "not-found":
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "plugin_loader.service is not installed",
            explanation="Homebrew files may exist, but systemd has no plugin_loader unit.",
            recommendation="Re-run the official Decky installer so it installs the systemd unit.",
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
            severity=Severity.HIGH,
        )

    if enabled_s == "masked" or "masked" in enabled_s:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "plugin_loader.service is masked",
            explanation="A masked unit will not start. DeckDoctor will not unmask it.",
            recommendation="If you did not mask it on purpose, unmask via systemctl after reading systemd docs — or reinstall Decky.",
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
            severity=Severity.HIGH,
        )

    if active_s == "failed" or result_state == "failed":
        return result(
            ID,
            TITLE,
            Status.FAIL,
            f"plugin_loader.service failed (result={result_state or active_s}, status={main_status})",
            explanation="The Decky backend service is not running. This often follows a missing PluginLoader, bad permissions, or a corrupt unit file.",
            recommendation="Read the backend logs section. Do not systemctl restart blindly until you know why it failed. DeckDoctor will not restart it.",
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
            severity=Severity.HIGH,
            extra={"nrestarts": nrestarts},
        )

    if active_s in {"inactive", "dead"}:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            "plugin_loader.service is not running",
            explanation="The unit exists but is inactive. Decky cannot inject into Steam without this service.",
            recommendation="Start it only if you intend to: `systemctl start plugin_loader.service` (requires root). DeckDoctor will not do that.",
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
            severity=Severity.HIGH,
        )

    if active_s == "active":
        finding = "Service active"
        if enabled_s not in {"enabled", "enabled-runtime"}:
            finding += f" (enabled={enabled_s})"
        if nrestarts and nrestarts not in {"0", ""}:
            finding += f", NRestarts={nrestarts}"
            return result(
                ID,
                TITLE,
                Status.WARNING,
                finding,
                explanation="The service is up but has restarted recently. That can indicate a crash loop.",
                evidence=evidence,
                source=EvidenceSource.SYSTEMD,
                extra={"nrestarts": nrestarts},
            )
        return result(
            ID,
            TITLE,
            Status.PASS,
            finding,
            explanation="systemd reports plugin_loader.service as active. DeckDoctor did not restart anything.",
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
        )

    return result(
        ID,
        TITLE,
        Status.UNKNOWN,
        f"Unexpected service state: enabled={enabled_s} active={active_s}",
        evidence=evidence,
        source=EvidenceSource.SYSTEMD,
    )
