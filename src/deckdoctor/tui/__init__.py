"""Interactive dashboard. Textual is imported lazily so the text CLI works without it."""
from __future__ import annotations

import importlib.util
from typing import Any


def available() -> bool:
    return importlib.util.find_spec("textual") is not None


def run(**options: Any) -> int:
    from deckdoctor.tui.app import DeckDoctorApp, TuiOptions

    app = DeckDoctorApp(TuiOptions(**options))
    result = app.run()
    return int(result or 0)
