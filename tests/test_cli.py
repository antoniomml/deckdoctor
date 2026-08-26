from __future__ import annotations

import sys
import time
from io import StringIO
from pathlib import Path

import pytest

from deckdoctor.cli import build_parser, main
from deckdoctor.command import CommandResult
from deckdoctor.models import Status
from deckdoctor.renderer import render_cli
from deckdoctor.runner import diagnose
from tests.conftest import healthy_commands, make_ctx, make_home


def test_parser_defaults() -> None:
    args = build_parser("en").parse_args([])
    assert args.command == "diagnose"
    assert args.json is False
    assert args.ascii is False
    assert args.only is None
    assert args.timeout == 60.0
    assert args.verbose is False
    assert args.yes is False


def test_help_exits_zero() -> None:
    try:
        build_parser("en").parse_args(["--help"])
    except SystemExit as exc:
        assert exc.code == 0


def test_ascii_marks(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, ascii_mode=True, verbose=True)
    report = diagnose(ctx)
    text = render_cli(report)
    assert "✅" not in text
    assert "❌" not in text
    assert "🩺" not in text
    assert "OK" in text


def test_compact_uses_titles_and_emoji(tmp_path: Path) -> None:
    commands = healthy_commands()
    commands[("systemctl", "is-active", "plugin_loader.service")] = CommandResult(
        ("systemctl", "is-active", "plugin_loader.service"), 3, "inactive\n", ""
    )
    ctx = make_ctx(tmp_path, commands=commands, locale="es")
    report = diagnose(ctx)
    text = render_cli(report)
    assert "❌" in text
    assert "🩺" in text
    assert "Servicio de Decky" in text
    assert "DECKY-SERVICE" not in text
    assert "Qué puedes hacer" in text


def test_spanish_chrome(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, locale="es")
    report = diagnose(ctx)
    text = render_cli(report)
    assert "Todo en orden" in text or "Problemas" in text


def test_only_runs_selected_checks(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, only_ids=frozenset({"SYS-DISK"}))
    report = diagnose(ctx)
    disk = next(r for r in report.results if r.check_id == "SYS-DISK")
    assert disk.status == Status.PASS
    skipped = [r for r in report.results if r.check_id != "SYS-DISK"]
    assert all(r.status == Status.SKIPPED for r in skipped)


def test_global_timeout_marks_partial(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, deadline=time.monotonic() - 1)
    report = diagnose(ctx)
    assert report.partial
    assert all(r.status == Status.SKIPPED for r in report.results)


def test_compact_hides_skipped(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, network=False)
    report = diagnose(ctx)
    text = render_cli(report)
    assert "NET-GITHUB" not in text
    assert "All clear" in text or "ok" in text


def test_verbose_shows_check_ids(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, verbose=True)
    report = diagnose(ctx)
    text = render_cli(report)
    assert "DECKY-INSTALL" in text
    assert "SYS-DISK" in text


def test_checks_command_lists_ids() -> None:
    buf = StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        assert main(["checks", "--no-color"]) == 0
    finally:
        sys.stdout = old
    out = buf.getvalue()
    assert "SYS-DISK" in out
    assert "DECKY-INSTALL" in out


def test_spanish_findings(tmp_path: Path) -> None:
    home = make_home(tmp_path, with_decky=False)
    ctx = make_ctx(tmp_path, home=home, locale="es")
    report = diagnose(ctx)
    inst = next(r for r in report.results if r.check_id == "DECKY-INSTALL")
    assert "no está instalado" in inst.finding.lower()


def test_internal_error_is_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("deckdoctor.cli.diagnose", boom)
    assert main(["--no-network"]) == 2
