from __future__ import annotations

from deckdoctor.cli import build_parser


def test_parser_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.command == "diagnose"
    assert args.json is False


def test_help_exits_zero() -> None:
    try:
        build_parser().parse_args(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
