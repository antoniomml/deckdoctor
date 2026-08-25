from __future__ import annotations

import pytest

from deckdoctor.command import CommandRunner, FakeCommandRunner, CommandResult


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


def test_fake_runner_records_calls() -> None:
    fake = FakeCommandRunner(
        {
            ("echo", "ok"): CommandResult(("echo", "ok"), 0, "ok\n", ""),
        }
    )
    res = fake.run(["echo", "ok"])
    assert res.ok
    assert fake.calls == [("echo", "ok")]
