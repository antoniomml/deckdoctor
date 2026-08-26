from __future__ import annotations

import os
import sys
import textwrap

from deckdoctor.checks import ALL_CHECKS
from deckdoctor.checks._util import format_bytes
from deckdoctor.i18n import translate
from deckdoctor.models import CheckResult, Diagnosis, FixPlan, FixResult, Report, Severity, Status

_STATUS_MARK = {
    Status.PASS: "✅",
    Status.INFO: "ℹ️",
    Status.WARNING: "⚠️",
    Status.FAIL: "❌",
    Status.SKIPPED: "⏭️",
    Status.UNKNOWN: "❓",
}

_STATUS_MARK_ASCII = {
    Status.PASS: "OK",
    Status.INFO: "i",
    Status.WARNING: "!",
    Status.FAIL: "X",
    Status.SKIPPED: "-",
    Status.UNKNOWN: "?",
}

_HINT_EMOJI = {
    "report": "📄",
    "verbose": "🔍",
    "fix": "🔧",
}

_GROUPS = (
    ("group.system", ("SYS-OS-VERSION", "SYS-OS-CHANNEL", "SYS-OS-UPDATER", "SYS-OS-REBOOT", "SYS-OVERLAY", "SYS-DISK", "SYS-TIME", "STEAM-CLIENT")),
    ("group.decky", ("DECKY-INSTALL", "DECKY-SERVICE", "DECKY-PORTS", "DECKY-FRONTEND", "DECKY-LOGS")),
    ("group.plugins", ("PLUGIN-INVENTORY", "PLUGIN-REMOTE-BIN", "PLUGIN-STORE-UPDATES", "AUTOFLATPAKS")),
    ("group.flatpak", ("FP-BASIC", "FP-UPDATES", "FP-EOL")),
    ("group.network", ("NET-GITHUB", "NET-STORE")),
)

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_WRAP = 78


def color_enabled(*, ascii_mode: bool, color: bool, stream: object | None = None) -> bool:
    if ascii_mode or not color:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    out = stream if stream is not None else sys.stdout
    return bool(getattr(out, "isatty", lambda: False)())


def _paint(text: str, code: str, *, on: bool) -> str:
    if not on:
        return text
    return f"{code}{text}{_RESET}"


def _arrow(ascii_mode: bool) -> str:
    return "->" if ascii_mode else "→"


def _fill(text: str, *, indent: str, width: int = _WRAP) -> list[str]:
    if not text:
        return []
    hang = "  " if text.startswith("→ ") or text.startswith("-> ") else ""
    wrapper = textwrap.TextWrapper(
        width=width,
        initial_indent=indent,
        subsequent_indent=indent + hang,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return wrapper.wrap(text) or [indent + text]


def _rule(label: str, *, ascii_mode: bool, color: bool, emoji: str = "") -> str:
    title = _paint(label, _BOLD, on=color)
    if ascii_mode:
        return f"-- {title} --"
    if emoji:
        return f"{emoji}  {title}"
    return f"{title}"


def _brand(report: Report) -> str:
    name = _paint(f"DeckDoctor {report.version}", _BOLD, on=report.color)
    if report.ascii_mode:
        return name
    return f"🩺  {name}"


def _headline(report: Report) -> str:
    by = {r.check_id: r for r in report.results}
    osver = by.get("SYS-OS-VERSION")
    decky = by.get("DECKY-INSTALL")
    bits: list[str] = []
    if osver and osver.status in {Status.PASS, Status.INFO}:
        bits.append(osver.finding)
    if decky and decky.status == Status.PASS:
        bits.append(decky.finding)
    return " · ".join(bits)


def _snapshot_lines(report: Report) -> list[str]:
    facts = report.facts
    if facts.get("storage_internal") is None and facts.get("steam_game_count") is None:
        return []
    locale = report.locale
    indent = "    " if not report.ascii_mode else ""
    lines: list[str] = []
    internal = facts.get("storage_internal")
    if isinstance(internal, dict) and internal.get("total"):
        lines.append(
            indent
            + translate(
                locale,
                "ui.snapshot.internal",
                free=format_bytes(int(internal["free"])),
                total=format_bytes(int(internal["total"])),
            )
        )
    sd = facts.get("storage_sd")
    if isinstance(sd, dict) and sd.get("total"):
        lines.append(
            indent
            + translate(
                locale,
                "ui.snapshot.sd",
                free=format_bytes(int(sd["free"])),
                total=format_bytes(int(sd["total"])),
            )
        )
    elif facts.get("is_steamos"):
        lines.append(indent + translate(locale, "ui.snapshot.sd.missing"))
    games = facts.get("steam_game_count")
    if games is None:
        return lines
    gi = int(facts.get("steam_games_internal") or 0)
    gs = int(facts.get("steam_games_sd") or 0)
    if int(games) == 0:
        lines.append(indent + translate(locale, "ui.snapshot.games.none"))
    elif sd:
        lines.append(
            indent
            + translate(locale, "ui.snapshot.games.split", total=games, internal=gi, sd=gs)
        )
    else:
        lines.append(indent + translate(locale, "ui.snapshot.games.internal_only", total=games))
    return lines


def render_cli(report: Report, *, plans: list[FixPlan] | None = None) -> str:
    if report.verbose:
        return _render_verbose(report, plans=plans)
    return _render_compact(report, plans=plans)


def _counts(report: Report) -> dict[str, int]:
    tallies = {"ok": 0, "fail": 0, "warn": 0, "skip": 0, "unknown": 0, "info": 0}
    for item in report.results:
        if item.status == Status.FAIL:
            tallies["fail"] += 1
        elif item.status == Status.WARNING:
            tallies["warn"] += 1
        elif item.status == Status.SKIPPED:
            tallies["skip"] += 1
        elif item.status == Status.UNKNOWN:
            tallies["unknown"] += 1
        elif item.status == Status.INFO:
            tallies["info"] += 1
            tallies["ok"] += 1
        else:
            tallies["ok"] += 1
    return tallies


def _summary_line(report: Report, *, color: bool) -> str:
    locale = report.locale
    n = _counts(report)
    if report.ascii_mode:
        return translate(
            locale,
            "ui.summary",
            ok=n["ok"],
            fail=n["fail"],
            warn=n["warn"],
            skip=n["skip"],
            unknown=n["unknown"],
        )
    bits = [_paint(translate(locale, "ui.tally.ok", n=n["ok"]), _GREEN, on=color)]
    if n["fail"]:
        bits.append(_paint(translate(locale, "ui.tally.fail", n=n["fail"]), _RED, on=color))
    if n["warn"]:
        bits.append(_paint(translate(locale, "ui.tally.warn", n=n["warn"]), _YELLOW, on=color))
    if report.verbose:
        if n["skip"]:
            bits.append(_paint(translate(locale, "ui.tally.skip", n=n["skip"]), _DIM, on=color))
        if n["unknown"]:
            bits.append(_paint(translate(locale, "ui.tally.unknown", n=n["unknown"]), _YELLOW, on=color))
    return "    ".join(bits)


def _hint(key: str, text: str, *, ascii_mode: bool) -> str:
    if ascii_mode:
        return f"    {text}"
    return f"    {_HINT_EMOJI[key]}  {text}"


def _footer(report: Report, plans: list[FixPlan] | None, *, color: bool) -> list[str]:
    locale = report.locale
    pad = "    "
    lines = ["", f"{pad}{_summary_line(report, color=color)}", ""]
    lines.append(_hint("report", translate(locale, "ui.report_hint"), ascii_mode=report.ascii_mode))
    lines.append(_hint("verbose", translate(locale, "ui.verbose_hint"), ascii_mode=report.ascii_mode))
    if plans:
        lines.append(_hint("fix", translate(locale, "ui.fix_hint", count=len(plans)), ascii_mode=report.ascii_mode))
    else:
        lines.append(_hint("fix", translate(locale, "ui.fix_none"), ascii_mode=report.ascii_mode))
    lines.append(_paint(pad + translate(locale, "ui.readonly"), _DIM, on=color))
    if report.partial:
        lines.append(pad + translate(locale, "ui.partial"))
    return lines


def _compact_diagnoses(report: Report) -> list[Diagnosis]:
    """Compact view only tells a story when we inferred a cause, not when a check already said it."""
    return [d for d in report.diagnoses if d.fact_kind == "likely"]


def _compact_notes(report: Report) -> list[CheckResult]:
    return [r for r in report.results if r.status == Status.INFO and r.extra.get("compact_note")]


def _join(lines: list[str]) -> str:
    text = "\n".join(lines).rstrip() + "\n"
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def _rec_lines(text: str, *, indent: str, color: bool) -> list[str]:
    rows = _fill(text, indent=indent)
    return [_paint(row, _CYAN, on=color) for row in rows]


def _diagnosis_block(report: Report, diagnoses: list[Diagnosis] | None = None, *, heading: bool) -> list[str]:
    color = report.color
    ascii_mode = report.ascii_mode
    items = list(report.diagnoses if diagnoses is None else diagnoses)
    if not items:
        return []
    arrow = _arrow(ascii_mode)
    lines: list[str] = []
    if heading:
        lines.append(
            _rule(translate(report.locale, "ui.diagnosis"), ascii_mode=ascii_mode, color=color, emoji="💡")
        )
    for diag in items:
        if heading:
            kind = translate(report.locale, "ui.fact") if diag.fact_kind == "fact" else translate(report.locale, "ui.likely")
            conf = translate(report.locale, f"ui.confidence.{diag.confidence.value}")
            lines.append(_paint(f"  {kind}  ·  {conf}", _DIM, on=color))
            lines.append(_paint(f"  {diag.title}", _BOLD, on=color))
            body_indent = "    "
        elif ascii_mode:
            lines.append(_paint(f"* {diag.title}", _BOLD, on=color))
            body_indent = "  "
        else:
            lines.append(_paint(f"💡  {diag.title}", _BOLD, on=color))
            body_indent = "    "
        lines.extend(_fill(diag.summary, indent=body_indent))
        if diag.recommendation:
            lines.extend(_rec_lines(f"{arrow} {diag.recommendation}", indent=body_indent, color=color))
        lines.append("")
    return lines


def _problem_lines(report: Report, *, compact: bool) -> list[str]:
    color = report.color
    ascii_mode = report.ascii_mode
    marks = _STATUS_MARK_ASCII if ascii_mode else _STATUS_MARK
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.NONE: 3}
    arrow = _arrow(ascii_mode)
    lines: list[str] = []
    if not compact:
        lines.append(_rule(translate(report.locale, "ui.problems"), ascii_mode=ascii_mode, color=color, emoji="❗"))
    for item in sorted(report.problems, key=lambda r: order.get(r.severity, 9)):
        mark = marks.get(item.status, "?")
        tone = _RED if item.status == Status.FAIL else _YELLOW
        label = item.title if compact else item.check_id
        lines.append(_paint(f"{mark}  {label}", tone + _BOLD if color else "", on=color))
        lines.extend(_fill(item.finding, indent="    "))
        if not compact and item.explanation and item.explanation != item.finding:
            for row in _fill(item.explanation, indent="    "):
                lines.append(_paint(row, _DIM, on=color))
        if item.recommendation:
            lines.extend(_rec_lines(f"{arrow} {item.recommendation}", indent="    ", color=color))
        lines.append("")
    return lines


def _render_compact(report: Report, *, plans: list[FixPlan] | None) -> str:
    locale = report.locale
    color = report.color
    lines = [_brand(report)]
    headline = _headline(report)
    if headline:
        lines.append(_paint(f"    {headline}" if not report.ascii_mode else headline, _DIM, on=color))
    lines.extend(_snapshot_lines(report))
    lines.append("")

    stories = _compact_diagnoses(report)
    notes = _compact_notes(report)
    problems = report.problems
    if not problems and not stories and not notes:
        ok = "✅  " if not report.ascii_mode else ""
        lines.append(_paint(f"{ok}{translate(locale, 'ui.no_problems')}", _GREEN + _BOLD if color else "", on=color))
        lines.extend(_footer(report, plans, color=color))
        return _join(lines)

    if notes:
        mark = "i" if report.ascii_mode else "ℹ️"
        for item in notes:
            lines.append(_paint(f"{mark}  {item.title}", _CYAN + _BOLD if color else "", on=color))
            lines.extend(_fill(item.finding, indent="    "))
            if item.recommendation:
                lines.extend(_rec_lines(f"{_arrow(report.ascii_mode)} {item.recommendation}", indent="    ", color=color))
            lines.append("")
    if stories:
        lines.extend(_diagnosis_block(report, stories, heading=False))
    if problems:
        lines.extend(_problem_lines(report, compact=True))
    lines.extend(_footer(report, plans, color=color))
    return _join(lines)


def _render_verbose(report: Report, *, plans: list[FixPlan] | None) -> str:
    locale = report.locale
    color = report.color
    marks = _STATUS_MARK_ASCII if report.ascii_mode else _STATUS_MARK
    lines = [_brand(report)]
    headline = _headline(report)
    if headline:
        lines.append(_paint(f"    {headline}" if not report.ascii_mode else headline, _DIM, on=color))
    lines.extend(_snapshot_lines(report))
    lines.append("")
    by = {r.check_id: r for r in report.results}
    tones = {
        Status.PASS: _GREEN,
        Status.FAIL: _RED,
        Status.WARNING: _YELLOW,
        Status.SKIPPED: _DIM,
        Status.INFO: _CYAN,
        Status.UNKNOWN: _YELLOW,
    }
    arrow = _arrow(report.ascii_mode)
    for title_key, ids in _GROUPS:
        lines.append(_paint(translate(locale, title_key), _BOLD, on=color))
        for check_id in ids:
            item = by.get(check_id)
            if not item:
                continue
            mark = marks.get(item.status, "?")
            prefix = _paint(f"  {mark}  {check_id:<22}", tones.get(item.status, ""), on=color)
            lines.append(f"{prefix} {item.finding}")
            if item.status in {Status.FAIL, Status.WARNING} and item.recommendation:
                rec = f"      {arrow} {item.recommendation}"
                lines.append(_paint(rec, _CYAN, on=color) if color else rec)
        lines.append("")

    if report.diagnoses:
        lines.extend(_diagnosis_block(report, heading=True))
    elif not report.problems:
        ok = "✅  " if not report.ascii_mode else ""
        lines.append(_paint(f"{ok}{translate(locale, 'ui.no_problems')}", _GREEN + _BOLD if color else "", on=color))

    lines.extend(_footer(report, plans, color=color))
    return _join(lines)


def render_checks_catalog(locale: str, *, ascii_mode: bool = False, color: bool = False) -> str:
    lines = [_paint(translate(locale, "checks.header"), _BOLD, on=color), ""]
    id_h = translate(locale, "checks.col.id")
    net_h = translate(locale, "checks.col.net")
    title_h = translate(locale, "checks.col.title")
    lines.append(f"  {id_h:<22} {net_h:<8} {title_h}")
    sep = "-" if ascii_mode else "─"
    lines.append(f"  {sep * 22} {sep * 8} {sep * 24}")
    for check in ALL_CHECKS:
        net = translate(locale, "checks.net.yes" if check.requires_network else "checks.net.no")
        title = translate(locale, f"title.{check.id}")
        lines.append(f"  {check.id:<22} {net:<8} {title}")
    lines.append("")
    return "\n".join(lines)


def render_fix_plan(plans: list[FixPlan], locale: str, *, ascii_mode: bool = False, color: bool = False) -> str:
    lines = [_paint(translate(locale, "fix.header"), _BOLD, on=color), ""]
    if not plans:
        lines.append(translate(locale, "fix.empty"))
        lines.append(_paint(translate(locale, "fix.empty.detail"), _DIM, on=color))
        lines.append("")
        return "\n".join(lines)
    for index, plan in enumerate(plans, start=1):
        risk = translate(locale, f"fix.risk.{plan.risk}")
        extra = f" · {translate(locale, 'fix.needs_root')}" if plan.needs_root else ""
        lines.append(_paint(f"{index}.  {plan.id}  —  {plan.title}", _BOLD, on=color))
        lines.append(_paint(f"    {risk}{extra}", _DIM, on=color))
        lines.append(f"    {plan.summary}")
        lines.append(f"    {translate(locale, 'fix.mutation')}: {plan.mutation}")
        lines.append(f"    {translate(locale, 'fix.undo')}: {plan.reversible}")
        lines.append("")
    return "\n".join(lines)


def render_fix_results(results: list[FixResult], locale: str, *, color: bool = False, ascii_mode: bool = False) -> str:
    lines = [translate(locale, "fix.applying", count=len(results)), ""]
    mark_ok = "OK" if ascii_mode else _paint("✅", _GREEN, on=color)
    mark_bad = "X" if ascii_mode else _paint("❌", _RED, on=color)
    for item in results:
        if item.ok:
            lines.append(f"  {mark_ok}  {translate(locale, 'fix.done_ok', id=item.id)}")
        else:
            lines.append(f"  {mark_bad}  {translate(locale, 'fix.done_fail', id=item.id)}")
        lines.append(f"      {item.finding}")
        for ev in item.evidence[:4]:
            lines.append(_paint(f"      {ev}", _DIM, on=color))
        lines.append("")
    return "\n".join(lines)
