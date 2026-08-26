from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Facts:
    """Typed bag of observations shared across checks and the correlator.

    Optional fields stay None until a check sets them. Treat ``is False`` as
    distinct from ``None`` (unknown / not run).
    """

    os_release: dict[str, str] = field(default_factory=dict)
    atomupd_manifest: dict[str, Any] = field(default_factory=dict)
    atomupd_manifest_path: str | None = None
    os_version: str | None = None
    os_build: str | None = None
    os_variant: str | None = None
    os_id: str | None = None
    is_steamos: bool | None = None
    os_family: str | None = None
    os_channel: str | None = None
    pending_reboot: bool | None = None
    pending_reboot_build: str | None = None
    overlay_edited: list[str] = field(default_factory=list)
    os_updater: str | None = None
    disk: list[dict[str, Any]] = field(default_factory=list)
    disk_min_free: int | None = None
    storage_internal: dict[str, Any] | None = None
    storage_sd: dict[str, Any] | None = None
    steam_game_count: int | None = None
    steam_games_internal: int | None = None
    steam_games_sd: int | None = None
    ntp_synchronized: bool | None = None
    steam_version: str | None = None
    steam_channel: str | None = None
    decky_home: str | None = None
    decky_installed: bool | None = None
    plugin_loader_present: bool | None = None
    decky_version: str | None = None
    decky_channel: str | None = None
    decky_settings_file: str | None = None
    decky_unit_readable: bool | None = None
    decky_unit_is_429: bool = False
    decky_incomplete: bool = False
    plugin_loader_executable: bool | None = None
    decky_latest_stable: str | None = None
    decky_service_active: str | None = None
    decky_service_enabled: str | None = None
    decky_service_result: str | None = None
    decky_service_pid: int | None = None
    port_8080: list[str] = field(default_factory=list)
    port_1337: list[str] = field(default_factory=list)
    port_8080_conflict: bool = False
    port_8080_listening: bool | None = None
    port_1337_conflict: bool = False
    port_1337_missing: bool = False
    decky_log_hits: list[str] = field(default_factory=list)
    decky_log_text: str = ""
    decky_log_signatures: list[str] = field(default_factory=list)
    cef_enable_file: bool | None = None
    cef_json_ok: bool | None = None
    cef_excerpt: list[str] = field(default_factory=list)
    cef_forward_exposed: bool = False
    cef_forward_setting: bool | None = None
    cef_forward_owner: str | None = None
    plugins: list[dict[str, Any]] = field(default_factory=list)
    store_plugins: list[dict[str, str]] = field(default_factory=list)
    store_updates: list[str] = field(default_factory=list)
    remote_binary_log_hit: bool = False
    flatpak_available: bool | None = None
    flatpak_version: str | None = None
    flatpak_remotes_raw: str | None = None
    flatpak_remote_count: int | None = None
    flatpak_update_check: str | None = None
    flatpak_updates: list[str] = field(default_factory=list)
    flatpak_failed_remotes: list[str] = field(default_factory=list)
    flatpak_eol: list[str] = field(default_factory=list)
    autoflatpaks_installed: bool | None = None
    autoflatpaks_remote_list_failed: bool = False
    github_reachable: bool | None = None
    github_remaining: int | None = None
    github_limit: int | None = None
    github_reset: int | None = None
    store_ok: bool | None = None
    checks_timed_out: list[str] = field(default_factory=list)
    partial: bool = False

    def to_dict(self, *, include_logs: bool = False) -> dict[str, Any]:
        data = asdict(self)
        if not include_logs:
            data.pop("decky_log_text", None)
            data.pop("decky_log_hits", None)
        return data
