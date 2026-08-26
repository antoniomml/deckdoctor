from __future__ import annotations

from pathlib import Path

from deckdoctor.checks._util import version_is_newer
from deckdoctor.command import CommandResult
from deckdoctor.http import HttpResult
from deckdoctor.models import Status
from deckdoctor.runner import diagnose
from tests.conftest import (
    RATE_ZERO,
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
    assert inst.status == Status.INFO
    assert "not" in inst.finding.lower() or "does not" in inst.finding.lower()
    assert inst not in report.problems


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
    assert "PLUGIN-STORE-UPDATES" in skipped
    assert "FP-UPDATES" in skipped
    updater = next(r for r in report.results if r.check_id == "SYS-OS-UPDATER")
    assert updater.status == Status.PASS
    assert "SYS-OS-UPDATER" not in skipped
    auto = next(r for r in report.results if r.check_id == "AUTOFLATPAKS")
    assert auto.status == Status.SKIPPED
    assert "not installed" in auto.finding.lower() or "no está" in auto.finding.lower()


def test_full_root_does_not_fail_when_home_has_space(tmp_path: Path) -> None:
    import shutil

    from tests.conftest import plenty_disk, tiny_disk

    def mixed(path: Path) -> shutil._ntuple_diskusage:
        if str(path) in {"/", ""}:
            return tiny_disk(path)
        return plenty_disk(path)

    ctx = make_ctx(tmp_path, disk=mixed)
    report = diagnose(ctx)
    disk = next(r for r in report.results if r.check_id == "SYS-DISK")
    assert disk.status == Status.PASS


def test_journalctl_denied_is_skipped(tmp_path: Path) -> None:
    commands = healthy_commands()
    journal = (
        "journalctl",
        "-b0",
        "-u",
        "plugin_loader.service",
        "-n",
        "200",
        "--no-pager",
    )
    commands[journal] = CommandResult(journal, 1, "", "Permission denied\n")
    ctx = make_ctx(tmp_path, commands=commands)
    report = diagnose(ctx)
    logs = next(r for r in report.results if r.check_id == "DECKY-LOGS")
    assert logs.status == Status.SKIPPED


def test_json_facts_omit_raw_logs(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    report = diagnose(ctx)
    assert "decky_log_text" not in report.facts


def test_pending_reboot_marker(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    ctx.reboot_for_update_path.write_text("20260824.1\n", encoding="utf-8")
    report = diagnose(ctx)
    reboot = next(r for r in report.results if r.check_id == "SYS-OS-REBOOT")
    assert reboot.status == Status.WARNING
    assert "20260824.1" in reboot.finding
    assert ctx.facts.pending_reboot is True


def test_overlay_edited_atomupd(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    dest = ctx.overlay_root / "steamos-atomupd"
    dest.mkdir(parents=True)
    (dest / "client.conf").write_text("QueryUrl=https://example.invalid/updates\n", encoding="utf-8")
    report = diagnose(ctx)
    overlay = next(r for r in report.results if r.check_id == "SYS-OVERLAY")
    assert overlay.status == Status.WARNING
    assert "client.conf" in overlay.finding


def test_flatpak_eol_runtime_and_app(tmp_path: Path) -> None:
    commands = healthy_commands()
    runtime_key = ("flatpak", "list", "--runtime", "--columns=ref,application,origin")
    app_key = ("flatpak", "list", "--app", "--columns=ref,application,runtime,origin")
    meta_key = ("flatpak", "info", "--show-metadata", "org.freedesktop.Platform/x86_64/22.08")
    commands[runtime_key] = CommandResult(
        runtime_key,
        0,
        "org.freedesktop.Platform/x86_64/22.08\tFreedesktop Platform\tflathub\n",
        "",
    )
    commands[app_key] = CommandResult(
        app_key,
        0,
        "org.mozilla.firefox/x86_64/stable\tFirefox\torg.freedesktop.Platform/x86_64/22.08\tflathub\n",
        "",
    )
    commands[meta_key] = CommandResult(
        meta_key,
        0,
        "[Runtime]\nname=org.freedesktop.Platform\nEndOfLife=The Freedesktop SDK 22.08 runtime is no longer supported\n",
        "",
    )
    ctx = make_ctx(tmp_path, commands=commands)
    report = diagnose(ctx)
    eol = next(r for r in report.results if r.check_id == "FP-EOL")
    assert eol.status == Status.WARNING
    assert "end-of-life" in eol.finding.lower()
    assert any("Firefox" in line for line in eol.evidence)


def test_plugin_store_unique_update(tmp_path: Path) -> None:
    http = healthy_http()
    http.add(
        "GET",
        "https://plugins.deckbrew.xyz/plugins",
        HttpResult(
            "https://plugins.deckbrew.xyz/plugins",
            "GET",
            200,
            '[{"id": "example", "name": "Example Plugin", "version": "2.1.0"}]',
        ),
    )
    ctx = make_ctx(tmp_path, http=http)
    report = diagnose(ctx)
    store = next(r for r in report.results if r.check_id == "PLUGIN-STORE-UPDATES")
    assert store.status == Status.WARNING
    assert "2.1.0" in store.finding or "2.1.0" in " ".join(store.evidence)


def test_plugin_store_ambiguous_name_is_not_an_update(tmp_path: Path) -> None:
    http = healthy_http()
    http.add(
        "GET",
        "https://plugins.deckbrew.xyz/plugins",
        HttpResult(
            "https://plugins.deckbrew.xyz/plugins",
            "GET",
            200,
            '[{"id": "a", "name": "Example Plugin", "version": "9.0.0"},'
            ' {"id": "b", "name": "Example Plugin", "version": "9.0.1"}]',
        ),
    )
    ctx = make_ctx(tmp_path, http=http)
    report = diagnose(ctx)
    store = next(r for r in report.results if r.check_id == "PLUGIN-STORE-UPDATES")
    assert store.status == Status.INFO
    assert "uniquely" in store.finding.lower()


def test_bazzite_skips_steamos_checks_but_keeps_decky(tmp_path: Path) -> None:
    os_release = """\
NAME="Bazzite"
PRETTY_NAME="Bazzite"
ID=bazzite
VERSION_ID=42
VARIANT_ID=bazzite-deck
"""
    ctx = make_ctx(tmp_path, os_release=os_release)
    report = diagnose(ctx)
    osver = next(r for r in report.results if r.check_id == "SYS-OS-VERSION")
    channel = next(r for r in report.results if r.check_id == "SYS-OS-CHANNEL")
    updater = next(r for r in report.results if r.check_id == "SYS-OS-UPDATER")
    reboot = next(r for r in report.results if r.check_id == "SYS-OS-REBOOT")
    overlay = next(r for r in report.results if r.check_id == "SYS-OVERLAY")
    decky = next(r for r in report.results if r.check_id == "DECKY-INSTALL")
    assert osver.status == Status.INFO
    assert "Bazzite" in osver.finding
    assert channel.status == Status.SKIPPED
    assert updater.status == Status.SKIPPED
    assert reboot.status == Status.SKIPPED
    assert overlay.status == Status.SKIPPED
    assert decky.status == Status.PASS
    assert ctx.facts.os_family == "bazzite"


def test_no_update_available_is_not_an_update(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    report = diagnose(ctx)
    upd = next(r for r in report.results if r.check_id == "SYS-OS-UPDATER")
    assert upd.status == Status.PASS
    assert "available" not in upd.finding.lower() or "no update" in upd.finding.lower()


def test_unknown_os_skips_steamos_reboot(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    ctx.os_release_path = tmp_path / "missing-os-release"
    report = diagnose(ctx)
    osver = next(r for r in report.results if r.check_id == "SYS-OS-VERSION")
    reboot = next(r for r in report.results if r.check_id == "SYS-OS-REBOOT")
    assert osver.status == Status.UNKNOWN
    assert reboot.status == Status.SKIPPED
    assert ctx.facts.is_steamos is False


def test_version_is_newer_is_conservative() -> None:
    assert version_is_newer("2.1.0", "2.0.0") is True
    assert version_is_newer("2.0.0", "2.0.0") is False
    assert version_is_newer("v3.2.6", "3.2.5") is True
    assert version_is_newer("1.0", "unknown") is None
