from __future__ import annotations

import pytest

from deckdoctor.command import CommandResult, CommandRunner, FakeCommandRunner


def test_command_runner_refuses_chmod() -> None:
    runner = CommandRunner()
    with pytest.raises(PermissionError):
        runner.run(["chmod", "777", "/tmp"])


def test_command_runner_refuses_systemctl_restart() -> None:
    runner = FakeCommandRunner()
    with pytest.raises(PermissionError):
        runner.run(["systemctl", "restart", "plugin_loader.service"])


def test_command_runner_refuses_flatpak_update() -> None:
    runner = FakeCommandRunner()
    with pytest.raises(PermissionError):
        runner.run(["flatpak", "update"])


def test_command_runner_refuses_steamos_update_apply() -> None:
    runner = FakeCommandRunner()
    with pytest.raises(PermissionError):
        runner.run(["steamos-update"])


def test_command_runner_refuses_systemctl_user_start() -> None:
    runner = FakeCommandRunner()
    with pytest.raises(PermissionError):
        runner.run(["systemctl", "--user", "start", "plugin_loader.service"])


def test_command_runner_refuses_flatpak_user_update() -> None:
    runner = FakeCommandRunner()
    with pytest.raises(PermissionError):
        runner.run(["flatpak", "--user", "update"])


def test_command_runner_allows_flatpak_repair_dry_run() -> None:
    runner = FakeCommandRunner(
        {
            ("flatpak", "repair", "--dry-run"): CommandResult(
                ("flatpak", "repair", "--dry-run"), 0, "ok\n", ""
            )
        }
    )
    assert runner.run(["flatpak", "repair", "--dry-run"]).ok


def test_zero_timeout_does_not_spawn() -> None:
    runner = CommandRunner()
    res = runner.run(["true"], timeout=0)
    assert res.timed_out
    assert res.error == "timeout"


def test_fake_runner_records_calls() -> None:
    fake = FakeCommandRunner(
        {
            ("echo", "ok"): CommandResult(("echo", "ok"), 0, "ok\n", ""),
        }
    )
    res = fake.run(["echo", "ok"])
    assert res.ok
    assert fake.calls == [("echo", "ok")]
