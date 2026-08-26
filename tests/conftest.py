from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from deckdoctor.command import CommandResult, FakeCommandRunner
from deckdoctor.context import DiagnosticContext
from deckdoctor.http import FakeHttpClient, HttpResult

OS_RELEASE = """\
NAME="SteamOS"
PRETTY_NAME="SteamOS"
ID=steamos
VERSION_ID=3.8.14
BUILD_ID=20260624.1
VARIANT_ID=steamdeck
"""

CEF_JSON = json.dumps(
    [
        {
            "title": "SharedJSContext",
            "url": "https://steamloopback.host/index.html",
            "webSocketDebuggerUrl": "ws://127.0.0.1:8080/devtools/page/1",
        }
    ]
)

STORE_JSON = json.dumps([{"id": "example", "name": "Example Plugin", "version": "2.0.0"}])

RATE_OK = json.dumps({"resources": {"core": {"limit": 60, "remaining": 53, "reset": 2000000000}}})
RATE_ZERO = json.dumps({"resources": {"core": {"limit": 60, "remaining": 0, "reset": 2000000000}}})


def cmd(argv: list[str], stdout: str = "", stderr: str = "", exit_code: int = 0, **kwargs) -> tuple[tuple[str, ...], CommandResult]:
    return tuple(argv), CommandResult(argv=tuple(argv), exit_code=exit_code, stdout=stdout, stderr=stderr, **kwargs)


def plenty_disk(_path: Path) -> shutil._ntuple_diskusage:
    return shutil._ntuple_diskusage(100 * 1024**3, 10 * 1024**3, 90 * 1024**3)


def tiny_disk(_path: Path) -> shutil._ntuple_diskusage:
    return shutil._ntuple_diskusage(64 * 1024**3, 64 * 1024**3 - 120 * 1024**2, 120 * 1024**2)


def write_plugin(root: Path, dirname: str, name: str, version: str = "1.0.0", remote: list[Any] | None = None) -> Path:
    d = root / "homebrew" / "plugins" / dirname
    d.mkdir(parents=True)
    (d / "plugin.json").write_text(json.dumps({"name": name, "author": "test"}), encoding="utf-8")
    pkg: dict = {"name": dirname, "version": version}
    if remote is not None:
        pkg["remote_binary"] = remote
    (d / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (d / "main.py").write_text("# plugin\n", encoding="utf-8")
    return d


def healthy_commands() -> dict[tuple[str, ...], CommandResult]:
    ss = """\
State Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
LISTEN 0 10 127.0.0.1:8080 0.0.0.0:* users:(("steamwebhelper",pid=10,fd=8))
LISTEN 0 10 127.0.0.1:1337 0.0.0.0:* users:(("PluginLoader",pid=11,fd=3))
"""
    mapping = dict(
        [
            cmd(["steamos-select-branch", "-c"], "stable\n"),
            cmd(["atomupd-manager", "get-update-status"], "No update available\n"),
            cmd(["timedatectl", "show"], "NTP=yes\nNTPSynchronized=yes\nNTPEnabled=yes\n"),
            cmd(["systemctl", "is-enabled", "plugin_loader.service"], "enabled\n"),
            cmd(["systemctl", "is-active", "plugin_loader.service"], "active\n"),
            cmd(
                [
                    "systemctl",
                    "show",
                    "plugin_loader.service",
                    "-p",
                    "LoadState,ActiveState,SubState,Result,ExecMainStatus,NRestarts,UnitFileState,InactiveExitTimestamp,ExecMainCode",
                ],
                "LoadState=loaded\nActiveState=active\nSubState=running\nResult=success\nExecMainStatus=0\nNRestarts=0\n",
            ),
            cmd(["ss", "-ltnp"], ss),
            cmd(["journalctl", "-b0", "-u", "plugin_loader.service", "-n", "200", "--no-pager"], "Jan 01 PluginLoader[1]: [loader][INFO]: Loaded example\n"),
            cmd(["flatpak", "--version"], "Flatpak 1.15.6\n"),
            cmd(["flatpak", "remotes", "--columns=name,options,url"], "flathub\tsystem\thttps://dl.flathub.org/repo/\n"),
            cmd(["flatpak", "remote-ls", "--updates", "--columns=application,branch,origin"], ""),
            cmd(["flatpak", "remote-ls", "--columns=ref,origin", "-a"], "app/org.mozilla.firefox/x86_64/stable\tflathub\n"),
            cmd(["flatpak", "list", "--runtime", "--columns=ref,application,origin"], ""),
            cmd(["flatpak", "list", "--app", "--columns=ref,application,runtime,origin"], ""),
        ]
    )
    return mapping


def healthy_http() -> FakeHttpClient:
    http = FakeHttpClient()
    http.add("GET", "http://127.0.0.1:8080/json", HttpResult("http://127.0.0.1:8080/json", "GET", 200, CEF_JSON))
    http.add("HEAD", "https://github.com/", HttpResult("https://github.com/", "HEAD", 200))
    http.add("GET", "https://api.github.com/rate_limit", HttpResult("https://api.github.com/rate_limit", "GET", 200, RATE_OK))
    http.add(
        "GET",
        "https://plugins.deckbrew.xyz/plugins",
        HttpResult("https://plugins.deckbrew.xyz/plugins", "GET", 200, STORE_JSON),
    )
    http.add(
        "HEAD",
        "https://github.com/SteamDeckHomebrew/decky-loader/releases/latest",
        HttpResult(
            "https://github.com/SteamDeckHomebrew/decky-loader/releases/latest",
            "HEAD",
            200,
            final_url="https://github.com/SteamDeckHomebrew/decky-loader/releases/tag/v3.2.6",
        ),
    )
    return http


def make_home(tmp: Path, *, with_decky: bool = True, loader: bool = True, cef: bool = True) -> Path:
    home = tmp / "deck"
    home.mkdir()
    (home / ".steam" / "steam" / "logs").mkdir(parents=True)
    (home / ".steam" / "steam" / "package").mkdir(parents=True)
    (home / ".steam" / "steam" / "config").mkdir(parents=True)
    (home / ".steam" / "steam" / "package" / "steam_client_ubuntu12.installed").write_text(
        '"ubuntu12" { "version" "1780000000" }\n', encoding="utf-8"
    )
    if cef:
        (home / ".steam" / "steam" / ".cef-enable-remote-debugging").write_text("", encoding="utf-8")
    if with_decky:
        (home / "homebrew" / "services").mkdir(parents=True)
        (home / "homebrew" / "plugins").mkdir(parents=True)
        (home / "homebrew" / "settings").mkdir(parents=True)
        (home / "homebrew" / "logs").mkdir(parents=True)
        (home / "homebrew" / "services" / ".loader.version").write_text("v3.2.6\n", encoding="utf-8")
        (home / "homebrew" / "settings" / "loader.json").write_text('{"branch": 0}\n', encoding="utf-8")
        if loader:
            pl = home / "homebrew" / "services" / "PluginLoader"
            pl.write_bytes(b"#!/bin/sh\n")
            pl.chmod(0o755)
        write_plugin(home, "Example", "Example Plugin", "2.0.0")
    return home


def make_ctx(
    tmp: Path,
    *,
    home: Path | None = None,
    commands: dict[tuple[str, ...], CommandResult] | None = None,
    http: FakeHttpClient | None = None,
    os_release: str = OS_RELEASE,
    disk: Callable[[Path], shutil._ntuple_diskusage] = plenty_disk,
    unit_text: str | None = "[Service]\nExecStart=/home/deck/homebrew/services/PluginLoader\n",
    network: bool = True,
    locale: str = "en",
    only_ids: frozenset[str] | None = None,
    deadline: float | None = None,
    ascii_mode: bool = False,
) -> DiagnosticContext:
    home = home or make_home(tmp)
    os_path = tmp / "os-release"
    os_path.write_text(os_release, encoding="utf-8")
    unit_path = tmp / "plugin_loader.service"
    if unit_text is not None:
        unit_path.write_text(unit_text, encoding="utf-8")
    overlay_root = tmp / "overlay-etc-upper"
    reboot_path = tmp / "reboot_for_update"
    runner = FakeCommandRunner(commands if commands is not None else healthy_commands())
    ctx = DiagnosticContext(
        home=home,
        runner=runner,
        http=http or healthy_http(),
        now=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        network_enabled=network,
        os_release_path=os_path,
        systemd_unit_path=unit_path,
        overlay_root=overlay_root,
        reboot_for_update_path=reboot_path,
        disk_usage=disk,
        hostname="steamdeck",
        user="deck",
        locale=locale,  # type: ignore[arg-type]
        only_ids=only_ids,
        deadline=deadline,
        ascii_mode=ascii_mode,
    )
    return ctx


@pytest.fixture
def tmp_home(tmp_path: Path) -> Path:
    return make_home(tmp_path)
