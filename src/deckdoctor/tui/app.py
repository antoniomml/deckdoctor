from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from textual import events, on, work
from textual.app import App, ComposeResult, SuspendNotSupported
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.theme import Theme
from textual.widgets import Footer, Static, TabbedContent, TabPane
from textual.worker import get_current_worker

from deckdoctor import __version__, storage
from deckdoctor.checks import ALL_CHECKS
from deckdoctor.context import DiagnosticContext, parse_os_release
from deckdoctor.device import Device, identify
from deckdoctor.fixes import apply_plans, collect_plans, verify_results
from deckdoctor.fixes.executor import FixExecutor
from deckdoctor.i18n import translate
from deckdoctor.models import FixPlan, FixResult, Report, Status
from deckdoctor.report import render_markdown
from deckdoctor.runner import DEFAULT_TIMEOUT_SECONDS, diagnose
from deckdoctor.sanitizer import Sanitizer
from deckdoctor.sensors import Sample, Sampler
from deckdoctor.tui import format as fmt
from deckdoctor.tui.panes import (
    ChecksPane,
    FixesPane,
    FixRequested,
    GamesPane,
    MonitorPane,
    OverviewPane,
    ReportPane,
)
from deckdoctor.tui.screens import ConfirmFixScreen, GameScreen, HelpScreen

TABS = ("overview", "checks", "monitor", "games", "fixes", "report")
NARROW_BELOW = 110

DECK_THEME = Theme(
    name="deckdoctor",
    primary=fmt.PALETTE["primary"],
    secondary=fmt.PALETTE["secondary"],
    accent=fmt.PALETTE["accent"],
    warning=fmt.PALETTE["warning"],
    error=fmt.PALETTE["error"],
    success=fmt.PALETTE["success"],
    foreground=fmt.PALETTE["foreground"],
    background=fmt.PALETTE["background"],
    surface=fmt.PALETTE["surface"],
    panel=fmt.PALETTE["panel"],
    dark=True,
)

CSS = """
Screen { background: $background; }
#topbar { height: 1; background: $panel; padding: 0 1; }
#brand { width: auto; }
#top-device { width: 1fr; content-align: center middle; color: $text-muted; }
#top-live { width: auto; }
#main { height: 1fr; }
#main > ContentSwitcher > TabPane { padding: 1 1 0 1; }
.card {
    border: round $panel-lighten-2;
    border-title-color: $secondary;
    border-title-style: bold;
    padding: 0 1;
    background: $surface;
    height: auto;
    margin: 0 0 1 0;
}
.hint { color: $text-muted; padding: 0 1; height: auto; }
.note { color: $text-muted; padding: 1 1; height: auto; }

#ov-columns { height: 1fr; }
#ov-left { width: 64; height: 1fr; overflow-y: auto; }
#ov-right { width: 1fr; height: 1fr; margin-left: 1; }
#attention { height: 1fr; border: none; padding: 0; background: $surface; }
#attention:focus { border: none; background-tint: $foreground 3%; }
#attention > .option-list--option { padding: 0 1; }
#attention-hint { padding: 0; }
#verdict { height: auto; padding-top: 1; }
#verdict-detail { height: auto; }
#tally { height: auto; padding: 1 0; }
#scan-progress { height: 1; }
#scan-progress Bar { width: 1fr; }
#scan-label { padding: 0 0 1 0; }

#main.narrow #ov-columns { layout: vertical; overflow-y: auto; }
#main.narrow #ov-left { width: 1fr; height: auto; overflow-y: hidden; }
#main.narrow #ov-right { width: 1fr; height: auto; min-height: 14; margin-left: 0; }
#main.narrow #attention { height: auto; max-height: 40; }

#checks-side { width: 40; height: 1fr; }
#checks-filter { padding: 0 0 1 1; }
#check-list { height: 1fr; }
#check-detail { width: 1fr; height: 1fr; margin: 0 0 0 1; padding: 1 2; }
#main.narrow #checks-side { width: 32; }

#monitor-note { padding: 0 0 1 1; }
#metrics { grid-size: 4; grid-gutter: 0 1; grid-rows: 6; height: auto; }
#main.narrow #metrics { grid-size: 2; }
.metric {
    border: round $panel-lighten-2;
    border-title-color: $text-muted;
    background: $surface;
    padding: 0 1;
    height: 6;
}
.metric-value { height: 1; }
.metric-graph { height: 3; }
#storage-card, #battery-card { height: auto; }
#storage-card Static, #battery-card Static { height: auto; }
.spaced { margin-bottom: 1; }
#proc-card { height: auto; margin-top: 1; }
#proc-table { height: auto; max-height: 14; background: $surface; }

#library-cards { height: auto; }
.library-card { width: 1fr; height: auto; margin-right: 1; }
.library-card Static { height: auto; }
.library-card:last-of-type { margin-right: 0; }
#games-status { padding: 0 0 1 1; }
#games-tabs { height: 1fr; }
#games-tabs TabPane { padding: 0; }
#games-table, #leftovers-table { height: 1fr; }

#fix-intro { padding: 0 0 1 1; }
#fix-empty { padding: 1 2; height: auto; }
#fix-list { height: auto; }
.fix-card Button { margin-top: 1; }
#fix-all { margin: 0 0 1 0; width: 100%; }
#fix-every { margin: 1 0 0 0; }
#check-fix-box { height: auto; margin-bottom: 1; padding: 0 0 1 0; border-bottom: solid $warning 40%; }
#check-fix-box Button { margin-top: 1; }
#confirm-scroll { height: auto; max-height: 24; }
#report-actions { height: auto; padding: 1 0; }
#report-actions Button { margin-right: 1; }
#report-saved { width: 1fr; padding: 1 1; color: $success; }
#report-scroll { height: 1fr; padding: 0 1; }

ModalScreen { align: center middle; background: $background 70%; }
.modal-box {
    width: 84;
    max-width: 95%;
    height: auto;
    max-height: 90%;
    border: round $primary;
    border-title-color: $primary;
    border-title-style: bold;
    background: $surface;
    padding: 1 2;
}
.modal-buttons { height: auto; align-horizontal: right; margin-top: 1; }
.modal-buttons Button { margin-left: 1; }
#game-scroll { height: auto; max-height: 32; }
#game-loading { height: 3; }
#game-close, #help-close { margin-top: 1; }
"""


@dataclass
class TuiOptions:
    locale: str = "en"
    network: bool = True
    only_ids: frozenset[str] | None = None
    symptom: str | None = None
    appid: int | None = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    initial_tab: str = "overview"
    make_context: Callable[[bool], DiagnosticContext] | None = None
    executor: FixExecutor | None = None
    sys_root: Path = Path("/sys")
    proc_root: Path = Path("/proc")
    os_release: Path = Path("/etc/os-release")
    report_dir: Path | None = None
    sample_interval: float = 1.0
    measure_storage: bool = True


class DeckDoctorApp(App[int]):
    TITLE = "DeckDoctor"
    CSS = CSS

    def __init__(self, options: TuiOptions | None = None) -> None:
        super().__init__()
        self.options = options or TuiOptions()
        self.lang = self.options.locale
        self.network = self.options.network
        self.ctx: DiagnosticContext | None = None
        self.report: Report | None = None
        self.plans: list[FixPlan] = []
        self.storage: storage.StorageReport | None = None
        self.device: Device | None = None
        self.last_sample: Sample | None = None
        self._scanning = False
        self._monitor_visible = self.options.initial_tab == "monitor"
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._last_fix: list[FixPlan] = []
        t = self.t
        self.bind("q", "quit", description=t("tui.key.quit"))
        self.bind("r", "rescan", description=t("tui.key.rescan"))
        self.bind("n", "toggle_network", description=t("tui.key.network"))
        self.bind("f", "fix", description=t("tui.key.fix"))
        self.bind("p", "problems", description=t("tui.key.problems"))
        self.bind("s", "sort", description=t("tui.key.sort"))
        self.bind("question_mark", "help", description=t("tui.key.help"), key_display="?")
        for index, name in enumerate(TABS, start=1):
            self.bind(str(index), f"tab('{name}')", show=False)

    @property
    def main(self) -> Screen[Any]:
        """The dashboard screen; ``App.query_one`` would search whichever modal is on top."""
        return self.screen_stack[0]

    def t(self, key: str, **kwargs: object) -> str:
        return translate(self.lang, key, **kwargs)

    # ------------------------------------------------------------------ layout

    def compose(self) -> ComposeResult:
        with Horizontal(id="topbar"):
            yield Static(f"[b $primary]✚ DeckDoctor[/] [$text-muted]{__version__}[/]", id="brand")
            yield Static("", id="top-device")
            yield Static("", id="top-live")
        initial = self.options.initial_tab if self.options.initial_tab in TABS else "overview"
        with TabbedContent(id="main", initial=initial):
            with TabPane(self.t("tui.tab.overview"), id="overview"):
                yield OverviewPane(self.lang, id="overview-pane")
            with TabPane(self.t("tui.tab.checks"), id="checks"):
                yield ChecksPane(self.lang, id="checks-pane")
            with TabPane(self.t("tui.tab.monitor"), id="monitor"):
                yield MonitorPane(self.lang, id="monitor-pane")
            with TabPane(self.t("tui.tab.games"), id="games"):
                yield GamesPane(self.lang, id="games-pane")
            with TabPane(self.t("tui.tab.fixes"), id="fixes"):
                yield FixesPane(self.lang, id="fixes-pane")
            with TabPane(self.t("tui.tab.report"), id="report"):
                yield ReportPane(self.lang, id="report-pane")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(DECK_THEME)
        self.theme = "deckdoctor"
        self._apply_layout(self.size.width)
        self.device = identify(self.options.sys_root, self.options.proc_root)
        os_line = self._os_line()
        self.main.query_one(OverviewPane).show_device(self.device, os_line)
        self.main.query_one("#top-device", Static).update(" · ".join(filter(None, (self.device.model, os_line))))
        self.sampler_loop()
        self.start_scan()
        self.load_storage()

    def on_unmount(self) -> None:
        self._stop.set()
        self._wake.set()

    def on_resize(self, event: events.Resize) -> None:
        self._apply_layout(event.size.width)

    def _apply_layout(self, width: int) -> None:
        try:
            self.main.query_one("#main", TabbedContent).set_class(width < NARROW_BELOW, "narrow")
        except Exception:  # noqa: BLE001 — resize can arrive before compose
            pass

    def _os_line(self) -> str:
        try:
            data = parse_os_release(self.options.os_release.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return ""
        return data.get("PRETTY_NAME") or " ".join(filter(None, (data.get("NAME"), data.get("VERSION_ID"))))

    def _post(self, callback: Callable[..., Any], *args: Any) -> bool:
        """Run ``callback`` on the UI thread; False once the app is shutting down."""
        if self._stop.is_set():
            return False

        def guarded() -> None:
            # A worker result can land while the app is tearing its widgets down; drop it.
            try:
                callback(*args)
            except NoMatches:
                pass

        try:
            self.call_from_thread(guarded)
        except RuntimeError:
            return False
        return True

    # ------------------------------------------------------------------ context

    def _make_context(self, network: bool | None = None) -> DiagnosticContext:
        net = self.network if network is None else network
        if self.options.make_context is not None:
            ctx = self.options.make_context(net)
        else:
            from deckdoctor.cli import build_context

            deadline = time.monotonic() + self.options.timeout if self.options.timeout > 0 else None
            ctx = build_context(network=net, locale=self.lang, only_ids=self.options.only_ids,
                                deadline=deadline, verbose=True)
        ctx.appid = self.options.appid
        ctx.symptom = self.options.symptom
        return ctx

    def _planned_checks(self) -> list[str]:
        only = self.options.only_ids
        return [c.id for c in ALL_CHECKS if (only is None or c.id in only) and (self.network or not c.requires_network)]

    # ------------------------------------------------------------------ sampler

    @work(thread=True, exclusive=True, group="sampler")
    def sampler_loop(self) -> None:
        worker = get_current_worker()
        sampler = Sampler(self.options.sys_root, self.options.proc_root)
        while not worker.is_cancelled and not self._stop.is_set():
            sample = sampler.sample(processes=12 if self._monitor_visible else 0)
            if not self._post(self._on_sample, sample):
                return
            self._wake.wait(self.options.sample_interval)
            self._wake.clear()

    def _on_sample(self, sample: Sample) -> None:
        self.last_sample = sample
        self.main.query_one(OverviewPane).show_battery(sample)
        self.main.query_one(MonitorPane).show_sample(sample)
        bits = []
        battery = sample.battery
        if battery and battery.percent is not None:
            mark = "ϟ" if battery.charging or sample.on_ac else "▮"
            text = f"[{fmt.battery_color(battery.percent)}]{mark} {battery.percent:.0f}%[/]"
            if battery.power_w is not None:
                text += f" {battery.power_w:.1f} W"
            bits.append(text)
        if sample.apu_temp_c is not None:
            bits.append(f"[{fmt.temp_color(sample.apu_temp_c)}]{sample.apu_temp_c:.0f}°C[/]")
        net = "[$success]●[/] " + self.t("tui.network.on") if self.network else "[$text-muted]○[/] " + self.t("tui.network.off")
        bits.append(net)
        self.main.query_one("#top-live", Static).update("   ".join(bits))

    @on(TabbedContent.TabActivated, "#main")
    def _tab_changed(self, event: TabbedContent.TabActivated) -> None:
        self._monitor_visible = event.pane.id == "monitor"
        if self._monitor_visible:
            self._wake.set()

    # ------------------------------------------------------------------ scan

    def start_scan(self, after_fix: tuple[list[FixPlan], list[FixResult]] | None = None) -> bool:
        if self._scanning:
            self.notify(self.t("tui.notify.busy"), severity="warning")
            return False
        self._scanning = True
        self.main.query_one(OverviewPane).scan_started(len(self._planned_checks()))
        self.run_scan(after_fix)
        return True

    @work(thread=True, exclusive=True, group="scan")
    def run_scan(self, after_fix: tuple[list[FixPlan], list[FixResult]] | None) -> None:
        planned = self._planned_checks()
        positions = {cid: index for index, cid in enumerate(planned)}

        def progress(check_id: str) -> None:
            if check_id in positions:
                self._post(self._on_progress, positions[check_id] + 1, len(planned),
                           translate(self.lang, f"title.{check_id}"))

        try:
            ctx = self._make_context()
            ctx.progress = progress
            report = diagnose(ctx)
            if after_fix is not None:
                fixed_plans, results = after_fix
                verify_results(fixed_plans, results, report)
                report.repair_results = results
            plans = collect_plans(ctx, report)
        except Exception as exc:  # noqa: BLE001 — keep the dashboard alive and show the failure
            self._post(self._on_scan_failed, str(exc))
            return
        self._post(self._on_scan_done, ctx, report, plans, after_fix is not None)

    def _on_progress(self, done: int, total: int, title: str) -> None:
        self.main.query_one(OverviewPane).scan_progress(done, total, title)

    def _on_scan_failed(self, error: str) -> None:
        self._scanning = False
        self.notify(translate(self.lang, "ui.internal_error", exc=error), severity="error", timeout=10)

    def _on_scan_done(self, ctx: DiagnosticContext, report: Report, plans: list[FixPlan], after_fix: bool) -> None:
        self._scanning = False
        self.ctx, self.report, self.plans = ctx, report, plans
        self.main.query_one(OverviewPane).show_report(report, plans)
        self.main.query_one(ChecksPane).show_report(report, plans)
        fixes = self.main.query_one(FixesPane)
        fixes.show_plans(plans)
        if after_fix:
            fixes.show_results(report.repair_results)
            self._announce(report.repair_results)
        sanitizer = Sanitizer(user=ctx.user, home=str(ctx.home), hostname=ctx.hostname)
        self.main.query_one(ReportPane).show_markdown(render_markdown(report, sanitizer))
        tabs = self.main.query_one("#main", TabbedContent)
        tally = fmt.counts(report)
        issues = tally[Status.FAIL] + tally[Status.WARNING]
        checks_label = self.t("tui.tab.checks")
        if issues:
            color = "$error" if tally[Status.FAIL] else "$warning"
            checks_label += f" [{color}]{issues}[/]"
        tabs.get_tab("checks").label = checks_label
        fixes_label = self.t("tui.tab.fixes") + (f" [$warning]{len(plans)}[/]" if plans else "")
        tabs.get_tab("fixes").label = fixes_label

    # ------------------------------------------------------------------ storage

    @work(thread=True, exclusive=True, group="storage")
    def load_storage(self) -> None:
        try:
            ctx = self._make_context(network=False)
            report = storage.scan(ctx)
        except Exception as exc:  # noqa: BLE001 — storage is optional; never break the dashboard
            self._post(self.notify, str(exc))
            return
        if not self._post(self._on_storage, report) or not self.options.measure_storage:
            return
        last = [0.0]

        def progress(done: int, total: int, _label: str) -> None:
            now = time.monotonic()
            if now - last[0] > 0.25:
                last[0] = now
                self._post(self.main.query_one(GamesPane).measure_progress, done, total)

        storage.measure_report(report, deadline=time.monotonic() + 180, progress=progress)
        self._post(self._on_storage, report)

    def _on_storage(self, report: storage.StorageReport) -> None:
        self.storage = report
        self.main.query_one(GamesPane).set_storage(report)
        self.main.query_one(OverviewPane).show_storage(report)
        tabs = self.main.query_one("#main", TabbedContent)
        tabs.get_tab("games").label = f"{self.t('tui.tab.games')} [$text-muted]{len(report.games)}[/]"

    # ------------------------------------------------------------------ messages

    def on_overview_pane_open_check(self, message: OverviewPane.OpenCheck) -> None:
        self.action_tab("checks")
        self.main.query_one(ChecksPane).select(message.check_id)

    def on_games_pane_open_game(self, message: GamesPane.OpenGame) -> None:
        self.push_screen(GameScreen(self.lang, message.game))

    def on_fix_requested(self, message: FixRequested) -> None:
        self.request_fix(message.plans)

    def request_fix(self, plans: list[FixPlan]) -> None:
        if not plans:
            self.notify(self.t("tui.notify.no_fixes"))
            return
        if self._scanning:
            self.notify(self.t("tui.notify.busy"), severity="warning")
            return

        def confirmed(ok: bool | None) -> None:
            if ok:
                self.apply_fixes(plans)

        self.push_screen(ConfirmFixScreen(self.lang, plans), confirmed)

    def apply_fixes(self, plans: list[FixPlan]) -> None:
        if self.ctx is None or self._scanning:
            self.notify(self.t("tui.notify.busy"), severity="warning")
            return
        self._last_fix = list(plans)
        try:
            with self.suspend():
                results = self._apply_in_terminal(plans)
        except SuspendNotSupported:
            results = apply_plans(self.ctx, plans, self.options.executor)
        self.main.query_one(FixesPane).show_verifying()
        self.start_scan(after_fix=(plans, results))

    def _apply_in_terminal(self, plans: list[FixPlan]) -> list[FixResult]:
        assert self.ctx is not None
        print(f"\n\033[1mDeckDoctor\033[0m  {self.t('tui.fixes.running')}\n", flush=True)

        def progress(phase: str, plan: FixPlan) -> None:
            print("  " + translate(self.lang, f"fix.progress.{phase}", title=plan.title), flush=True)

        results = apply_plans(self.ctx, plans, self.options.executor, progress=progress)
        print()
        for item in results:
            print(("  \033[32m✔\033[0m " if item.ok else "  \033[31m✖\033[0m ") + item.finding, flush=True)
        try:
            input("\n" + self.t("tui.fixes.return"))
        except EOFError:
            pass
        return results

    def on_report_pane_save(self, message: ReportPane.Save) -> None:
        report, ctx = self.report, self.ctx
        if report is None or ctx is None:
            return
        sanitizer = Sanitizer(user=ctx.user, home=str(ctx.home), hostname=ctx.hostname)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        folder = self.options.report_dir or ctx.home
        path = folder / f"deckdoctor-report-{stamp}.{'json' if message.as_json else 'md'}"
        if message.as_json:
            body = json.dumps(sanitizer.apply_obj(report.to_dict()), indent=2, ensure_ascii=False)
        else:
            body = render_markdown(report, sanitizer)
        pane = self.main.query_one(ReportPane)
        try:
            path.write_text(body, encoding="utf-8")
        except OSError as exc:
            pane.saved(f"[$error]{self.t('tui.report.failed', error=exc)}[/]")
            return
        pane.saved(self.t("tui.report.saved", path=path))
        self.notify(self.t("tui.report.saved", path=path))

    # ------------------------------------------------------------------ actions

    def action_tab(self, name: str) -> None:
        if name in TABS:
            self.main.query_one("#main", TabbedContent).active = name

    def action_rescan(self) -> None:
        if self.start_scan():
            self.notify(self.t("tui.notify.rescan"))
            self.load_storage()

    def action_toggle_network(self) -> None:
        if self._scanning:
            self.notify(self.t("tui.notify.busy"), severity="warning")
            return
        self.network = not self.network
        self.notify(self.t("tui.notify.network_on" if self.network else "tui.notify.network_off"))
        if self.last_sample is not None:
            self._on_sample(self.last_sample)
        self.start_scan()

    def _announce(self, results: list[FixResult]) -> None:
        titles = {plan.id: plan.title for plan in self._last_fix}
        good = [titles.get(item.id, item.id) for item in results if item.ok and item.verified is not False]
        bad = [item for item in results if not item.ok or item.verified is False]
        if good:
            self.notify(self.t("tui.notify.fixed", titles=", ".join(good)), timeout=8)
        if bad:
            self.notify(self.t("tui.notify.fix_partial", count=len(bad)), severity="error", timeout=12)

    def action_fix(self) -> None:
        tabs = self.main.query_one("#main", TabbedContent)
        if tabs.active == "checks":
            selected = self.main.query_one(ChecksPane).selected_plans()
            if selected:
                self.request_fix(selected)
                return
        self.request_fix(list(self.plans))

    def action_problems(self) -> None:
        self.action_tab("checks")
        self.main.query_one(ChecksPane).toggle_filter()

    def action_sort(self) -> None:
        self.action_tab("games")
        self.main.query_one(GamesPane).cycle_sort()

    def action_help(self) -> None:
        self.push_screen(HelpScreen(self.lang))
