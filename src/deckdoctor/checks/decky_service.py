from __future__ import annotations

from deckdoctor.checks._util import result, skip_no_decky
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "DECKY-SERVICE"
TITLE = "Decky service"

UNIT = "plugin_loader.service"


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    skipped = skip_no_decky(ctx, ID, title, source=EvidenceSource.SYSTEMD)
    if skipped:
        return skipped

    evidence: list[str] = []
    enabled = ctx.run(["systemctl", "is-enabled", UNIT])
    active = ctx.run(["systemctl", "is-active", UNIT])
    show = ctx.run(
        [
            "systemctl",
            "show",
            UNIT,
            "-p",
            "LoadState,ActiveState,SubState,Result,ExecMainStatus,NRestarts,UnitFileState,InactiveExitTimestamp,ExecMainCode,MainPID",
        ]
    )

    if enabled.error == "not_found" and active.error == "not_found":
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("decky.service.no_systemctl"),
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
    ctx.facts.decky_service_active = active_s
    ctx.facts.decky_service_enabled = enabled_s
    ctx.facts.decky_service_result = result_state
    pid_raw = props.get("MainPID", "")
    if pid_raw.isdigit() and int(pid_raw) > 0:
        ctx.facts.decky_service_pid = int(pid_raw)

    if "not-found" in enabled_s or load_state == "not-found":
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("decky.service.missing_unit"),
            explanation=ctx.tr("decky.service.missing_unit.explain"),
            recommendation=ctx.tr("decky.service.missing_unit.rec"),
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
            severity=Severity.HIGH,
        )

    if enabled_s == "masked" or "masked" in enabled_s:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("decky.service.masked"),
            explanation=ctx.tr("decky.service.masked.explain"),
            recommendation=ctx.tr("decky.service.masked.rec"),
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
            severity=Severity.HIGH,
        )

    if active_s == "failed" or result_state == "failed":
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("decky.service.failed", result=result_state or active_s, status=main_status),
            explanation=ctx.tr("decky.service.failed.explain"),
            recommendation=ctx.tr("decky.service.failed.rec"),
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
            severity=Severity.HIGH,
            extra={"nrestarts": nrestarts},
        )

    if active_s in {"inactive", "dead"}:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("decky.service.inactive"),
            explanation=ctx.tr("decky.service.inactive.explain"),
            recommendation=ctx.tr("decky.service.inactive.rec"),
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
            severity=Severity.HIGH,
        )

    if active_s == "active":
        finding = ctx.tr("decky.service.active")
        if enabled_s not in {"enabled", "enabled-runtime"}:
            finding += f" (enabled={enabled_s})"
        if nrestarts and nrestarts not in {"0", ""}:
            finding += f", NRestarts={nrestarts}"
            return result(
                ID,
                title,
                Status.WARNING,
                finding,
                explanation=ctx.tr("decky.service.restarts.explain"),
                evidence=evidence,
                source=EvidenceSource.SYSTEMD,
                extra={"nrestarts": nrestarts},
            )
        return result(
            ID,
            title,
            Status.PASS,
            finding,
            explanation=ctx.tr("decky.service.ok.explain"),
            evidence=evidence,
            source=EvidenceSource.SYSTEMD,
        )

    return result(
        ID,
        title,
        Status.UNKNOWN,
        ctx.tr("decky.service.unknown", enabled=enabled_s, active=active_s),
        evidence=evidence,
        source=EvidenceSource.SYSTEMD,
    )
