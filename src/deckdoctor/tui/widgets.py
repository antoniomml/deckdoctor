from __future__ import annotations

from collections.abc import Callable

from rich.text import Text
from textual.widget import Widget

from deckdoctor.tui.format import PALETTE

_BLOCKS = " ▁▂▃▄▅▆▇█"
TRACK = "#2A3440"
ColorFn = Callable[[float], str]


class Meter(Widget):
    """Full-width horizontal gauge; ``fraction`` is 0..1 or None for unknown."""

    DEFAULT_CSS = "Meter { height: 1; width: 1fr; }"

    def __init__(self, fraction: float | None = None, color: str = PALETTE["primary"], **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.fraction = fraction
        self.color = color

    def set(self, fraction: float | None, color: str | None = None) -> None:
        self.fraction = fraction
        if color:
            self.color = color
        self.refresh()

    def render(self) -> Text:
        width = max(1, self.size.width)
        if self.fraction is None:
            return Text("─" * width, style=TRACK)
        filled = int(round(max(0.0, min(1.0, self.fraction)) * width))
        if self.fraction > 0 and filled == 0:
            filled = 1
        text = Text("━" * filled, style=self.color)
        text.append("━" * (width - filled), style=TRACK)
        return text


class Graph(Widget):
    """Block-character history graph on a fixed scale, newest sample on the right."""

    DEFAULT_CSS = "Graph { height: 3; width: 1fr; }"

    def __init__(self, *, low: float = 0.0, high: float | None = None, floor: float = 1.0,
                 color: ColorFn | None = None, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.low = low
        self.high = high
        self.floor = floor
        self.color = color or (lambda _v: PALETTE["secondary"])
        self.values: list[float] = []

    def push(self, value: float) -> None:
        self.values.append(value)
        del self.values[:-400]
        self.refresh()

    def scale_high(self) -> float:
        if self.high is not None:
            return self.high
        peak = max(self.values, default=self.floor)
        return max(peak * 1.1, self.floor)

    def render(self) -> Text:
        width, height = max(1, self.size.width), max(1, self.size.height)
        data = self.values[-width:]
        low, high = self.low, self.scale_high()
        span = max(high - low, 1e-9)
        levels = height * 8
        heights = []
        for value in data:
            level = int(round((value - low) / span * levels))
            if value > low and level == 0:
                level = 1
            heights.append(max(0, min(levels, level)))
        pad = width - len(data)
        rows = []
        for row in range(height - 1, -1, -1):
            line = Text(" " * pad)
            for value, level in zip(data, heights, strict=True):
                cell = level - row * 8
                if cell >= 8:
                    line.append("█", style=self.color(value))
                elif cell > 0:
                    line.append(_BLOCKS[cell], style=self.color(value))
                elif row == 0:
                    line.append("▁", style=TRACK)
                else:
                    line.append(" ")
            rows.append(line)
        return Text("\n").join(rows)


def threshold_color(warn: float, bad: float, *, base: str = PALETTE["secondary"]) -> ColorFn:
    def pick(value: float) -> str:
        if value >= bad:
            return PALETTE["error"]
        if value >= warn:
            return PALETTE["warning"]
        return base

    return pick
