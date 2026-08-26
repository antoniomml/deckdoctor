from __future__ import annotations

import time
from pathlib import Path

import pytest

from deckdoctor.cli import build_parser, main
from deckdoctor.models import Status
from deckdoctor.renderer import render_cli
from deckdoctor.runner import diagnose
from tests.conftest import make_ctx


def test_parser_defaults() -> None:
    args = build_parser("en").parse_args([])
    assert args.command == "diagnose"
    assert args.json is False
    assert args.ascii is False
    assert args.only is None
    assert args.timeout == 60.0


def test_help_exits_zero() -> None:
    try:
        build_parser("en").parse_args(["--help"])
    except SystemExit as exc:
        assert exc.code == 0


def test_ascii_marks(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, ascii_mode=True)
    report = diagnose(ctx)
    text = render_cli(report)
    assert "✓" not in text
    assert "OK" in text


def test_spanish_chrome(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, locale="es")
    report = diagnose(ctx)
    text = render_cli(report)
    assert "Problemas encontrados" in text


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


def test_internal_error_is_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("deckdoctor.cli.diagnose", boom)
    assert main(["--no-network"]) == 2
