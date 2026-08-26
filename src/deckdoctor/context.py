from __future__ import annotations

import json
import os
import pwd
import shutil
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from deckdoctor.command import CommandResult, CommandRunner
from deckdoctor.facts import Facts
from deckdoctor.http import HttpClient
from deckdoctor.i18n import Locale, detect_locale, translate

DiskUsageFn = Callable[[Path], shutil._ntuple_diskusage]


def default_home() -> Path:
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            return Path(pwd.getpwnam(sudo_user).pw_dir)
        except KeyError:
            pass
    env_home = os.environ.get("HOME")
    if env_home:
        return Path(env_home)
    return Path.home()


def default_user(home: Path) -> str:
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        return sudo_user
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return home.name or "user"


def parse_os_release(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        data[key] = value
    return data


@dataclass
class DiagnosticContext:
    home: Path
    runner: CommandRunner
    http: HttpClient
    now: datetime = field(default_factory=lambda: datetime.now(UTC))
    network_enabled: bool = True
    os_release_path: Path = Path("/etc/os-release")
    atomupd_manifest_paths: tuple[Path, ...] = (
        Path("/etc/steamos-atomupd/manifest.json"),
        Path("/lib/steamos-atomupd/manifest.json"),
        Path("/usr/lib/steamos-atomupd/manifest.json"),
    )
    systemd_unit_path: Path = Path("/etc/systemd/system/plugin_loader.service")
    atomupd_client_conf: Path = Path("/etc/steamos-atomupd/client.conf")
    overlay_root: Path = Path("/var/lib/overlays/etc/upper")
    reboot_for_update_path: Path = Path("/run/steamos-atomupd/reboot_for_update")
    disk_usage: DiskUsageFn | None = None
    hostname: str = field(default_factory=lambda: os.uname().nodename if hasattr(os, "uname") else "unknown")
    user: str = ""
    facts: Facts = field(default_factory=Facts)
    locale: Locale = "en"
    ascii_mode: bool = False
    only_ids: frozenset[str] | None = None
    deadline: float | None = None
    _cmd_cache: dict[tuple[str, ...], CommandResult] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.user:
            self.user = default_user(self.home)
        if self.locale not in {"en", "es"}:
            self.locale = detect_locale(str(self.locale))

    def tr(self, key: str, **kwargs: object) -> str:
        return translate(self.locale, key, **kwargs)

    @property
    def decky_home(self) -> Path:
        return self.home / "homebrew"

    @property
    def plugin_loader(self) -> Path:
        return self.decky_home / "services" / "PluginLoader"

    @property
    def loader_version_file(self) -> Path:
        return self.decky_home / "services" / ".loader.version"

    @property
    def plugins_dir(self) -> Path:
        return self.decky_home / "plugins"

    @property
    def settings_dir(self) -> Path:
        return self.decky_home / "settings"

    @property
    def logs_dir(self) -> Path:
        return self.decky_home / "logs"

    @property
    def steam_root(self) -> Path:
        # ~/.steam/steam is the usual symlink on SteamOS.
        direct = self.home / ".steam" / "steam"
        alt = self.home / ".local" / "share" / "Steam"
        if direct.exists():
            return direct
        if alt.exists():
            return alt
        return direct

    def read_text(self, path: Path, max_bytes: int = 1_000_000) -> str | None:
        try:
            data = path.read_bytes()[:max_bytes]
            return data.decode("utf-8", errors="replace")
        except OSError:
            return None

    def exists(self, path: Path) -> bool:
        try:
            return path.exists()
        except OSError:
            return False

    def remaining_timeout(self, requested: float) -> float:
        if self.deadline is None:
            return requested
        left = self.deadline - time.monotonic()
        if left <= 0:
            return 0.0
        return min(requested, left)

    def timed_out(self) -> bool:
        return self.deadline is not None and time.monotonic() >= self.deadline

    def run(self, argv: list[str], *, timeout: float = 15.0, cache: bool = True) -> CommandResult:
        key = tuple(argv)
        if cache and key in self._cmd_cache:
            return self._cmd_cache[key]
        capped = self.remaining_timeout(timeout)
        result = self.runner.run(argv, timeout=capped)
        if cache:
            self._cmd_cache[key] = result
        return result

    def probe_flatpak_listing(self) -> CommandResult:
        """Shared ``flatpak remote-ls -a`` used by FP-UPDATES and AUTOFLATPAKS."""
        argv = ["flatpak", "remote-ls", "--columns=ref,origin", "-a"]
        return self.run(argv, timeout=45.0)

    def measure_disk(self, path: Path) -> shutil._ntuple_diskusage | None:
        fn = self.disk_usage or shutil.disk_usage
        try:
            return fn(path)
        except OSError:
            return None

    def load_os_release(self) -> dict[str, str]:
        text = self.read_text(self.os_release_path)
        if text is None:
            return {}
        parsed = parse_os_release(text)
        self.facts.os_release = parsed
        return parsed

    def load_atomupd_manifest(self) -> dict[str, Any]:
        for path in self.atomupd_manifest_paths:
            text = self.read_text(path)
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                self.facts.atomupd_manifest = data
                self.facts.atomupd_manifest_path = str(path)
                return data
        return {}


def parse_only_ids(raw: str | Sequence[str] | None) -> frozenset[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        parts = raw.split(",")
    else:
        parts = list(raw)
    ids = frozenset(p.strip().upper() for p in parts if p.strip())
    return ids or None
