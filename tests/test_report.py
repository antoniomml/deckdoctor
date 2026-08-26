from __future__ import annotations

from pathlib import Path

from deckdoctor.report import render_markdown
from deckdoctor.runner import diagnose
from deckdoctor.sanitizer import Sanitizer
from tests.conftest import make_ctx, make_home


def test_report_is_sanitised(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    ctx = make_ctx(tmp_path, home=home)
    ctx.user = "antonio"
    ctx.hostname = "steamdeck"
    ctx.home = home
    report = diagnose(ctx)
    san = Sanitizer(user="antonio", home=str(home), hostname="steamdeck")
    body = render_markdown(report, san)
    assert "# DeckDoctor report" in body
    assert "antonio" not in body
    assert str(home) not in body
    assert "/home/<USER>" in body or "<USER>" in body
    assert "steamloopback.host" in body
    assert "CEF / steamloopback.host" in body
