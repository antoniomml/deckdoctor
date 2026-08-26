from __future__ import annotations

from pathlib import Path

from deckdoctor.command import CommandResult
from deckdoctor.fixes import FakeFixExecutor, apply_plans, collect_plans
from deckdoctor.runner import diagnose
from tests.conftest import healthy_commands, make_ctx, make_home


def test_healthy_has_no_automatic_fixes(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    report = diagnose(ctx)
    assert collect_plans(ctx, report) == []


def test_pluginloader_exec_plan_and_apply(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    loader = home / "homebrew" / "services" / "PluginLoader"
    loader.chmod(0o644)
    ctx = make_ctx(tmp_path, home=home)
    report = diagnose(ctx)
    plans = collect_plans(ctx, report)
    assert any(p.id == "pluginloader-exec" for p in plans)
    executor = FakeFixExecutor()
    results = apply_plans(ctx, [p for p in plans if p.id == "pluginloader-exec"], executor)
    assert results[0].ok
    assert loader.stat().st_mode & 0o111


def test_cef_debug_creates_file(tmp_path: Path) -> None:
    home = make_home(tmp_path, cef=False)
    ctx = make_ctx(tmp_path, home=home)
    report = diagnose(ctx)
    plans = collect_plans(ctx, report)
    assert any(p.id == "cef-debug" for p in plans)
    executor = FakeFixExecutor()
    results = apply_plans(ctx, [p for p in plans if p.id == "cef-debug"], executor)
    assert results[0].ok
    assert (home / ".steam" / "steam" / ".cef-enable-remote-debugging").is_file()


def test_decky_service_fix_when_inactive(tmp_path: Path) -> None:
    commands = healthy_commands()
    commands[("systemctl", "is-active", "plugin_loader.service")] = CommandResult(
        ("systemctl", "is-active", "plugin_loader.service"), 3, "inactive\n", ""
    )
    ctx = make_ctx(tmp_path, commands=commands)
    report = diagnose(ctx)
    plans = collect_plans(ctx, report)
    assert any(p.id == "decky-service" for p in plans)
    executor = FakeFixExecutor()
    results = apply_plans(ctx, [p for p in plans if p.id == "decky-service"], executor)
    assert results[0].ok
    assert ("systemctl", "enable", "--now", "plugin_loader.service") in executor.calls


def test_flatpak_update_plan(tmp_path: Path) -> None:
    commands = healthy_commands()
    key = ("flatpak", "remote-ls", "--updates", "--columns=application,branch,origin")
    commands[key] = CommandResult(key, 0, "org.mozilla.firefox\tstable\tflathub\n", "")
    ctx = make_ctx(tmp_path, commands=commands)
    report = diagnose(ctx)
    plans = collect_plans(ctx, report)
    assert any(p.id == "flatpak-update" for p in plans)


def test_flatpak_update_timeout_is_not_success(tmp_path: Path) -> None:
    from deckdoctor.fixes import FakeFixExecutor, flatpak_update

    ctx = make_ctx(tmp_path)
    executor = FakeFixExecutor()
    executor.mapping[("flatpak", "update", "-y")] = CommandResult(
        ("flatpak", "update", "-y"),
        124,
        "",
        "timed out",
        timed_out=True,
        error="timeout",
    )
    executor.mapping[("flatpak", "--user", "update", "-y")] = CommandResult(
        ("flatpak", "--user", "update", "-y"),
        0,
        "",
        "",
    )
    result = flatpak_update.apply(ctx, executor)
    assert not result.ok
    assert "timed out" in result.finding.lower()


def test_missing_decky_has_no_decky_fixes(tmp_path: Path) -> None:
    home = make_home(tmp_path, with_decky=False)
    ctx = make_ctx(tmp_path, home=home)
    report = diagnose(ctx)
    ids = {p.id for p in collect_plans(ctx, report)}
    assert "pluginloader-exec" not in ids
    assert "decky-service" not in ids
    assert "cef-debug" not in ids
