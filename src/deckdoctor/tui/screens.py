from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.markup import escape
from textual.screen import ModalScreen
from textual.widgets import Button, LoadingIndicator, Static

from deckdoctor.i18n import translate
from deckdoctor.models import CheckResult, FixPlan
from deckdoctor.tui import format as fmt

if TYPE_CHECKING:
    from deckdoctor.storage import Game


class _Modal(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "close", show=False), Binding("b", "close", show=False)]

    def __init__(self, locale: str) -> None:
        super().__init__()
        self.locale = locale

    def t(self, key: str, **kwargs: object) -> str:
        return translate(self.locale, key, **kwargs)

    def action_close(self) -> None:
        self.dismiss(False)


class HelpScreen(_Modal):
    BINDINGS = [*_Modal.BINDINGS, Binding("question_mark", "close", show=False), Binding("q", "close", show=False),
                Binding("enter", "close", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box", id="help-box") as box:
            box.border_title = self.t("tui.help.title")
            yield Static(self.t("tui.help.body"), id="help-body")
            yield Button(self.t("tui.key.close"), id="help-close", variant="primary")

    @on(Button.Pressed, "#help-close")
    def _close(self) -> None:
        self.dismiss(False)


class ConfirmFixScreen(_Modal):
    BINDINGS = [*_Modal.BINDINGS, Binding("y", "confirm", show=False), Binding("n", "close", show=False)]

    def __init__(self, locale: str, plans: list[FixPlan]) -> None:
        super().__init__(locale)
        self.plans = plans

    def _describe(self, plan: FixPlan, *, detailed: bool) -> list[str]:
        risk = translate(self.locale, f"fix.risk.{plan.risk}")
        color = {"low": "$success", "medium": "$warning"}.get(str(plan.risk), "$error")
        lines = [f"[b]{escape(plan.title)}[/b]   [{color}]● {escape(risk)}[/]"]
        if detailed:
            lines += ["", escape(plan.summary), ""]
        lines.append(f"[$text-muted]{self.t('tui.fixes.changes')}[/]  [$accent]{escape(plan.mutation)}[/]")
        lines.append(f"[$text-muted]{self.t('tui.fixes.undo')}[/]  {escape(plan.reversible)}")
        return lines

    def compose(self) -> ComposeResult:
        single = len(self.plans) == 1
        lines: list[str] = []
        for plan in self.plans:
            if lines:
                lines.append("")
            lines += self._describe(plan, detailed=single)
        if any(plan.needs_root for plan in self.plans):
            lines += ["", f"[$warning]▲ {self.t('tui.fixes.root')}[/]"]
        lines += ["", f"[$text-muted]{self.t('tui.fixes.confirm.after')}[/]"]
        with Vertical(classes="modal-box", id="confirm-box") as box:
            box.border_title = (self.t("tui.fixes.confirm.title") if single
                                else self.t("tui.fixes.confirm.many", count=len(self.plans)))
            with VerticalScroll(id="confirm-scroll"):
                yield Static("\n".join(lines), id="confirm-body")
            with Horizontal(classes="modal-buttons"):
                yield Button(self.t("tui.fixes.confirm.no"), id="confirm-no")
                yield Button(self.t("tui.fixes.confirm.yes"), id="confirm-yes", variant="warning")

    def on_mount(self) -> None:
        self.query_one("#confirm-no", Button).focus()

    @on(Button.Pressed, "#confirm-yes")
    def action_confirm(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def _no(self) -> None:
        self.dismiss(False)


class GameScreen(_Modal):
    BINDINGS = [*_Modal.BINDINGS, Binding("enter", "close", show=False)]

    def __init__(self, locale: str, game: Game) -> None:
        super().__init__(locale)
        self.game = game

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box", id="game-box") as box:
            box.border_title = escape(self.game.name)
            with VerticalScroll(id="game-scroll"):
                yield Static(self._summary(), id="game-summary")
                yield LoadingIndicator(id="game-loading")
                yield Static("", id="game-check")
            yield Button(self.t("tui.key.close"), id="game-close", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#game-close", Button).focus()
        self._inspect()

    def _row(self, label: str, value: str) -> str:
        return f"[$text-muted]{label:<20}[/] {value}"

    def _summary(self) -> str:
        g = self.game
        never = self.t("tui.games.never")
        rows = [
            self._row(self.t("tui.game.appid"), str(g.appid)),
            self._row(self.t("tui.games.col.library"), f"{self.t('tui.kind.' + g.library_kind)}  [$text-muted]{escape(g.library)}[/]"),
            self._row(self.t("tui.games.col.size"), fmt.size(g.size_on_disk)),
            self._row(self.t("tui.game.prefix"), fmt.size(g.prefix_bytes) if g.prefix_path else self.t("tui.games.native")),
            self._row(self.t("tui.game.shaders"), fmt.size(g.shader_bytes) if g.shader_path else "—"),
            self._row(self.t("tui.game.total"), f"[b]{fmt.size(g.total_bytes)}[/b]"),
            self._row(self.t("tui.games.col.proton"), escape(g.proton or self.t("tui.games.native"))),
            self._row(self.t("tui.games.col.played"), fmt.day(g.last_played, never)),
            self._row(self.t("tui.game.updated"), fmt.day(g.last_updated, never)),
        ]
        if g.update_pending:
            rows.append(f"[$warning]▲ {self.t('tui.game.update_pending')}[/]")
        if g.prefix_path:
            rows.append(self._row(self.t("tui.game.prefix"), f"[$text-muted]{escape(g.prefix_path)}[/]"))
        return "\n".join(rows)

    @work(thread=True, exclusive=True)
    def _inspect(self) -> None:
        from deckdoctor.checks import steam_game
        from deckdoctor.cli import build_context

        ctx = build_context(network=False, locale=self.locale)
        ctx.appid = self.game.appid
        try:
            result = steam_game.run(ctx)
        except Exception as exc:  # noqa: BLE001 — show inspection errors instead of crashing the UI
            result = None
            error = str(exc)
        else:
            error = ""
        try:
            self.app.call_from_thread(self._show, result, error)
        except RuntimeError:
            pass

    def _show(self, result: CheckResult | None, error: str) -> None:
        self.query_one("#game-loading").display = False
        target = self.query_one("#game-check", Static)
        if result is None:
            target.update(f"[$error]{escape(error)}[/]")
            return
        lines = ["", f"{fmt.glyph(result.status)} [b]{escape(result.finding)}[/b]"]
        if result.explanation:
            lines.append(f"[$text-muted]{escape(result.explanation)}[/]")
        if result.recommendation:
            lines.append(f"[$accent]→ {escape(result.recommendation)}[/]")
        if result.evidence:
            lines += ["", f"[$text-muted]{self.t('tui.detail.evidence')}[/]"]
            lines += [f"[dim]{escape(item)}[/]" for item in result.evidence[:20]]
        target.update("\n".join(lines))

    @on(Button.Pressed, "#game-close")
    def _close(self) -> None:
        self.dismiss(False)
