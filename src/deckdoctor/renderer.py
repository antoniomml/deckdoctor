from __future__ import annotations

import os
import sys

from deckdoctor.checks import ALL_CHECKS
from deckdoctor.checks._util import format_bytes
from deckdoctor.i18n import translate
from deckdoctor.models import FixPlan, FixResult, Report, Severity, Status

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


def _summary_line(report: Report) -> str:
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
    bits = [translate(locale, "ui.tally.ok", n=n["ok"])]
    if n["fail"]:
        bits.append(translate(locale, "ui.tally.fail", n=n["fail"]))
    if n["warn"]:
        bits.append(translate(locale, "ui.tally.warn", n=n["warn"]))
    if report.verbose:
        if n["skip"]:
            bits.append(translate(locale, "ui.tally.skip", n=n["skip"]))
        if n["unknown"]:
            bits.append(translate(locale, "ui.tally.unknown", n=n["unknown"]))
    return "   ".join(bits)


def _hint(key: str, text: str, *, ascii_mode: bool) -> str:
    if ascii_mode:
        return f"    {text}"
    return f"    {_HINT_EMOJI[key]}  {text}"


def _footer(report: Report, plans: list[FixPlan] | None, *, color: bool) -> list[str]:
    locale = report.locale
    lines = [
        "",
        _summary_line(report),
        "",
        _rule(translate(locale, "ui.next"), ascii_mode=report.ascii_mode, color=color, emoji="👉"),
        _hint("report", translate(locale, "ui.report_hint"), ascii_mode=report.ascii_mode),
        _hint("verbose", translate(locale, "ui.verbose_hint"), ascii_mode=report.ascii_mode),
    ]
    if plans:
        lines.append(_hint("fix", translate(locale, "ui.fix_hint", count=len(plans)), ascii_mode=report.ascii_mode))
    else:
        lines.append(_hint("fix", translate(locale, "ui.fix_none"), ascii_mode=report.ascii_mode))
    lines.append(_paint("    " + translate(locale, "ui.readonly"), _DIM, on=color))
    if report.partial:
        lines.append(translate(locale, "ui.partial"))
    return lines


def _diagnosis_block(report: Report) -> list[str]:
    locale = report.locale
    color = report.color
    lines = [_rule(translate(locale, "ui.diagnosis"), ascii_mode=report.ascii_mode, color=color, emoji="💡")]
    for diag in report.diagnoses:
        kind = translate(locale, "ui.fact") if diag.fact_kind == "fact" else translate(locale, "ui.likely")
        conf = translate(locale, f"ui.confidence.{diag.confidence.value}")
        badge = _paint(f"{kind}  ·  {conf}", _YELLOW, on=color)
        lines.append(f"  {badge}")
        lines.append(_paint(f"  {diag.title}", _BOLD, on=color))
        for para in diag.summary.split(". "):
            if para.strip():
                lines.append(f"    {para.strip().rstrip('.')}.")
        if diag.recommendation:
            lines.append("    → " + diag.recommendation)
        lines.append("")
    return lines


def _problem_block(report: Report, *, show_ids: bool) -> list[str]:
    locale = report.locale
    color = report.color
    marks = _STATUS_MARK_ASCII if report.ascii_mode else _STATUS_MARK
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.NONE: 3}
    lines = [_rule(translate(locale, "ui.problems"), ascii_mode=report.ascii_mode, color=color, emoji="❗")]
    for item in sorted(report.problems, key=lambda r: order.get(r.severity, 9)):
        mark = marks.get(item.status, "?")
        tone = _RED if item.status == Status.FAIL else _YELLOW
        label = item.check_id if show_ids else item.title
        sev = translate(locale, f"ui.severity.{item.severity.value}")
        head = _paint(f"  {mark}  {label}", tone + _BOLD if color else "", on=color)
        lines.append(f"{head}  ·  {sev}" if sev else head)
        lines.append(f"      {item.finding}")
        if item.explanation and item.explanation != item.finding and not show_ids:
            lines.append(_paint(f"      {item.explanation}", _DIM, on=color))
        if item.recommendation:
            lines.append(f"      → {item.recommendation}")
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

    problems = report.problems
    if not problems and not report.diagnoses:
        ok = "✅  " if not report.ascii_mode else ""
        lines.append(_paint(f"{ok}{translate(locale, 'ui.no_problems')}", _GREEN + _BOLD if color else "", on=color))
        lines.append(_paint(f"    {translate(locale, 'ui.no_problems.detail')}", _DIM, on=color))
        lines.extend(_footer(report, plans, color=color))
        return "\n".join(lines) + "\n"

    meta: list[str] = []
    if problems:
        meta.append(translate(locale, "ui.problems_count", count=len(problems)))
    if report.diagnoses:
        meta.append(translate(locale, "ui.diag_count", count=len(report.diagnoses)))
    if meta:
        prefix = "    " if not report.ascii_mode else ""
        lines.append(prefix + "  ·  ".join(meta))
        lines.append("")

    if report.diagnoses:
        lines.extend(_diagnosis_block(report))

    lines.extend(_problem_block(report, show_ids=False))
    lines.extend(_footer(report, plans, color=color))
    return "\n".join(lines).rstrip() + "\n"


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
    for title_key, ids in _GROUPS:
        lines.append(_paint(translate(locale, title_key), _BOLD, on=color))
        for check_id in ids:
            item = by.get(check_id)
            if not item:
                continue
            mark = marks.get(item.status, "?")
            prefix = _paint(f"  {mark}  {check_id:<22}", tones.get(item.status, ""), on=color)
            lines.append(f"{prefix} {item.finding}")
        lines.append("")

    if report.diagnoses:
        lines.extend(_diagnosis_block(report))
    if report.problems:
        lines.extend(_problem_block(report, show_ids=True))
    elif not report.diagnoses:
        ok = "✅  " if not report.ascii_mode else ""
        lines.append(_paint(f"{ok}{translate(locale, 'ui.no_problems')}", _GREEN + _BOLD if color else "", on=color))
        lines.append(_paint(f"    {translate(locale, 'ui.no_problems.detail')}", _DIM, on=color))

    lines.extend(_footer(report, plans, color=color))
    return "\n".join(lines).rstrip() + "\n"


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
    lines.append(translate(locale, "fix.need_yes"))
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
