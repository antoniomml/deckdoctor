#!/usr/bin/env python3
"""Render the dashboard headless and save one SVG (and PNG if rsvg-convert exists) per tab.

    .venv/bin/python scripts/screenshots.py --out docs/screenshots --size 160x45 --lang en
"""
from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.pop("NO_COLOR", None)
os.environ["COLORTERM"] = "truecolor"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deckdoctor.tui.app import TABS, DeckDoctorApp, TuiOptions  # noqa: E402
from deckdoctor.tui.panes import ChecksPane  # noqa: E402


def _save(app: DeckDoctorApp, out: Path, name: str) -> None:
    svg = out / f"{name}.svg"
    app.save_screenshot(filename=svg.name, path=str(out))
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-o", str(svg.with_suffix(".png")), str(svg)], check=False)
    print(svg)


async def capture(out: Path, size: tuple[int, int], lang: str, network: bool, tabs: list[str], wait: float,
                  fix_flow: bool = False) -> None:
    app = DeckDoctorApp(TuiOptions(locale=lang, network=network))
    async with app.run_test(size=size) as pilot:
        for _ in range(int(wait * 10)):
            await pilot.pause(0.1)
            if app.report is not None and app.storage is not None and app.storage.measured:
                break
        await pilot.pause(1.5)
        suffix = f"{lang}-{size[0]}x{size[1]}"
        for tab in tabs:
            app.action_tab(tab)
            await pilot.pause(0.6)
            _save(app, out, f"{tab}-{suffix}")
        if fix_flow and app.plans:
            # Shows the fix button and the confirmation dialog, then cancels: nothing is applied.
            app.action_tab("checks")
            app.main.query_one(ChecksPane).select(app.plans[0].related_checks[0])
            await pilot.pause(0.6)
            _save(app, out, f"check-fix-{suffix}")
            app.action_fix()
            await pilot.pause(0.6)
            _save(app, out, f"confirm-{suffix}")
            await pilot.press("escape")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("build/screenshots"))
    parser.add_argument("--size", default="160x45")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--tabs", default=",".join(TABS))
    parser.add_argument("--wait", type=float, default=90)
    parser.add_argument("--fix-flow", action="store_true", help="also capture a fix button and its (cancelled) confirmation")
    args = parser.parse_args()
    width, height = (int(v) for v in args.size.split("x"))
    args.out.mkdir(parents=True, exist_ok=True)
    asyncio.run(capture(args.out, (width, height), args.lang, not args.no_network, args.tabs.split(","), args.wait,
                        args.fix_flow))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
