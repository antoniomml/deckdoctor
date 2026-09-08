from io import StringIO
from pathlib import Path

import pytest

from deckdoctor.progress import diagnose_with_progress
from tests.conftest import make_ctx


class Terminal(StringIO):
    def isatty(self) -> bool:
        return True


def test_progress_updates_one_line_and_clears(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stream = Terminal()
    monkeypatch.setattr('sys.stderr', stream)
    monkeypatch.setenv('TERM', 'xterm')
    ctx = make_ctx(tmp_path, only_ids=frozenset({'SYS-DISK', 'HW-BATTERY'}))
    diagnose_with_progress(ctx)
    output = stream.getvalue()
    assert '0/2 checked' in output
    assert '1/2 checked' in output
    assert '50%' in output
    assert '\n' not in output
    assert output.endswith('\r')
    assert ctx.progress is None


def test_redirected_progress_is_silent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stream = StringIO()
    monkeypatch.setattr('sys.stderr', stream)
    diagnose_with_progress(make_ctx(tmp_path))
    assert stream.getvalue() == ''


def test_progress_cleanup_on_interrupt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stream = Terminal()
    monkeypatch.setattr('sys.stderr', stream)
    monkeypatch.setenv('TERM', 'xterm')
    ctx = make_ctx(tmp_path)

    def interrupt(context):
        context.progress('SYS-DISK')
        raise KeyboardInterrupt

    monkeypatch.setattr('deckdoctor.progress.diagnose', interrupt)
    with pytest.raises(KeyboardInterrupt):
        diagnose_with_progress(ctx)
    assert stream.getvalue().endswith('\r')
    assert ctx.progress is None


def test_compact_comparison_omits_measurement_noise(tmp_path: Path) -> None:
    from deckdoctor.renderer import render_cli
    from deckdoctor.runner import diagnose

    report = diagnose(make_ctx(tmp_path))
    report.comparison = [
        {'id': 'SYS-DISK', 'before': 'pass', 'after': 'pass'},
        {'id': 'FP-UPDATES', 'before': 'warning', 'after': 'pass'},
    ]
    assert 'SYS-DISK: pass -> pass' not in render_cli(report)
    assert 'FP-UPDATES: warning -> pass' in render_cli(report)
    report.verbose = True
    assert 'SYS-DISK: pass -> pass' in render_cli(report)
