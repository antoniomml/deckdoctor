"""One widget per dashboard tab. Panes only render; the app owns data and workers."""
from __future__ import annotations

from typing import Any

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.coordinate import Coordinate
from textual.markup import escape
from textual.message import Message
from textual.widgets import Button, DataTable, Markdown, OptionList, ProgressBar, Static, TabbedContent, TabPane
from textual.widgets.option_list import Option

from deckdoctor.device import Device
from deckdoctor.i18n import translate
from deckdoctor.models import CheckResult, FixPlan, FixResult, Report, Status
from deckdoctor.renderer import CHECK_GROUPS
from deckdoctor.sensors import Sample
from deckdoctor.storage import Game, StorageReport
from deckdoctor.tui import format as fmt
from deckdoctor.tui.widgets import Graph, Meter, threshold_color


class _Localized:
    locale: str

    def t(self, key: str, **kwargs: object) -> str:
        return translate(self.locale, key, **kwargs)


class FixRequested(Message):
    """Any pane asks the app to confirm and apply these plans."""

    def __init__(self, plans: list[FixPlan]) -> None:
        super().__init__()
        self.plans = plans


def plans_for(plans: list[FixPlan], check_id: str) -> list[FixPlan]:
    return [plan for plan in plans if check_id in plan.related_checks]


def _card(widget: Any, title: str) -> Any:
    widget.add_class("card")
    widget.border_title = title
    return widget


# --------------------------------------------------------------------------- overview


class OverviewPane(_Localized, Vertical):
    class OpenCheck(Message):
        def __init__(self, check_id: str) -> None:
            super().__init__()
            self.check_id = check_id

    def __init__(self, locale: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.locale = locale
        self._device: Device | None = None
        self._report: Report | None = None
        self._plans: list[FixPlan] = []
        self._os_line = ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="ov-columns"):
            with Vertical(id="ov-left"):
                with _card(Vertical(id="health-card"), self.t("tui.health")):
                    yield Static(id="verdict")
                    yield Static(id="verdict-detail")
                    yield Static(id="tally")
                    yield Button("", id="fix-all", variant="warning")
                    yield ProgressBar(id="scan-progress", show_eta=False, show_percentage=True)
                    yield Static(id="scan-label", classes="hint")
                yield _card(Static(id="device-card"), self.t("tui.device"))
                yield _card(Vertical(id="storage-card"), self.t("tui.storage"))
                with _card(Vertical(id="battery-card"), self.t("tui.battery")):
                    yield Static(id="battery-head")
                    yield Meter(id="battery-meter")
                    yield Static(id="battery-body")
            with _card(Vertical(id="ov-right"), self.t("tui.attention")):
                yield OptionList(id="attention")
                yield Static(self.t("tui.attention.hint"), classes="hint", id="attention-hint")

    def on_mount(self) -> None:
        self.query_one("#fix-all", Button).display = False
        self.scan_started(0)

    # -- scan lifecycle
    def scan_started(self, total: int) -> None:
        self.query_one("#verdict", Static).update(f"[b $primary]{self.t('tui.verdict.scanning')}[/]")
        self.query_one("#verdict-detail", Static).update("")
        bar = self.query_one("#scan-progress", ProgressBar)
        bar.display = True
        bar.update(total=total or None, progress=0)
        self.query_one("#scan-label", Static).display = True
        self.query_one("#fix-all", Button).display = False

    def scan_progress(self, done: int, total: int, title: str) -> None:
        self.query_one("#scan-progress", ProgressBar).update(total=total, progress=done - 1)
        self.query_one("#scan-label", Static).update(escape(self.t("tui.progress", title=title, done=done, total=total)))

    def show_report(self, report: Report, plans: list[FixPlan]) -> None:
        self._report = report
        self._plans = plans
        button = self.query_one("#fix-all", Button)
        if len(plans) == 1:
            button.label = f"🔧 {self.t('tui.fixes.one')}: {plans[0].title}"
        elif plans:
            button.label = "🔧 " + self.t("tui.fixes.all", count=len(plans))
        button.display = bool(plans)
        self.query_one("#scan-progress", ProgressBar).display = False
        self.query_one("#scan-label", Static).display = False
        state, count, color = fmt.verdict(report)
        tally = fmt.counts(report)
        headline = {
            "ok": self.t("tui.verdict.ok"),
            "limited": self.t("tui.verdict.ok"),
            "attention": self.t("tui.verdict.attention", count=count),
            "problem": self.t("tui.verdict.problem", count=count),
            "incomplete": self.t("tui.verdict.incomplete"),
        }[state]
        verified = tally[Status.PASS] + tally[Status.INFO]
        detail = {
            "ok": self.t("tui.verdict.ok.detail", count=verified),
            "limited": self.t("tui.verdict.limited.detail", count=count),
            "attention": self.t("tui.verdict.attention.detail"),
            "problem": (self.t("tui.verdict.warnings", count=tally[Status.WARNING]) + " " if tally[Status.WARNING] else "")
            + self.t("tui.verdict.problem.detail"),
            "incomplete": self.t("tui.verdict.incomplete.detail"),
        }[state]
        mark = {"ok": "✔", "limited": "✔", "attention": "▲", "problem": "✖", "incomplete": "▲"}[state]
        self.query_one("#verdict", Static).update(f"[b {color}]{mark}  {escape(headline)}[/]")
        self.query_one("#verdict-detail", Static).update(f"[$text-muted]{escape(detail)}[/]")
        parts = []
        for status in fmt.STATUS_ORDER:
            if tally[status]:
                key = f"tui.count.{status.value}"
                if tally[status] == 1 and self.t(key + ".one") != key + ".one":
                    key += ".one"
                parts.append(f"{fmt.glyph(status)} {tally[status]} {self.t(key)}")
        self.query_one("#tally", Static).update("  ".join(parts))
        self._fill_attention(report)
        self._render_device()

    def _fill_attention(self, report: Report) -> None:
        options: list[Option | None] = []
        order = {Status.FAIL: 0, Status.WARNING: 1, Status.UNKNOWN: 2}
        problems = sorted((r for r in report.results if r.status in order), key=lambda r: order[r.status])
        for item in problems:
            options.append(Option(self._issue_prompt(item), id=f"check:{item.check_id}"))
            options.append(None)
        for index, diag in enumerate(d for d in report.diagnoses if d.fact_kind == "likely"):
            text = f"[$secondary]◆ {self.t('tui.likely')}[/]  [b]{escape(diag.title)}[/b]\n{escape(diag.summary)}"
            if diag.recommendation:
                text += f"\n[$accent]→ {escape(diag.recommendation)}[/]"
            options.append(Option(text, id=f"diag:{index}"))
            options.append(None)
        notes = [r for r in report.results if r.status == Status.INFO and r.extra.get("compact_note")]
        if notes:
            options.append(Option(f"[b $text-muted]{self.t('tui.notes')}[/]", disabled=True))
            for item in notes:
                options.append(Option(self._issue_prompt(item), id=f"check:{item.check_id}"))
                options.append(None)
        if not problems:
            options.insert(0, Option(f"[$success]✔ {self.t('tui.attention.none')}[/]", disabled=True))
            options.insert(1, None)
        while options and options[-1] is None:
            options.pop()
        attention = self.query_one("#attention", OptionList)
        attention.clear_options()
        attention.add_options(options)

    def _issue_prompt(self, item: CheckResult) -> str:
        text = f"{fmt.glyph(item.status)} [b]{escape(item.title)}[/b]"
        fixable = bool(plans_for(self._plans, item.check_id))
        if fixable:
            text += f"   [b $success]🔧 {self.t('tui.fixes.fixable')}[/]"
        text += f"\n{escape(item.finding)}"
        if fixable:
            text += f"\n[$accent]→ {escape(self.t('tui.fixes.press'))}[/]"
        elif item.recommendation:
            text += f"\n[$accent]→ {escape(item.recommendation)}[/]"
        return text

    @on(Button.Pressed, "#fix-all")
    def _fix_all(self) -> None:
        if self._plans:
            self.post_message(FixRequested(list(self._plans)))

    @on(OptionList.OptionSelected, "#attention")
    def _open(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option.id or ""
        if option_id.startswith("check:"):
            self.post_message(self.OpenCheck(option_id.partition(":")[2]))

    # -- cards
    def show_device(self, device: Device, os_line: str) -> None:
        self._device = device
        self._os_line = os_line
        self._render_device()

    def _render_device(self) -> None:
        device = self._device
        if device is None:
            return
        rows = [(self.t("tui.device.model"), f"[b]{escape(device.model)}[/b]")]
        if device.apu:
            rows.append((self.t("tui.device.apu"), escape(device.apu)))
        report = self._report
        by = {r.check_id: r for r in report.results} if report else {}
        osver = by.get("SYS-OS-VERSION")
        os_text = osver.finding if osver and osver.status in {Status.PASS, Status.INFO} else self._os_line
        if os_text:
            rows.append((self.t("tui.device.os"), escape(os_text)))
        from deckdoctor.device import kernel_release

        rows.append((self.t("tui.device.kernel"), escape(kernel_release())))
        steam = by.get("STEAM-CLIENT")
        if steam and steam.status in {Status.PASS, Status.INFO, Status.WARNING}:
            rows.append((self.t("tui.device.steam"), escape(steam.finding)))
        if report is not None:
            decky = report.facts.get("decky_version")
            rows.append((self.t("tui.device.decky"), escape(str(decky)) if decky else f"[$text-muted]{self.t('tui.decky.missing')}[/]"))
        width = max(len(label) for label, _ in rows)
        self.query_one("#device-card", Static).update(
            "\n".join(f"[$text-muted]{label:<{width}}[/]  {value}" for label, value in rows))

    def show_storage(self, storage: StorageReport) -> None:
        widgets: list[Any] = []
        for lib in storage.libraries:
            label = self.t("tui.kind." + lib.kind)
            if not lib.accessible or not lib.total:
                widgets.append(Static(f"[b]{label}[/b]  [$error]✖[/] [$text-muted]{escape(lib.path)}[/]"))
                continue
            used = (lib.total - (lib.free or 0)) / lib.total
            free = self.t("tui.storage.free", free=fmt.size(lib.free), total=fmt.size(lib.total))
            games = self.t("tui.storage.games", count=lib.game_count, size=fmt.size(lib.games_bytes))
            widgets.append(Static(f"[b]{label}[/b]  {free}  [$text-muted]· {games}[/]"))
            widgets.append(Meter(used, fmt.hex_of(fmt.level_color(used, warn=0.85, bad=0.95)), classes="spaced"))
        notes = []
        if storage.leftovers:
            notes.append(f"[$warning]▲[/] {self.t('tui.storage.leftovers', size=fmt.size(storage.leftover_bytes) if storage.measured else '…')}")
        pending = [g for g in storage.games if g.update_pending]
        if pending:
            notes.append(f"[$warning]▲[/] {self.t('tui.storage.updates', count=len(pending), size=fmt.size(storage.pending_update_bytes))}")
        if notes:
            widgets.append(Static("\n".join(notes)))
        box = self.query_one("#storage-card", Vertical)
        box.remove_children()
        box.mount_all(widgets or [Static("—")])

    def show_battery(self, sample: Sample) -> None:
        battery = sample.battery
        head = self.query_one("#battery-head", Static)
        meter = self.query_one("#battery-meter", Meter)
        body = self.query_one("#battery-body", Static)
        if battery is None:
            head.update(f"[$text-muted]{self.t('tui.battery.none')}[/]")
            meter.display = False
            body.display = False
            return
        status = battery.status.lower().replace(" ", "_")
        state = self.t(f"tui.battery.{status}") if status in {"charging", "discharging", "full", "not_charging"} else battery.status
        pct = battery.percent
        color = fmt.battery_color(pct)
        line = f"[b {color}]{pct:.0f}%[/]  {escape(state)}" if pct is not None else escape(state)
        if battery.power_w is not None:
            line += f"  ·  {self.t('tui.battery.draw')} [b]{battery.power_w:.1f} W[/b]"
        if battery.hours_left is not None:
            key = "tui.battery.to_full" if battery.charging else "tui.battery.left"
            line += "  ·  " + self.t(key, time=fmt.duration(battery.hours_left))
        head.update(line)
        meter.set((pct or 0) / 100 if pct is not None else None, fmt.hex_of(color))
        extra = []
        if battery.health_percent is not None:
            hcolor = "$success" if battery.health_percent >= 80 else "$warning" if battery.health_percent >= 70 else "$error"
            extra.append(f"{self.t('tui.battery.health')} [{hcolor}]{battery.health_percent:.0f}%[/]")
        if battery.full_wh and battery.design_wh:
            extra.append(f"{battery.full_wh:.1f}/{battery.design_wh:.1f} Wh")
        if battery.cycles:
            extra.append(f"{battery.cycles} {self.t('tui.battery.cycles')}")
        if sample.charger_w:
            extra.append(f"{self.t('tui.battery.charger')} {sample.charger_w:.0f} W")
        if battery.charge_limit:
            extra.append(f"{self.t('tui.battery.limit')} {battery.charge_limit}%")
        if battery.temp_c is not None:
            extra.append(f"{battery.temp_c:.0f} °C")
        body.update("[$text-muted]" + "  ·  ".join(extra) + "[/]" if extra else "")


# --------------------------------------------------------------------------- checks


class ChecksPane(_Localized, Horizontal):
    def __init__(self, locale: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.locale = locale
        self.report: Report | None = None
        self.plans: list[FixPlan] = []
        self.problems_only = False
        self._pending_select: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="checks-side"):
            yield Static(self.t("tui.checks.all"), id="checks-filter", classes="hint")
            yield OptionList(id="check-list")
        with _card(VerticalScroll(id="check-detail"), self.t("tui.detail.finding")):
            with Vertical(id="check-fix-box"):
                yield Static(self.t("tui.fixes.check_hint"), classes="hint")
                yield Button("", id="check-fix", variant="warning")
            yield Static(self.t("tui.checks.empty"), id="detail-body")

    def on_mount(self) -> None:
        self.query_one("#check-fix-box").display = False

    def show_report(self, report: Report, plans: list[FixPlan] | None = None) -> None:
        self.report = report
        self.plans = plans or []
        self._rebuild()

    def toggle_filter(self) -> None:
        self.problems_only = not self.problems_only
        self.query_one("#checks-filter", Static).update(self.t("tui.checks.filter" if self.problems_only else "tui.checks.all"))
        self._rebuild()

    def _visible(self, item: CheckResult) -> bool:
        if not self.problems_only:
            return True
        return item.status in {Status.FAIL, Status.WARNING, Status.UNKNOWN}

    def _rebuild(self) -> None:
        report = self.report
        listing = self.query_one("#check-list", OptionList)
        current = listing.highlighted_option.id if listing.highlighted_option else None
        listing.clear_options()
        if report is None:
            return
        by = {r.check_id: r for r in report.results}
        grouped: list[tuple[str, list[str]]] = [(self.t(key), list(ids)) for key, ids in CHECK_GROUPS]
        known = {cid for _, ids in CHECK_GROUPS for cid in ids}
        others = [r.check_id for r in report.results if r.check_id not in known]
        if others:
            grouped.append(("…", others))
        scope = report.facts.get("scope")
        options: list[Option | None] = []
        for label, ids in grouped:
            rows = [by[cid] for cid in ids if cid in by and self._visible(by[cid])
                    and not (isinstance(scope, list) and cid not in scope)]
            if not rows:
                continue
            if options:
                options.append(None)
            options.append(Option(f"[b $secondary]{escape(label)}[/]", disabled=True))
            for item in rows:
                options.append(Option(f"{fmt.glyph(item.status)} {escape(item.title)}", id=item.check_id))
        listing.add_options(options)
        target = self._pending_select or current
        self._pending_select = None
        if target and self._index_of(target) is not None:
            listing.highlighted = self._index_of(target)
        else:
            first = next((i for i in range(listing.option_count) if not listing.get_option_at_index(i).disabled), None)
            listing.highlighted = first
        self._render_detail()

    def _index_of(self, check_id: str) -> int | None:
        listing = self.query_one("#check-list", OptionList)
        try:
            return listing.get_option_index(check_id)
        except Exception:  # noqa: BLE001 — OptionDoesNotExist differs between Textual versions
            return None

    def select(self, check_id: str) -> None:
        if self.problems_only and self.report:
            item = next((r for r in self.report.results if r.check_id == check_id), None)
            if item and not self._visible(item):
                self.toggle_filter()
        index = self._index_of(check_id)
        listing = self.query_one("#check-list", OptionList)
        if index is None:
            self._pending_select = check_id
            return
        listing.highlighted = index
        listing.focus()
        self._render_detail()

    def selected_plans(self) -> list[FixPlan]:
        option = self.query_one("#check-list", OptionList).highlighted_option
        if option is None or option.id is None:
            return []
        return plans_for(self.plans, option.id)

    @on(Button.Pressed, "#check-fix")
    def _fix(self) -> None:
        fixes = self.selected_plans()
        if fixes:
            self.post_message(FixRequested(fixes))

    @on(OptionList.OptionHighlighted, "#check-list")
    def _highlighted(self) -> None:
        self._render_detail()

    def _render_detail(self) -> None:
        body = self.query_one("#detail-body", Static)
        listing = self.query_one("#check-list", OptionList)
        option = listing.highlighted_option
        fix_box = self.query_one("#check-fix-box")
        fix_box.display = False
        if self.report is None or option is None or option.id is None:
            self.query_one("#check-detail").border_title = self.t("tui.detail.finding")
            body.update(self.t("tui.checks.select") if self.report else self.t("tui.checks.empty"))
            return
        item = next((r for r in self.report.results if r.check_id == option.id), None)
        if item is None:
            return
        status_label = self.t(f"tui.status.{item.status.value}")
        color = fmt.STATUS_GLYPH[item.status][1]
        self.query_one("#check-detail").border_title = escape(item.title)
        fixes = self.selected_plans()
        if fixes:
            label = self.t("tui.fixes.one") if len(fixes) == 1 else self.t("tui.fixes.all", count=len(fixes))
            self.query_one("#check-fix", Button).label = f"🔧 {label}: {fixes[0].title}" if len(fixes) == 1 else f"🔧 {label}"
            fix_box.display = True
        lines = [f"[b {color}]{fmt.STATUS_GLYPH[item.status][0]} {status_label}[/]   [$text-muted]{item.check_id}[/]", ""]
        lines.append(escape(item.finding))
        if item.explanation and item.explanation != item.finding:
            lines += ["", f"[$text-muted]{self.t('tui.detail.why')}[/]", escape(item.explanation)]
        todo = self.t("tui.fixes.press") if fixes else item.recommendation
        if todo:
            lines += ["", f"[$text-muted]{self.t('tui.detail.todo')}[/]", f"[$accent]→ {escape(todo)}[/]"]
        if item.evidence:
            lines += ["", f"[$text-muted]{self.t('tui.detail.evidence')}[/]"]
            lines += [f"[dim]{escape(row)}[/]" for row in item.evidence[:40]]
        lines += ["", f"[$text-muted]{self.t('tui.detail.source')}: {item.source.value}[/]"]
        body.update("\n".join(lines))


# --------------------------------------------------------------------------- monitor


class MetricCard(Vertical):
    def __init__(self, title: str, graph: Graph, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.add_class("metric")
        self.border_title = title
        self.graph = graph
        self.graph.add_class("metric-graph")

    def compose(self) -> ComposeResult:
        yield Static("…", classes="metric-value")
        yield self.graph

    def set(self, value: float | None, text: str, sub: str = "", *, color: str = "$text") -> None:
        if value is not None:
            self.graph.push(value)
        suffix = f"  [$text-muted]{escape(sub)}[/]" if sub else ""
        self.query_one(".metric-value", Static).update(f"[b {color}]{escape(text)}[/]{suffix}")


_METRICS = ("cpu", "cpu_freq", "gpu", "gpu_freq", "power", "temp", "fan", "ssd", "draw", "battery", "memory", "swap")
_LOAD = threshold_color(85, 97)
_TEMP = threshold_color(85, 95)


def _graph(key: str) -> Graph:
    """Fixed scales keep graphs comparable over time instead of auto-zooming noise."""
    if key in {"cpu", "gpu", "swap"}:
        return Graph(high=100, color=_LOAD)
    if key == "memory":
        return Graph(high=100, color=threshold_color(85, 95))
    if key == "battery":
        return Graph(high=100, color=lambda v: fmt.hex_of(fmt.battery_color(v)))
    if key in {"temp", "ssd"}:
        return Graph(low=30, high=100, color=_TEMP)
    if key == "fan":
        return Graph(high=7000)
    if key in {"cpu_freq", "gpu_freq"}:
        return Graph(floor=1000)
    return Graph(floor=15)


class MonitorPane(_Localized, VerticalScroll):
    def __init__(self, locale: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.locale = locale

    def compose(self) -> ComposeResult:
        yield Static(self.t("tui.monitor.note"), classes="hint", id="monitor-note")
        with Grid(id="metrics"):
            for key in _METRICS:
                yield MetricCard(self.t(f"tui.monitor.{key}"), _graph(key), id=f"m-{key}")
        with _card(Vertical(id="proc-card"), self.t("tui.monitor.processes")):
            yield DataTable(id="proc-table", cursor_type="none", zebra_stripes=True, show_cursor=False)

    def on_mount(self) -> None:
        table = self.query_one("#proc-table", DataTable)
        table.add_column(self.t("tui.monitor.col.process"), key="name", width=28)
        table.add_column(self.t("tui.monitor.col.cpu"), key="cpu", width=8)
        table.add_column(self.t("tui.monitor.col.memory"), key="mem", width=10)

    def _card(self, key: str) -> MetricCard:
        return self.query_one(f"#m-{key}", MetricCard)

    def show_sample(self, s: Sample) -> None:
        na = self.t("tui.monitor.na")

        def pct(value: float | None) -> str:
            return f"{value:.0f}%" if value is not None else na

        self._card("cpu").set(s.cpu_percent, pct(s.cpu_percent),
                              f"load {s.load[0]:.2f}" if s.load else "",
                              color=fmt.level_color((s.cpu_percent or 0) / 100))
        self._card("cpu_freq").set(s.cpu_freq_mhz, f"{s.cpu_freq_mhz:.0f} MHz" if s.cpu_freq_mhz else na)
        self._card("gpu").set(s.gpu_percent, pct(s.gpu_percent), color=fmt.level_color((s.gpu_percent or 0) / 100))
        vram = ""
        if s.vram_used is not None and s.vram_total:
            vram = f"{self.t('tui.monitor.vram')} {fmt.size(s.vram_used)}/{fmt.size(s.vram_total)}"
        self._card("gpu_freq").set(s.gpu_freq_mhz, f"{s.gpu_freq_mhz:.0f} MHz" if s.gpu_freq_mhz is not None else na, vram)
        power_sub = self.t("tui.monitor.tdp", watts=f"{s.tdp_limit_w:.0f}") if s.tdp_limit_w else ""
        if s.tdp_limit_w:
            self._card("power").graph.high = s.tdp_limit_w
        ratio = (s.apu_power_w / s.tdp_limit_w) if s.apu_power_w is not None and s.tdp_limit_w else None
        self._card("power").set(s.apu_power_w, f"{s.apu_power_w:.1f} W" if s.apu_power_w is not None else na, power_sub,
                                color=fmt.level_color(ratio, warn=0.85, bad=0.98))
        temp = s.apu_temp_c
        self._card("temp").set(temp, f"{temp:.0f} °C" if temp is not None else na, color=fmt.temp_color(temp))
        self._card("fan").set(float(s.fan_rpm) if s.fan_rpm is not None else None,
                              f"{s.fan_rpm} RPM" if s.fan_rpm is not None else na)
        ssd_sub = f"max {s.nvme_temp_max_c:.0f} °C" if s.nvme_temp_max_c else ""
        self._card("ssd").set(s.nvme_temp_c, f"{s.nvme_temp_c:.0f} °C" if s.nvme_temp_c is not None else na, ssd_sub,
                              color=fmt.temp_color(s.nvme_temp_c))
        battery = s.battery
        draw = battery.power_w if battery else None
        sub = ""
        if battery and battery.hours_left is not None:
            key = "tui.battery.to_full" if battery.charging else "tui.battery.left"
            sub = self.t(key, time=fmt.duration(battery.hours_left))
        self._card("draw").set(draw, f"{draw:.1f} W" if draw is not None else na, sub)
        bpct = battery.percent if battery else None
        bsub = ""
        if battery and battery.health_percent is not None:
            bsub = f"{self.t('tui.battery.health')} {battery.health_percent:.0f}%"
        self._card("battery").set(bpct, pct(bpct), bsub, color=fmt.battery_color(bpct))
        mem = s.mem_used_percent
        mem_sub = f"{fmt.size((s.mem_total or 0) - (s.mem_available or 0))}/{fmt.size(s.mem_total)}" if s.mem_total else ""
        self._card("memory").set(mem, pct(mem), mem_sub, color=fmt.level_color((mem or 0) / 100, warn=0.85, bad=0.95))
        swap = s.swap_used
        swap_pct = 100.0 * swap / s.swap_total if swap is not None and s.swap_total else None
        self._card("swap").set(swap_pct, fmt.size(swap) if swap is not None else na,
                               f"/ {fmt.size(s.swap_total)}" if s.swap_total else "")
        if s.processes:
            table = self.query_one("#proc-table", DataTable)
            table.clear()
            for proc in s.processes:
                name = proc.name if proc.count == 1 else f"{proc.name} ×{proc.count}"
                table.add_row(Text(name), Text(f"{proc.cpu_percent:.1f}%", justify="right"),
                              Text(fmt.size(proc.rss_bytes), justify="right"))


# --------------------------------------------------------------------------- games

_SORTS = ("size", "name", "played", "hours", "shaders", "prefix")


class GamesPane(_Localized, Vertical):
    class OpenGame(Message):
        def __init__(self, game: Game) -> None:
            super().__init__()
            self.game = game

    def __init__(self, locale: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.locale = locale
        self.storage: StorageReport | None = None
        self.sort = "size"

    def compose(self) -> ComposeResult:
        yield Horizontal(id="library-cards")
        yield Static(self.t("tui.games.loading"), id="games-status", classes="hint")
        with TabbedContent(id="games-tabs"):
            with TabPane(self.t("tui.games.installed", count="…"), id="games-installed"):
                yield DataTable(id="games-table", cursor_type="row", zebra_stripes=True)
            with TabPane(self.t("tui.games.leftovers", size="…"), id="games-leftovers"):
                yield Static(self.t("tui.left.note"), classes="note", id="leftover-note")
                yield DataTable(id="leftovers-table", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        games = self.query_one("#games-table", DataTable)
        for key, col in (("name", "name"), ("where", "library"), ("size", "size"), ("prefix", "prefix"),
                         ("shaders", "shaders"), ("proton", "proton"), ("hours", "hours"), ("played", "played")):
            games.add_column(self.t(f"tui.games.col.{col}"), key=key)
        left = self.query_one("#leftovers-table", DataTable)
        for key in ("type", "app", "reason", "size", "cloud", "path"):
            left.add_column(self.t(f"tui.left.col.{key}"), key=key)

    def set_storage(self, storage: StorageReport) -> None:
        self.storage = storage
        self._libraries()
        self._fill_games()
        self._fill_leftovers()
        self._status()

    def measure_progress(self, done: int, total: int) -> None:
        self.query_one("#games-status", Static).update(self.t("tui.games.measuring", done=done, total=total))

    def _status(self) -> None:
        if self.storage is None:
            return
        sort_label = self.t(f"tui.games.col.{'size' if self.sort == 'size' else self.sort}")
        text = f"{self.t('tui.games.hint')}   [$text-muted]{self.t('tui.games.sort', column=sort_label)}[/]"
        pending = [g for g in self.storage.games if g.update_pending]
        if pending:
            text += "\n[$warning]▲[/] " + self.t("tui.storage.updates", count=len(pending),
                                                   size=fmt.size(self.storage.pending_update_bytes))
        if not self.storage.measured:
            text = self.t("tui.games.measuring", done=0, total="…")
        self.query_one("#games-status", Static).update(text)

    def _libraries(self) -> None:
        storage = self.storage
        assert storage is not None
        box = self.query_one("#library-cards", Horizontal)
        box.remove_children()
        cards = []
        for lib in storage.libraries:
            title = self.t(f"tui.kind.{lib.kind}")
            if not lib.accessible or not lib.total:
                parts: list[Any] = [Static(f"[$error]✖[/] [$text-muted]{escape(lib.path)}[/]")]
            else:
                used = (lib.total - (lib.free or 0)) / lib.total
                parts = [
                    Meter(used, fmt.hex_of(fmt.level_color(used, warn=0.85, bad=0.95))),
                    Static(self.t("tui.storage.free", free=fmt.size(lib.free), total=fmt.size(lib.total))),
                    Static(f"[$text-muted]{self.t('tui.storage.games', count=lib.game_count, size=fmt.size(lib.games_bytes))}[/]"),
                ]
            cards.append(_card(Vertical(*parts, classes="library-card"), title))
        box.mount_all(cards)

    def _sorted(self) -> list[Game]:
        assert self.storage is not None
        games = list(self.storage.games)
        if self.sort == "name":
            return sorted(games, key=lambda g: g.name.lower())
        if self.sort == "hours":
            return sorted(games, key=lambda g: g.playtime_minutes or 0, reverse=True)
        if self.sort == "played":
            return sorted(games, key=lambda g: g.last_played or 0, reverse=True)
        if self.sort == "shaders":
            return sorted(games, key=lambda g: g.shader_bytes or 0, reverse=True)
        if self.sort == "prefix":
            return sorted(games, key=lambda g: g.prefix_bytes or 0, reverse=True)
        return sorted(games, key=lambda g: g.total_bytes, reverse=True)

    def _fill_games(self) -> None:
        table = self.query_one("#games-table", DataTable)
        selected = None
        if table.row_count and table.cursor_row is not None:
            try:
                selected = table.coordinate_to_cell_key(Coordinate(table.cursor_row, 0)).row_key.value
            except Exception:  # noqa: BLE001 — cursor may point past a shrinking table
                selected = None
        table.clear()
        never = self.t("tui.games.never")
        for game in self._sorted():
            prefix = fmt.size(game.prefix_bytes) if game.prefix_path else "—"
            shaders = fmt.size(game.shader_bytes) if game.shader_path else "—"
            where = self.t(f"tui.kind.{game.library_kind}")
            title = game.name if len(game.name) <= 36 else game.name[:35] + "…"
            name = Text(title, style="bold")
            if game.update_pending:
                name.append(" ▲", style=fmt.PALETTE["warning"])
            muted = fmt.PALETTE["muted"]
            table.add_row(name, where, Text(fmt.size(game.size_on_disk), justify="right"),
                          Text(prefix, justify="right", style="" if game.prefix_path else muted),
                          Text(shaders, justify="right", style="" if game.shader_path else muted),
                          Text(game.proton or self.t("tui.games.native"), style="" if game.proton else muted),
                          Text(fmt.hours(game.playtime_minutes), justify="right", style="" if game.playtime_minutes else muted),
                          Text(fmt.day(game.last_played, never), style="" if game.last_played else muted),
                          key=str(game.appid))
        if selected is not None:
            try:
                table.move_cursor(row=table.get_row_index(selected))
            except Exception:  # noqa: BLE001 — row may be gone after a rescan
                pass
        tabs = self.query_one("#games-tabs", TabbedContent)
        tabs.get_tab("games-installed").label = self.t("tui.games.installed", count=len(self.storage.games if self.storage else []))

    def _fill_leftovers(self) -> None:
        storage = self.storage
        assert storage is not None
        table = self.query_one("#leftovers-table", DataTable)
        table.clear()
        for item in sorted(storage.leftovers, key=lambda i: -(i.size or 0)):
            name = storage.shortcuts.get(item.appid) or str(item.appid)
            if item.cloud_synced:
                cloud = Text("✔ " + self.t("tui.left.cloud.yes"), style=fmt.PALETTE["success"])
            else:
                cloud = Text(self.t("tui.left.cloud.unknown"), style=fmt.PALETTE["muted"])
            table.add_row(self.t(f"tui.left.{item.kind}"), Text(name, style="bold"), self.t(f"tui.left.{item.reason}"),
                          Text(fmt.size(item.size), justify="right"), cloud, Text(item.path, style=fmt.PALETTE["muted"]))
        note = self.t("tui.left.note") if storage.leftovers else self.t("tui.left.none")
        if not storage.all_libraries_accessible:
            note += "\n[$warning]▲ " + self.t("tui.left.missing_library") + "[/]"
        self.query_one("#leftover-note", Static).update(note)
        size = fmt.size(storage.leftover_bytes) if storage.measured else "…"
        tabs = self.query_one("#games-tabs", TabbedContent)
        tabs.get_tab("games-leftovers").label = self.t("tui.games.leftovers", size=size)

    def cycle_sort(self) -> None:
        self.sort = _SORTS[(_SORTS.index(self.sort) + 1) % len(_SORTS)]
        if self.storage is not None:
            self._fill_games()
            self._status()

    @on(DataTable.RowSelected, "#games-table")
    def _open(self, event: DataTable.RowSelected) -> None:
        if self.storage is None:
            return
        appid = int(str(event.row_key.value))
        game = next((g for g in self.storage.games if g.appid == appid), None)
        if game is not None:
            self.post_message(self.OpenGame(game))


# --------------------------------------------------------------------------- fixes


class FixCard(Vertical):
    def __init__(self, plan: FixPlan, body: str, label: str) -> None:
        super().__init__(classes="card fix-card")
        self.plan = plan
        self.border_title = plan.title
        self._body = body
        self._label = label

    def compose(self) -> ComposeResult:
        yield Static(self._body)
        yield Button(self._label, variant="warning", classes="fix-apply")


class FixesPane(_Localized, VerticalScroll):
    def __init__(self, locale: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.locale = locale
        self.plans: list[FixPlan] = []

    def compose(self) -> ComposeResult:
        yield Static(self.t("tui.fixes.intro"), classes="hint", id="fix-intro")
        yield Button("", id="fix-every", variant="warning")
        yield Static(f"[$text-muted]{self.t('tui.fixes.waiting')}[/]", id="fix-empty")
        yield Vertical(id="fix-list")
        yield _card(Static(id="fix-results-body"), self.t("tui.fixes.results"))

    def on_mount(self) -> None:
        self._results_card().display = False
        self.query_one("#fix-every", Button).display = False

    def _results_card(self) -> Static:
        return self.query_one("#fix-results-body", Static)

    def show_plans(self, plans: list[FixPlan]) -> None:
        self.plans = plans
        every = self.query_one("#fix-every", Button)
        every.label = "🔧 " + self.t("tui.fixes.all", count=len(plans))
        every.display = len(plans) > 1
        box = self.query_one("#fix-list", Vertical)
        box.remove_children()
        empty = self.query_one("#fix-empty", Static)
        if not plans:
            empty.update(f"[b $success]✔ {self.t('tui.fixes.none')}[/]\n[$text-muted]{self.t('tui.fixes.none.detail')}[/]")
            empty.display = True
            return
        empty.display = False
        cards = []
        for plan in plans:
            risk = translate(self.locale, f"fix.risk.{plan.risk}")
            risk_color = {"low": "$success", "medium": "$warning"}.get(str(plan.risk), "$error")
            meta = f"[b {risk_color}]● {escape(risk)}[/]"
            if plan.needs_root:
                meta += f"   [$warning]▲ {self.t('tui.fixes.root')}[/]"
            body = "\n".join([
                escape(plan.summary), "", meta, "",
                f"[$text-muted]{self.t('tui.fixes.changes')}[/]  [$accent]{escape(plan.mutation)}[/]",
                f"[$text-muted]{self.t('tui.fixes.undo')}[/]  {escape(plan.reversible)}",
            ])
            cards.append(FixCard(plan, body, "🔧 " + self.t("tui.fixes.apply")))
        box.mount_all(cards)

    def show_verifying(self) -> None:
        card = self._results_card()
        card.display = True
        card.update(f"[$primary]{self.t('tui.fixes.verifying')}[/]")

    def show_results(self, results: list[FixResult]) -> None:
        card = self._results_card()
        card.display = True
        lines = []
        for item in results:
            mark = "[$success]✔[/]" if item.ok and item.verified is not False else "[$error]✖[/]"
            key = "fix.verified" if item.verified is True else "fix.unresolved" if item.verified is False else "fix.unverified"
            lines.append(f"{mark} [b]{escape(item.id)}[/b]  {escape(item.finding)}")
            lines.append(f"   [$text-muted]{escape(translate(self.locale, key))}[/]")
            lines += [f"   [dim]{escape(ev)}[/]" for ev in item.evidence[:4]]
        card.update("\n".join(lines))

    @on(Button.Pressed, ".fix-apply")
    def _apply(self, event: Button.Pressed) -> None:
        card = event.button.parent
        if isinstance(card, FixCard):
            self.post_message(FixRequested([card.plan]))

    @on(Button.Pressed, "#fix-every")
    def _apply_all(self) -> None:
        if self.plans:
            self.post_message(FixRequested(list(self.plans)))


# --------------------------------------------------------------------------- report


class ReportPane(_Localized, Vertical):
    class Save(Message):
        def __init__(self, as_json: bool) -> None:
            super().__init__()
            self.as_json = as_json

    def __init__(self, locale: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.locale = locale

    def compose(self) -> ComposeResult:
        yield Static(self.t("tui.report.intro"), classes="hint")
        with Horizontal(id="report-actions"):
            yield Button(self.t("tui.report.save_md"), id="save-md", variant="primary", disabled=True)
            yield Button(self.t("tui.report.save_json"), id="save-json", disabled=True)
            yield Static("", id="report-saved")
        with VerticalScroll(id="report-scroll", classes="card"):
            yield Markdown(self.t("tui.report.waiting"), id="report-md")

    def show_markdown(self, text: str) -> None:
        self.query_one("#report-md", Markdown).update(text)
        self.query_one("#save-md", Button).disabled = False
        self.query_one("#save-json", Button).disabled = False

    def saved(self, message: str) -> None:
        self.query_one("#report-saved", Static).update(message)

    @on(Button.Pressed, "#save-md")
    def _md(self) -> None:
        self.post_message(self.Save(False))

    @on(Button.Pressed, "#save-json")
    def _json(self) -> None:
        self.post_message(self.Save(True))
