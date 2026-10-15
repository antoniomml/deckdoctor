from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("textual")

from rich.text import Text  # noqa: E402
from textual.widgets import Button, DataTable, Static, TabbedContent  # noqa: E402

from deckdoctor.fixes import FakeFixExecutor  # noqa: E402
from deckdoctor.models import CheckResult, Report, Status  # noqa: E402
from deckdoctor.tui import format as fmt  # noqa: E402
from deckdoctor.tui.app import DeckDoctorApp, TuiOptions  # noqa: E402
from deckdoctor.tui.screens import ConfirmFixScreen, GameScreen, HelpScreen  # noqa: E402
from deckdoctor.tui.widgets import Graph, Meter  # noqa: E402
from tests.conftest import make_ctx, make_home  # noqa: E402
from tests.test_hardware_storage import fake_deck_sys, steam_library, write  # noqa: E402


def make_app(tmp_path: Path, *, home: Path | None = None, locale: str = "en", **extra: Any) -> DeckDoctorApp:
    if home is None:
        ctx, _sd = steam_library(tmp_path)
        home = ctx.home  # type: ignore[attr-defined]
    sys_root = tmp_path / "sys"
    fake_deck_sys(sys_root)
    write(sys_root / "class/dmi/id/sys_vendor", "Valve\n")
    write(sys_root / "class/dmi/id/product_name", "Jupiter\n")
    write(tmp_path / "proc/stat", "cpu 1 0 1 8 0 0 0 0\n")
    options = TuiOptions(
        locale=locale,
        network=False,
        make_context=lambda net: make_ctx(tmp_path, home=home, network=net, locale=locale),
        executor=FakeFixExecutor(),
        sys_root=sys_root,
        proc_root=tmp_path / "proc",
        os_release=tmp_path / "os-release",
        report_dir=tmp_path,
        sample_interval=0.1,
        **extra,
    )
    return DeckDoctorApp(options)


async def wait_for(pilot: Any, condition: Callable[[], bool], timeout: float = 30) -> None:
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while not condition():
        if loop.time() > end:
            raise AssertionError("timed out waiting for the dashboard")
        await pilot.pause(0.05)


def ready(app: DeckDoctorApp) -> bool:
    return app.report is not None and app.storage is not None and app.storage.measured and app.last_sample is not None


def text_of(app: DeckDoctorApp, selector: str) -> str:
    return str(app.query_one(selector, Static).render())


def test_dashboard_scans_and_shows_every_tab(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = make_app(tmp_path)
        async with app.run_test(size=(150, 45)) as pilot:
            await wait_for(pilot, lambda: ready(app))
            await pilot.pause()
            assert "Steam Deck LCD" in text_of(app, "#top-device")
            assert text_of(app, "#verdict")
            tabs = app.query_one("#main", TabbedContent)
            for key, name in zip("123456", ("overview", "checks", "monitor", "games", "fixes", "report"), strict=True):
                await pilot.press(key)
                assert tabs.active == name
            await pilot.press("4")
            table = app.query_one("#games-table", DataTable)
            assert table.row_count == 2
            table.focus()
            await pilot.press("enter")
            await wait_for(pilot, lambda: isinstance(app.screen, GameScreen))
            await pilot.press("escape")
            await pilot.press("question_mark")
            assert isinstance(app.screen, HelpScreen)
            seen = app.last_sample
            await wait_for(pilot, lambda: app.last_sample is not seen)  # live updates must not hit the modal
            await pilot.press("escape")
            assert app.query_one("#leftovers-table", DataTable).row_count == 3

    asyncio.run(scenario())


def test_dashboard_in_spanish_on_a_narrow_terminal(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = make_app(tmp_path, locale="es")
        async with app.run_test(size=(80, 24)) as pilot:
            await wait_for(pilot, lambda: ready(app))
            assert app.query_one("#main", TabbedContent).has_class("narrow")
            assert "Resumen" in str(app.query_one("#main", TabbedContent).get_tab("overview").label)

    asyncio.run(scenario())


def test_fix_asks_first_then_verifies(tmp_path: Path) -> None:
    home = make_home(tmp_path, cef=False)
    marker = home / ".steam/steam/.cef-enable-remote-debugging"

    async def scenario() -> None:
        app = make_app(tmp_path, home=home)
        async with app.run_test(size=(150, 45)) as pilot:
            await wait_for(pilot, lambda: app.report is not None)
            assert any(plan.id == "cef-debug" for plan in app.plans)
            await pilot.press("5")
            await pilot.pause()
            button = next(b for b in app.query(".fix-apply").results(Button)
                          if getattr(b.parent, "plan", None) and b.parent.plan.id == "cef-debug")  # type: ignore[union-attr]
            button.press()
            await wait_for(pilot, lambda: isinstance(app.screen, ConfirmFixScreen))
            await pilot.click("#confirm-no")
            await pilot.pause()
            assert not marker.exists()
            button.press()
            await wait_for(pilot, lambda: isinstance(app.screen, ConfirmFixScreen))
            await pilot.click("#confirm-yes")
            await wait_for(pilot, lambda: bool(app.report and app.report.repair_results))
            assert marker.is_file()
            assert app.report is not None
            assert all(item.ok for item in app.report.repair_results)

    asyncio.run(scenario())


def test_report_saved_sanitised(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = make_app(tmp_path)
        async with app.run_test(size=(150, 45)) as pilot:
            await wait_for(pilot, lambda: app.report is not None)
            await pilot.press("6")
            await pilot.pause()
            await pilot.click("#save-md")
            await wait_for(pilot, lambda: any(tmp_path.glob("deckdoctor-report-*.md")))

    asyncio.run(scenario())
    body = next(tmp_path.glob("deckdoctor-report-*.md")).read_text(encoding="utf-8")
    assert "DeckDoctor" in body
    assert str(tmp_path / "deck") not in body


# --------------------------------------------------------------------------- formatting


def report_with(*statuses: Status) -> Report:
    report = Report(version="test", generated_at="now", results=[], diagnoses=[])
    for index, status in enumerate(statuses):
        report.results.append(CheckResult(check_id=f"X{index}", title="t", status=status, finding="f"))
    return report


def test_verdict_counts_only_failures_as_problems() -> None:
    assert fmt.verdict(report_with(Status.FAIL, Status.WARNING, Status.WARNING))[:2] == ("problem", 1)
    assert fmt.verdict(report_with(Status.WARNING, Status.PASS))[0] == "attention"
    assert fmt.verdict(report_with(Status.PASS, Status.INFO))[0] == "ok"


@pytest.mark.parametrize(("minutes", "text"), [(None, "—"), (0, "—"), (45, "45 min"), (125, "2.1 h"), (6000, "100 h")])
def test_hours(minutes: int | None, text: str) -> None:
    assert fmt.hours(minutes) == text


def test_meter_fills_proportionally() -> None:
    meter = Meter(0.5)
    rendered = Text.assemble(meter.render())
    assert "━" in rendered.plain or "─" in rendered.plain


def test_graph_uses_fixed_scale() -> None:
    graph = Graph(high=100)
    for value in (0, 50, 100):
        graph.push(value)
    assert graph.scale_high() == 100
    auto = Graph(floor=15)
    auto.push(3)
    assert auto.scale_high() == 15


def broken_home(tmp_path: Path) -> Path:
    home = make_home(tmp_path, cef=False)
    (home / "homebrew/services/PluginLoader").chmod(0o644)
    return home


def test_fix_everything_from_the_overview_with_one_confirmation(tmp_path: Path) -> None:
    home = broken_home(tmp_path)

    async def scenario() -> None:
        app = make_app(tmp_path, home=home)
        async with app.run_test(size=(150, 45)) as pilot:
            await wait_for(pilot, lambda: app.report is not None)
            assert {plan.id for plan in app.plans} >= {"cef-debug", "pluginloader-exec"}
            button = app.query_one("#fix-all", Button)
            assert button.display and str(len(app.plans)) in str(button.label)
            await pilot.press("f")
            await wait_for(pilot, lambda: isinstance(app.screen, ConfirmFixScreen))
            assert len(app.screen.plans) == len(app.plans)  # type: ignore[attr-defined]
            await pilot.click("#confirm-yes")
            await wait_for(pilot, lambda: bool(app.report and app.report.repair_results))
            assert not app.plans
            assert not app.query_one("#fix-all", Button).display

    asyncio.run(scenario())
    assert (home / ".steam/steam/.cef-enable-remote-debugging").is_file()
    assert (home / "homebrew/services/PluginLoader").stat().st_mode & 0o111


def test_fix_button_inside_the_check_detail_fixes_only_that(tmp_path: Path) -> None:
    home = broken_home(tmp_path)

    async def scenario() -> None:
        app = make_app(tmp_path, home=home)
        async with app.run_test(size=(150, 45)) as pilot:
            await wait_for(pilot, lambda: app.report is not None)
            await pilot.press("2")
            from deckdoctor.tui.panes import ChecksPane

            checks = app.query_one(ChecksPane)
            checks.select("DECKY-FRONTEND")
            await pilot.pause()
            assert app.query_one("#check-fix-box").display
            assert [plan.id for plan in checks.selected_plans()] == ["cef-debug"]
            app.query_one("#check-fix", Button).press()
            await wait_for(pilot, lambda: isinstance(app.screen, ConfirmFixScreen))
            assert [plan.id for plan in app.screen.plans] == ["cef-debug"]  # type: ignore[attr-defined]
            await pilot.click("#confirm-yes")
            await wait_for(pilot, lambda: bool(app.report and app.report.repair_results))
            assert [plan.id for plan in app.plans] == ["pluginloader-exec"]
            checks.select("DECKY-FRONTEND")
            await pilot.pause()
            assert not app.query_one("#check-fix-box").display

    asyncio.run(scenario())
    assert not (home / "homebrew/services/PluginLoader").stat().st_mode & 0o111


def test_fix_key_with_nothing_to_fix_only_notifies(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = make_app(tmp_path)
        async with app.run_test(size=(150, 45)) as pilot:
            await wait_for(pilot, lambda: app.report is not None)
            assert not app.plans
            await pilot.press("f")
            await pilot.pause()
            assert not isinstance(app.screen, ConfirmFixScreen)

    asyncio.run(scenario())
