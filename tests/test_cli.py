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
from tests.conftest import healthy_commands, make_ctx, make_home, write_plugin


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


def test_compact_snapshot_shows_storage(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    report = diagnose(ctx)
    text = render_cli(report)
    assert "Internal" in text
    assert "free of" in text
    assert "microSD" in text
    assert "not inserted" in text
    assert "game" in text.lower()


def test_compact_uses_titles_and_emoji(tmp_path: Path) -> None:
    commands = healthy_commands()
    commands[("systemctl", "is-active", "plugin_loader.service")] = CommandResult(
        ("systemctl", "is-active", "plugin_loader.service"), 3, "inactive\n", ""
    )
    ctx = make_ctx(tmp_path, commands=commands)
    report = diagnose(ctx)
    text = render_cli(report)
    assert "❌" in text
    assert "🩺" in text
    assert "Decky service" in text
    assert "DECKY-SERVICE" not in text
    assert "plugin_loader.service is not running" in text
    assert "The unit exists but is inactive" not in text
    assert "What you can do" not in text
    assert "deckdoctor report" in text


def test_spanish_opt_in(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path, locale="es")
    report = diagnose(ctx)
    text = render_cli(report)
    assert "Todo en orden" in text or "Problemas" in text or "bien" in text


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


def test_compact_broken_remote_is_short_and_english(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    write_plugin(home, "decky-autoflatpaks", "AutoFlatpaks", "1.6.8")
    commands = healthy_commands()
    remotes_key = ("flatpak", "remotes", "--columns=name,options,url")
    commands[remotes_key] = CommandResult(
        remotes_key,
        0,
        "flathub\tsystem\thttps://dl.flathub.org/repo/\n"
        "onepassword-origin\tuser\thttps://downloads.1password.com/linux/flatpak/1Password.flatpakrepo\n",
        "",
    )
    listing_key = ("flatpak", "remote-ls", "--columns=ref,origin", "-a")
    commands[listing_key] = CommandResult(
        listing_key,
        1,
        "",
        "error: Unable to load summary from remote onepassword-origin: GPG signatures found, but none are in trusted keyring\n",
    )
    flathub_key = (
        "flatpak",
        "remote-ls",
        "--system",
        "flathub",
        "--updates",
        "--columns=application,branch,origin",
    )
    commands[flathub_key] = CommandResult(
        flathub_key,
        0,
        "com.google.Chrome\tstable\tflathub\n",
        "",
    )
    ctx = make_ctx(tmp_path, home=home, commands=commands)
    report = diagnose(ctx)
    text = render_cli(report)
    assert "onepassword-origin" in text
    assert "Cannot list remotes" in text
    assert "FACT:" not in text
    assert "What's going on" not in text
    assert "Problems" not in text
    assert "AutoFlatpaks is installed. Current versions" not in text
    assert "grave" not in text
    assert "aviso" not in text
    assert "`deckdoctor fix` can apply the updates." in text


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


def test_detect_locale_ignores_lang(monkeypatch: pytest.MonkeyPatch) -> None:
    from deckdoctor.i18n import detect_locale

    monkeypatch.setenv("LANG", "es_ES.UTF-8")
    monkeypatch.setenv("LC_ALL", "es_ES.UTF-8")
    monkeypatch.delenv("DECKDOCTOR_LANG", raising=False)
    assert detect_locale() == "en"
    monkeypatch.setenv("DECKDOCTOR_LANG", "es")
    assert detect_locale() == "es"
    assert detect_locale("en") == "en"


def test_parser_yes_short_flag() -> None:
    args = build_parser("en").parse_args(["fix", "-y"])
    assert args.command == "fix"
    assert args.yes is True
    args = build_parser("en").parse_args(["-y", "fix"])
    assert args.yes is True


def test_confirm_fix_yes_flag_skips_prompt() -> None:
    from io import StringIO

    from deckdoctor.cli import confirm_fix

    out = StringIO()
    assert confirm_fix(yes=True, locale="en", stdin=StringIO("n\n"), stderr=out) is True
    assert out.getvalue() == ""


def test_confirm_fix_tty_y_and_n() -> None:
    from io import StringIO

    from deckdoctor.cli import confirm_fix

    class Tty(StringIO):
        def isatty(self) -> bool:
            return True

    err = StringIO()
    assert confirm_fix(yes=False, locale="en", stdin=Tty("y\n"), stderr=err) is True
    assert "Apply this plan?" in err.getvalue()
    err = StringIO()
    assert confirm_fix(yes=False, locale="en", stdin=Tty("n\n"), stderr=err) is False
    assert "Nothing was changed." in err.getvalue()
    err = StringIO()
    assert confirm_fix(yes=False, locale="en", stdin=Tty("\n"), stderr=err) is False


def test_confirm_fix_non_tty_needs_dash_y() -> None:
    from io import StringIO

    from deckdoctor.cli import confirm_fix

    err = StringIO()
    assert confirm_fix(yes=False, locale="en", stdin=StringIO("y\n"), stderr=err) is False
    assert "-y" in err.getvalue()


def test_translation_tables_have_matching_keys() -> None:
    from deckdoctor.i18n import MESSAGES

    assert set(MESSAGES["en"]) == set(MESSAGES["es"])
