"""Pure formatting helpers for the dashboard. No Textual imports, so they are unit-testable."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from deckdoctor.checks._util import format_bytes
from deckdoctor.models import Report, Status

PALETTE = {
    "primary": "#1A9FFF",
    "secondary": "#66C0F4",
    "accent": "#5CE1E6",
    "warning": "#FFC83D",
    "error": "#FF5F5F",
    "success": "#5DD879",
    "foreground": "#E6EDF3",
    "muted": "#7D8794",
    "background": "#0B0F14",
    "surface": "#11161D",
    "panel": "#1A222C",
}

STATUS_GLYPH: dict[Status, tuple[str, str]] = {
    Status.PASS: ("✔", "$success"),
    Status.INFO: ("●", "$primary"),
    Status.WARNING: ("▲", "$warning"),
    Status.FAIL: ("✖", "$error"),
    Status.SKIPPED: ("○", "$text-muted"),
    Status.UNKNOWN: ("?", "$warning"),
}

STATUS_ORDER = (Status.FAIL, Status.WARNING, Status.UNKNOWN, Status.INFO, Status.PASS, Status.SKIPPED)


def hex_of(variable: str) -> str:
    """Map a ``$theme`` variable used in markup to a concrete color for Rich renderables."""
    name = variable.lstrip("$")
    return PALETTE.get("muted" if name == "text-muted" else name, PALETTE["foreground"])


def glyph(status: Status) -> str:
    mark, color = STATUS_GLYPH[status]
    return f"[{color}]{mark}[/]"


def counts(report: Report) -> Counter[Status]:
    return Counter(r.status for r in report.results)


def verdict(report: Report | None) -> tuple[str, int, str]:
    """Return ``(state, count, color)``; state is scanning|ok|limited|attention|problem|incomplete."""
    if report is None:
        return "scanning", 0, "$primary"
    tally = counts(report)
    if tally[Status.FAIL]:
        return "problem", tally[Status.FAIL], "$error"
    if report.partial:
        return "incomplete", 0, "$warning"
    if tally[Status.WARNING]:
        return "attention", tally[Status.WARNING], "$warning"
    verified = sum(tally[s] for s in (Status.PASS, Status.INFO))
    if tally[Status.UNKNOWN]:
        return "limited", tally[Status.UNKNOWN], "$success"
    return "ok", verified, "$success"


def size(num: int | None) -> str:
    if num is None:
        return "…"
    if num <= 0:
        return "0 B"
    return format_bytes(num)


def duration(hours: float | None) -> str:
    if hours is None:
        return ""
    minutes = int(round(hours * 60))
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d} min"


def day(timestamp: int | None, never: str) -> str:
    if not timestamp:
        return never
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return never


def hours(minutes: int | None) -> str:
    if not minutes:
        return "—"
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes / 60:.0f} h" if minutes >= 600 else f"{minutes / 60:.1f} h"


def bar(fraction: float | None, width: int, *, color: str = "$primary", empty: str = "$panel-lighten-2") -> str:
    """A thin horizontal gauge using markup colors."""
    width = max(1, width)
    if fraction is None:
        return f"[{empty}]{'─' * width}[/]"
    fraction = max(0.0, min(1.0, fraction))
    filled = int(round(fraction * width))
    out = ""
    if filled:
        out += f"[{color}]{'━' * filled}[/]"
    if width - filled:
        out += f"[{empty}]{'━' * (width - filled)}[/]"
    return out


def level_color(fraction: float | None, *, warn: float = 0.75, bad: float = 0.9) -> str:
    if fraction is None:
        return "$text-muted"
    if fraction >= bad:
        return "$error"
    if fraction >= warn:
        return "$warning"
    return "$success"


def temp_color(celsius: float | None) -> str:
    if celsius is None:
        return "$text-muted"
    if celsius >= 90:
        return "$error"
    if celsius >= 75:
        return "$warning"
    return "$success"


def battery_color(percent: float | None) -> str:
    if percent is None:
        return "$text-muted"
    if percent <= 15:
        return "$error"
    if percent <= 30:
        return "$warning"
    return "$success"
