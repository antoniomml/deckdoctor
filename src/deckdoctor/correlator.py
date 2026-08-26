from __future__ import annotations

from deckdoctor.facts import Facts
from deckdoctor.i18n import translate
from deckdoctor.models import CheckResult, Confidence, Diagnosis, Severity, Status


def _by_id(results: list[CheckResult]) -> dict[str, CheckResult]:
    return {r.check_id: r for r in results}


def correlate(results: list[CheckResult], facts: Facts, locale: str = "en") -> list[Diagnosis]:
    """Explicit rules only. Prefer UNKNOWN over storytelling."""
    found: list[Diagnosis] = []
    by = _by_id(results)

    def t(key: str) -> str:
        return translate(locale, key)

    incomplete = bool(facts.decky_incomplete) or (
        facts.decky_installed and facts.plugin_loader_present is False
    )
    remaining = facts.github_remaining
    unit_429 = bool(facts.decky_unit_is_429)

    if incomplete and remaining == 0:
        found.append(
            Diagnosis(
                title=t("diag.incomplete_rate.title"),
                summary=t("diag.incomplete_rate.summary"),
                recommendation=t("diag.incomplete_rate.rec"),
                related_checks=["DECKY-INSTALL", "NET-GITHUB"],
                confidence=Confidence.HIGH,
                fact_kind="likely",
                severity=Severity.HIGH,
            )
        )
    elif unit_429:
        found.append(
            Diagnosis(
                title=t("diag.unit_429.title"),
                summary=t("diag.unit_429.summary"),
                recommendation=t("diag.unit_429.rec"),
                related_checks=["DECKY-INSTALL", "DECKY-SERVICE"],
                confidence=Confidence.HIGH,
                fact_kind="fact",
                severity=Severity.HIGH,
            )
        )
    elif incomplete:
        found.append(
            Diagnosis(
                title=t("diag.incomplete.title"),
                summary=t("diag.incomplete.summary"),
                recommendation=t("diag.incomplete.rec"),
                related_checks=["DECKY-INSTALL"],
                confidence=Confidence.HIGH,
                fact_kind="fact",
                severity=Severity.HIGH,
            )
        )

    backend_ok = facts.plugin_loader_present and facts.decky_service_active == "active"
    cef_ok = bool(facts.cef_json_ok)
    port_conflict = bool(facts.port_8080_conflict)
    steam_beta = facts.steam_channel == "beta"
    logs = by.get("DECKY-LOGS")
    log_sigs = set(facts.decky_log_signatures)

    if port_conflict and facts.plugin_loader_present:
        found.append(
            Diagnosis(
                title=t("diag.port.title"),
                summary=t("diag.port.summary"),
                recommendation=t("diag.port.rec"),
                related_checks=["DECKY-PORTS", "DECKY-FRONTEND"],
                confidence=Confidence.HIGH,
                fact_kind="fact",
                severity=Severity.HIGH,
            )
        )
    elif (
        backend_ok
        and cef_ok
        and steam_beta
        and "inject" not in log_sigs
        and (logs is None or logs.status in {Status.PASS, Status.WARNING, Status.SKIPPED})
    ):
        found.append(
            Diagnosis(
                title=t("diag.steam_beta.title"),
                summary=t("diag.steam_beta.summary"),
                recommendation=t("diag.steam_beta.rec"),
                related_checks=["DECKY-INSTALL", "DECKY-SERVICE", "DECKY-FRONTEND", "STEAM-CLIENT"],
                confidence=Confidence.MEDIUM,
                fact_kind="likely",
                severity=Severity.MEDIUM,
            )
        )

    if facts.autoflatpaks_installed and facts.autoflatpaks_remote_list_failed:
        remotes = ", ".join(facts.flatpak_failed_remotes)
        rec = (
            translate(locale, "diag.autoflatpaks.rec.named", remote=remotes)
            if remotes
            else t("diag.autoflatpaks.rec")
        )
        found.append(
            Diagnosis(
                title=t("diag.autoflatpaks.title"),
                summary=t("diag.autoflatpaks.summary"),
                recommendation=rec,
                related_checks=["AUTOFLATPAKS", "FP-BASIC", "FP-UPDATES"],
                confidence=Confidence.HIGH,
                fact_kind="fact",
                severity=Severity.MEDIUM,
            )
        )

    if facts.overlay_edited and facts.os_updater in {"error", "timeout"}:
        found.append(
            Diagnosis(
                title=t("diag.overlay.title"),
                summary=t("diag.overlay.summary"),
                recommendation=t("diag.overlay.rec"),
                related_checks=["SYS-OVERLAY", "SYS-OS-UPDATER"],
                confidence=Confidence.MEDIUM,
                fact_kind="likely",
                severity=Severity.MEDIUM,
            )
        )

    return found
