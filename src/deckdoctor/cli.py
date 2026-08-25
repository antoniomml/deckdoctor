from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from deckdoctor import __version__
from deckdoctor.command import CommandRunner
from deckdoctor.context import DiagnosticContext, default_home, parse_only_ids
from deckdoctor.http import HttpClient
from deckdoctor.i18n import detect_locale, translate
from deckdoctor.models import Status
from deckdoctor.renderer import render_cli
from deckdoctor.report import render_markdown
from deckdoctor.runner import DEFAULT_TIMEOUT_SECONDS, diagnose
from deckdoctor.sanitizer import Sanitizer


def build_parser(locale: str | None = None) -> argparse.ArgumentParser:
    loc = locale or detect_locale()

    def t(key: str) -> str:
        return translate(loc, key)

    parser = argparse.ArgumentParser(
        prog="deckdoctor",
        description=t("cli.description"),
    )
    parser.add_argument("--version", action="version", version=f"DeckDoctor {__version__}")
    parser.add_argument("--json", action="store_true", help=t("cli.json"))
    parser.add_argument("--no-network", action="store_true", help=t("cli.no_network"))
    parser.add_argument("--output", "-o", type=Path, default=None, help=t("cli.output"))
    parser.add_argument("--ascii", "--plain", action="store_true", dest="ascii", help=t("cli.ascii"))
    parser.add_argument("--only", default=None, help=t("cli.only"))
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=t("cli.timeout"),
    )
    parser.add_argument("--lang", choices=["en", "es"], default=None, help=t("cli.lang"))
    parser.add_argument(
        "command",
        nargs="?",
        default="diagnose",
        choices=["diagnose", "report"],
        help=t("cli.command"),
    )
    return parser


def build_context(
    *,
    network: bool,
    locale: str = "en",
    ascii_mode: bool = False,
    only_ids: frozenset[str] | None = None,
    deadline: float | None = None,
) -> DiagnosticContext:
    return DiagnosticContext(
        home=default_home(),
        runner=CommandRunner(),
        http=HttpClient(),
        now=datetime.now(UTC),
        network_enabled=network,
        locale=locale,  # type: ignore[arg-type]
        ascii_mode=ascii_mode,
        only_ids=only_ids,
        deadline=deadline,
    )


def _exit_code(status_values: list[Status]) -> int:
    if any(s == Status.FAIL for s in status_values):
        return 1
    return 0


def _main(argv: list[str] | None) -> int:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang", choices=["en", "es"], default=None)
    pre_args, _ = pre.parse_known_args(argv)
    locale = detect_locale(pre_args.lang)
    parser = build_parser(locale)
    args = parser.parse_args(argv)
    locale = detect_locale(args.lang)
    deadline = None
    if args.timeout and args.timeout > 0:
        deadline = time.monotonic() + float(args.timeout)
    ctx = build_context(
        network=not args.no_network,
        locale=locale,
        ascii_mode=bool(args.ascii),
        only_ids=parse_only_ids(args.only),
        deadline=deadline,
    )
    report = diagnose(ctx)
    sanitizer = Sanitizer(user=ctx.user, home=str(ctx.home), hostname=ctx.hostname)

    if args.json:
        print(json.dumps(sanitizer.apply_obj(report.to_dict()), indent=2, ensure_ascii=False))
    else:
        print(sanitizer.apply(render_cli(report)), end="")

    if args.command == "report":
        path = args.output or Path.cwd() / "deckdoctor-report.md"
        body = render_markdown(report, sanitizer)
        path.write_text(body, encoding="utf-8")
        print(translate(locale, "ui.wrote", path=path), file=sys.stderr)

    return _exit_code([r.status for r in report.results])


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 — CLI boundary; map to exit 2
        locale = detect_locale()
        print(translate(locale, "ui.internal_error", exc=exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
