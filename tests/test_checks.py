from __future__ import annotations

from pathlib import Path

from deckdoctor.command import CommandResult
from deckdoctor.correlator import correlate
from deckdoctor.http import FakeHttpClient, HttpResult
from deckdoctor.models import Status
from deckdoctor.runner import diagnose
from tests.conftest import (
    RATE_ZERO,
    cmd,
    healthy_commands,
    healthy_http,
    make_ctx,
    make_home,
    tiny_disk,
    write_plugin,
)


def test_healthy(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    report = diagnose(ctx)
    fails = [r for r in report.results if r.status == Status.FAIL]
    assert fails == [], [r.check_id + ": " + r.finding for r in fails]
    ids = {r.check_id for r in report.results}
    assert "DECKY-INSTALL" in ids
    assert len(report.results) >= 16


def test_decky_missing(tmp_path: Path) -> None:
    home = make_home(tmp_path, with_decky=False)
    ctx = make_ctx(tmp_path, home=home)
    report = diagnose(ctx)
    inst = next(r for r in report.results if r.check_id == "DECKY-INSTALL")
    assert inst.status == Status.FAIL
    assert "not" in inst.finding.lower() or "does not" in inst.finding.lower()


def test_decky_service_failed(tmp_path: Path) -> None:
    commands = healthy_commands()
    commands[("systemctl", "is-active", "plugin_loader.service")] = CommandResult(
        ("systemctl", "is-active", "plugin_loader.service"), 3, "failed\n", ""
    )
    show_key = next(k for k in commands if k[:3] == ("systemctl", "show", "plugin_loader.service"))
    commands[show_key] = CommandResult(
        show_key,
        0,
        "LoadState=loaded\nActiveState=failed\nResult=exit-code\nExecMainStatus=203\nNRestarts=4\n",
        "",
    )
    ctx = make_ctx(tmp_path, commands=commands)
    report = diagnose(ctx)
    svc = next(r for r in report.results if r.check_id == "DECKY-SERVICE")
    assert svc.status == Status.FAIL


def test_pluginloader_missing_with_rate_limit(tmp_path: Path) -> None:
    home = make_home(tmp_path, loader=False)
    http = healthy_http()
    http.add(
        "GET",
        "https://api.github.com/rate_limit",
        HttpResult("https://api.github.com/rate_limit", "GET", 200, RATE_ZERO),
    )
    ctx = make_ctx(tmp_path, home=home, http=http)
    report = diagnose(ctx)
    inst = next(r for r in report.results if r.check_id == "DECKY-INSTALL")
    gh = next(r for r in report.results if r.check_id == "NET-GITHUB")
    assert inst.status == Status.FAIL
    assert "PluginLoader" in inst.finding
    assert gh.status == Status.FAIL
    titles = [d.title for d in report.diagnoses]
    assert any("rate limit" in t.lower() or "Incomplete" in t for t in titles)


def test_unit_file_429(tmp_path: Path) -> None:
    ctx = make_ctx(
        tmp_path,
        unit_text="429: Too Many Requests\nFor more on scraping GitHub\n",
    )
    report = diagnose(ctx)
    inst = next(r for r in report.results if r.check_id == "DECKY-INSTALL")
    assert inst.status == Status.FAIL
    assert any("429" in d.title or "429" in d.summary for d in report.diagnoses)


def test_frontend_port_conflict(tmp_path: Path) -> None:
    commands = healthy_commands()
    commands[("ss", "-ltnp")] = CommandResult(
        ("ss", "-ltnp"),
        0,
        'LISTEN 0 10 127.0.0.1:8080 0.0.0.0:* users:(("syncthing",pid=9,fd=8))\n'
        'LISTEN 0 10 127.0.0.1:1337 0.0.0.0:* users:(("PluginLoader",pid=11,fd=3))\n',
        "",
    )
    http = healthy_http()
    http.add(
        "GET",
        "http://127.0.0.1:8080/json",
        HttpResult("http://127.0.0.1:8080/json", "GET", 404, "404 page not found\n"),
    )
    ctx = make_ctx(tmp_path, commands=commands, http=http)
    report = diagnose(ctx)
    ports = next(r for r in report.results if r.check_id == "DECKY-PORTS")
    front = next(r for r in report.results if r.check_id == "DECKY-FRONTEND")
    assert ports.status == Status.FAIL
    assert front.status == Status.FAIL
    assert any("8080" in d.title for d in report.diagnoses)


def test_frontend_missing_steam_beta(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    (home / ".steam" / "steam" / "package" / "beta").write_text("steampipe_stable_steamdeck_beta\n", encoding="utf-8")
    ctx = make_ctx(tmp_path, home=home)
    report = diagnose(ctx)
    steam = next(r for r in report.results if r.check_id == "STEAM-CLIENT")
    assert steam.extra.get("channel") == "beta" or "beta" in steam.finding.lower()
    assert any("Steam" in d.title or "frontend" in d.title.lower() for d in report.diagnoses)


def test_github_rate_limited(tmp_path: Path) -> None:
    http = healthy_http()
    http.add(
        "GET",
        "https://api.github.com/rate_limit",
        HttpResult("https://api.github.com/rate_limit", "GET", 200, RATE_ZERO),
    )
    ctx = make_ctx(tmp_path, http=http)
    report = diagnose(ctx)
    gh = next(r for r in report.results if r.check_id == "NET-GITHUB")
    assert gh.status == Status.FAIL
    assert "rate limit" in gh.finding.lower()


def test_flatpak_broken_remote(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    write_plugin(home, "decky-autoflatpaks", "AutoFlatpaks", "1.6.8")
    commands = healthy_commands()
    commands[("flatpak", "remote-ls", "--updates", "--columns=application,branch,origin")] = CommandResult(
        ("flatpak", "remote-ls", "--updates", "--columns=application,branch,origin"),
        1,
        "",
        "error: Unable to load summary from remote kdeapps: refs that no longer exist\n",
    )
    commands[("flatpak", "remote-ls", "--columns=ref,origin", "-a")] = CommandResult(
        ("flatpak", "remote-ls", "--columns=ref,origin", "-a"),
        1,
        "",
        "error: Unable to load summary from remote kdeapps: Server returned status 404\n",
    )
    ctx = make_ctx(tmp_path, home=home, commands=commands)
    report = diagnose(ctx)
    updates = next(r for r in report.results if r.check_id == "FP-UPDATES")
    auto = next(r for r in report.results if r.check_id == "AUTOFLATPAKS")
    assert updates.status == Status.FAIL
    assert "0 update" not in updates.finding.lower()
    assert auto.status == Status.FAIL
    assert any("AutoFlatpaks" in d.title for d in report.diagnoses)


def test_plugin_remote_binary_failure(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    write_plugin(
        home,
        "Decky Framegen",
        "Decky FrameGen",
        "1.0.0",
        remote=[{"name": "assets.zip", "url": "https://example.invalid/a.zip", "sha256hash": "abc"}],
    )
    logs = home / "homebrew" / "logs" / "Decky Framegen"
    logs.mkdir(parents=True)
    (logs / "plugin.log").write_text("Failed Downloading Remote Binaries\n", encoding="utf-8")
    ctx = make_ctx(tmp_path, home=home)
    report = diagnose(ctx)
    remote = next(r for r in report.results if r.check_id == "PLUGIN-REMOTE-BIN")
    assert remote.status == Status.FAIL
    assert "FrameGen" in remote.finding or "assets.zip" in remote.finding or "Remote" in remote.finding


def test_low_disk_space(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, disk=tiny_disk)
    report = diagnose(ctx)
    disk = next(r for r in report.results if r.check_id == "SYS-DISK")
    assert disk.status == Status.FAIL
    assert "free" in disk.finding.lower()


def test_updater_timeout_is_not_up_to_date(tmp_path: Path) -> None:
    commands = healthy_commands()
    commands[("atomupd-manager", "get-update-status")] = CommandResult(
        ("atomupd-manager", "get-update-status"),
        124,
        "",
        "timed out",
        timed_out=True,
        error="timeout",
    )
    ctx = make_ctx(tmp_path, commands=commands)
    report = diagnose(ctx)
    upd = next(r for r in report.results if r.check_id == "SYS-OS-UPDATER")
    assert upd.status == Status.FAIL
    assert "up to date" not in upd.finding.lower()


def test_no_network_skips(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, network=False)
    report = diagnose(ctx)
    skipped = {r.check_id: r for r in report.results if r.status == Status.SKIPPED}
    assert "NET-GITHUB" in skipped
    assert "NET-STORE" in skipped
