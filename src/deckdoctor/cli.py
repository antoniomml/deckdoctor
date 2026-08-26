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
from deckdoctor.fixes import KNOWN_FIX_IDS, apply_plans, collect_plans
from deckdoctor.http import HttpClient
from deckdoctor.i18n import detect_locale, translate
from deckdoctor.models import FixPlan, Report, Status
from deckdoctor.renderer import color_enabled, render_checks_catalog, render_cli, render_fix_plan, render_fix_results
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
    parser.add_argument("-v", "--verbose", action="store_true", help=t("cli.verbose"))
    parser.add_argument("--no-color", action="store_true", help=t("cli.no_color"))
    parser.add_argument("--yes", action="store_true", help=t("cli.yes"))
    parser.add_argument(
        "command",
        nargs="?",
        default="diagnose",
        choices=["diagnose", "report", "fix", "checks"],
        help=t("cli.command"),
    )
    parser.add_argument("target", nargs="?", default=None, help=t("cli.target"))
    return parser


def build_context(
    *,
    network: bool,
    locale: str = "en",
    ascii_mode: bool = False,
    only_ids: frozenset[str] | None = None,
    deadline: float | None = None,
    verbose: bool = False,
    color: bool = False,
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
        verbose=verbose,
        color=color,
    )


def _exit_code(status_values: list[Status]) -> int:
    if any(s == Status.FAIL for s in status_values):
        return 1
    return 0


def _use_color(args: argparse.Namespace) -> bool:
    return color_enabled(ascii_mode=bool(args.ascii), color=not args.no_color)


def _print_report(report: Report, sanitizer: Sanitizer, plans: list[FixPlan], *, as_json: bool) -> None:
    if as_json:
        payload = sanitizer.apply_obj(report.to_dict())
        payload["fixes"] = [
            {
                "id": p.id,
                "title": p.title,
                "mutation": p.mutation,
                "needs_root": p.needs_root,
            }
            for p in plans
        ]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    print(sanitizer.apply(render_cli(report, plans=plans)), end="")


def _filter_plans(plans: list[FixPlan], target: str | None, locale: str) -> tuple[list[FixPlan], int]:
    if not target:
        return plans, 0
    wanted = target.strip().lower()
    if wanted not in KNOWN_FIX_IDS:
        print(
            translate(locale, "fix.unknown", name=target, known=", ".join(KNOWN_FIX_IDS)),
            file=sys.stderr,
        )
        return [], 2
    matched = [p for p in plans if p.id == wanted]
    if not matched:
        print(translate(locale, "fix.not_applicable", name=target), file=sys.stderr)
        return [], 0
    return matched, 0


def _main(argv: list[str] | None) -> int:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang", choices=["en", "es"], default=None)
    pre_args, _ = pre.parse_known_args(argv)
    locale = detect_locale(pre_args.lang)
    parser = build_parser(locale)
    args = parser.parse_args(argv)
    locale = detect_locale(args.lang)

    if args.command == "checks":
        print(render_checks_catalog(locale, ascii_mode=bool(args.ascii), color=_use_color(args)), end="")
        return 0

    if args.target and args.command != "fix":
        parser.error(translate(locale, "cli.target"))

    deadline = None
    if args.timeout and args.timeout > 0:
        deadline = time.monotonic() + float(args.timeout)
    color = _use_color(args)
    ctx = build_context(
        network=not args.no_network,
        locale=locale,
        ascii_mode=bool(args.ascii),
        only_ids=parse_only_ids(args.only),
        deadline=deadline,
        verbose=bool(args.verbose),
        color=color,
    )
    report = diagnose(ctx)
    sanitizer = Sanitizer(user=ctx.user, home=str(ctx.home), hostname=ctx.hostname)
    plans = collect_plans(ctx, report)

    if args.command == "fix":
        plans, code = _filter_plans(plans, args.target, locale)
        if code:
            return code
        print(sanitizer.apply(render_fix_plan(plans, locale, ascii_mode=bool(args.ascii), color=color)), end="")
        if not plans or not args.yes:
            return 0
        results = apply_plans(ctx, plans)
        print(sanitizer.apply(render_fix_results(results, locale, color=color)), end="")
        print(translate(locale, "fix.rediagnose"), file=sys.stderr)
        ctx2 = build_context(
            network=not args.no_network,
            locale=locale,
            ascii_mode=bool(args.ascii),
            only_ids=parse_only_ids(args.only),
            deadline=deadline,
            verbose=bool(args.verbose),
            color=color,
        )
        report2 = diagnose(ctx2)
        plans2 = collect_plans(ctx2, report2)
        _print_report(report2, sanitizer, plans2, as_json=bool(args.json))
        if any(not item.ok for item in results):
            return 1
        return _exit_code([r.status for r in report2.results])

    _print_report(report, sanitizer, plans, as_json=bool(args.json))

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
