from __future__ import annotations

from deckdoctor.models import CheckResult, Confidence, Diagnosis, Severity, Status


def _by_id(results: list[CheckResult]) -> dict[str, CheckResult]:
    return {r.check_id: r for r in results}


def correlate(results: list[CheckResult], facts: dict) -> list[Diagnosis]:
    """Explicit rules only. Prefer UNKNOWN over storytelling."""
    found: list[Diagnosis] = []
    by = _by_id(results)

    incomplete = bool(facts.get("decky_incomplete")) or (
        facts.get("decky_installed") and facts.get("plugin_loader_present") is False
    )
    remaining = facts.get("github_remaining")
    unit_429 = bool(facts.get("decky_unit_is_429"))

    if incomplete and remaining == 0:
        found.append(
            Diagnosis(
                title="Incomplete Decky install and GitHub rate limit",
                summary=(
                    "FACT: PluginLoader is missing. FACT: GitHub API remaining is 0. "
                    "LIKELY CAUSE: the installer could not download PluginLoader because the unauthenticated "
                    "GitHub API quota was exhausted (common on CGNAT)."
                ),
                recommendation=(
                    "Wait for the quota reset or switch networks, then reinstall with the official Decky installer. "
                    "Do not delete ~/homebrew/plugins unless you intend to. DeckDoctor will not reinstall Decky."
                ),
                related_checks=["DECKY-INSTALL", "NET-GITHUB"],
                confidence=Confidence.HIGH,
                fact_kind="likely",
                severity=Severity.HIGH,
            )
        )
    elif unit_429:
        found.append(
            Diagnosis(
                title="systemd unit replaced by GitHub 429 page",
                summary=(
                    "FACT: plugin_loader.service contains GitHub's rate-limit HTML. "
                    "The installer saved an API error as a unit file, so Decky cannot start."
                ),
                recommendation="Reinstall Decky after GitHub API quota recovers. Do not hand-edit a 429 page into a valid unit unless you know systemd.",
                related_checks=["DECKY-INSTALL", "DECKY-SERVICE"],
                confidence=Confidence.HIGH,
                fact_kind="fact",
                severity=Severity.HIGH,
            )
        )
    elif incomplete:
        found.append(
            Diagnosis(
                title="Incomplete Decky installation",
                summary="FACT: the homebrew tree exists but PluginLoader was never downloaded.",
                recommendation="Re-run the official installer. If it failed before, check NET-GITHUB first.",
                related_checks=["DECKY-INSTALL"],
                confidence=Confidence.HIGH,
                fact_kind="fact",
                severity=Severity.HIGH,
            )
        )

    backend_ok = facts.get("plugin_loader_present") and facts.get("decky_service_active") == "active"
    cef_ok = bool(facts.get("cef_json_ok"))
    port_conflict = bool(facts.get("port_8080_conflict"))
    steam_beta = facts.get("steam_channel") == "beta"
    logs = by.get("DECKY-LOGS")
    log_sigs = set(facts.get("decky_log_signatures") or [])

    if port_conflict and facts.get("plugin_loader_present"):
        found.append(
            Diagnosis(
                title="Decky cannot inject: port 8080 conflict",
                summary=(
                    "FACT: PluginLoader is present but port 8080 is not Steam's CEF debugger. "
                    "Decky injects through localhost:8080; another process is in the way."
                ),
                recommendation="Move the conflicting app (Syncthing should use 8384). DeckDoctor will not kill processes.",
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
                title="Backend healthy; frontend may be a Steam client issue",
                summary=(
                    "FACT: PluginLoader is present and plugin_loader.service is active. "
                    "FACT: localhost:8080/json looks like Steam CEF. "
                    "FACT: Steam client channel appears to be Beta. "
                    "LIKELY CAUSE (medium): the Steam client/frontend, not a broken Decky install. "
                    "DeckDoctor cannot see whether the QAM tab is actually missing."
                ),
                recommendation="Contrast with Steam Deck Stable, update Decky, and if React error #130 persists, disable plugins from Desktop Mode.",
                related_checks=["DECKY-INSTALL", "DECKY-SERVICE", "DECKY-FRONTEND", "STEAM-CLIENT"],
                confidence=Confidence.MEDIUM,
                fact_kind="likely",
                severity=Severity.MEDIUM,
            )
        )

    if facts.get("autoflatpaks_installed") and facts.get("autoflatpaks_remote_list_failed"):
        found.append(
            Diagnosis(
                title="AutoFlatpaks is fine; Flatpak remote listing is not",
                summary=(
                    "FACT: AutoFlatpaks is installed. FACT: `flatpak` works. "
                    "FACT: `flatpak remote-ls` failed. "
                    "The plugin cannot display a remote package list because Flatpak cannot produce one."
                ),
                recommendation="Fix or remove the failing Flatpak remote yourself. DeckDoctor will not delete remotes.",
                related_checks=["AUTOFLATPAKS", "FP-BASIC", "FP-UPDATES"],
                confidence=Confidence.HIGH,
                fact_kind="fact",
                severity=Severity.MEDIUM,
            )
        )

    return found
