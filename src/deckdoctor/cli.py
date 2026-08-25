from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from deckdoctor import __version__
from deckdoctor.command import CommandRunner
from deckdoctor.context import DiagnosticContext, default_home
from deckdoctor.http import HttpClient
from deckdoctor.models import Status
from deckdoctor.report import render_markdown
from deckdoctor.renderer import render_cli
from deckdoctor.runner import diagnose
from deckdoctor.sanitizer import Sanitizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deckdoctor",
        description="Read-only diagnostics for SteamOS, Decky Loader, plugins, and Flatpak.",
    )
    parser.add_argument("--version", action="version", version=f"DeckDoctor {__version__}")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--no-network", action="store_true", help="Skip checks that need the internet")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Report path (for the report command)")
    parser.add_argument(
        "command",
        nargs="?",
        default="diagnose",
        choices=["diagnose", "report"],
        help="diagnose (default) or report",
    )
    return parser


def build_context(*, network: bool) -> DiagnosticContext:
    return DiagnosticContext(
        home=default_home(),
        runner=CommandRunner(),
        http=HttpClient(),
        now=datetime.now(timezone.utc),
        network_enabled=network,
    )


def _exit_code(status_values: list[Status]) -> int:
    if any(s == Status.FAIL for s in status_values):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ctx = build_context(network=not args.no_network)
    report = diagnose(ctx)
    sanitizer = Sanitizer(user=ctx.user, home=str(ctx.home), hostname=ctx.hostname)

    if args.json:
        print(sanitizer.apply(json.dumps(report.to_dict(), indent=2, ensure_ascii=False)))
    else:
        print(sanitizer.apply(render_cli(report)), end="")

    if args.command == "report":
        path = args.output or Path.cwd() / "deckdoctor-report.md"
        body = render_markdown(report, sanitizer)
        path.write_text(body, encoding="utf-8")
        print(f"Wrote {path}", file=sys.stderr)

    return _exit_code([r.status for r in report.results])


if __name__ == "__main__":
    raise SystemExit(main())
