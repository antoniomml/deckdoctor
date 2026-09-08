from __future__ import annotations

import os
import shutil
import sys

from deckdoctor.checks import ALL_CHECKS
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import Report
from deckdoctor.runner import diagnose


def diagnose_with_progress(ctx: DiagnosticContext) -> Report:
    """Keep transient progress on stderr; redirected output stays machine readable."""
    stream = sys.stderr
    if not stream.isatty() or os.environ.get("TERM") == "dumb":
        return diagnose(ctx)
    checks = [c for c in ALL_CHECKS if (ctx.only_ids is None or c.id in ctx.only_ids)
              and (ctx.network_enabled or not c.requires_network)]
    positions = {c.id: i for i, c in enumerate(checks)}
    titles = {c.id: c.title for c in checks}
    previous = ctx.progress
    width = 0

    def progress(check_id: str) -> None:
        nonlocal width
        completed = positions[check_id]
        total = len(checks)
        percent = completed * 100 // total
        bar = '#' * (percent // 10) + '-' * (10 - percent // 10)
        label = ctx.tr("progress.check", done=completed, total=total, title=titles[check_id])
        columns = max(1, shutil.get_terminal_size().columns - 1)
        text = f"[{bar}] {percent:3d}% {label}"[:columns]
        stream.write("\r" + text.ljust(min(width, columns)))
        stream.flush()
        width = len(text)

    ctx.progress = progress
    try:
        return diagnose(ctx)
    finally:
        ctx.progress = previous
        if width:
            stream.write("\r" + " " * width + "\r")
            stream.flush()
