from __future__ import annotations

from deckdoctor.i18n import translate
from deckdoctor.models import Report, Severity, Status

_STATUS_MARK = {
    Status.PASS: "✓",
    Status.INFO: "•",
    Status.WARNING: "⚠",
    Status.FAIL: "✗",
    Status.SKIPPED: "⊘",
    Status.UNKNOWN: "?",
}

_STATUS_MARK_ASCII = {
    Status.PASS: "OK",
    Status.INFO: "i",
    Status.WARNING: "!",
    Status.FAIL: "X",
    Status.SKIPPED: "-",
    Status.UNKNOWN: "?",
}

_GROUPS = (
    ("group.system", ("SYS-OS-VERSION", "SYS-OS-CHANNEL", "SYS-OS-UPDATER", "SYS-DISK", "SYS-TIME", "STEAM-CLIENT")),
    ("group.decky", ("DECKY-INSTALL", "DECKY-SERVICE", "DECKY-PORTS", "DECKY-FRONTEND", "DECKY-LOGS")),
    ("group.plugins", ("PLUGIN-INVENTORY", "PLUGIN-REMOTE-BIN", "AUTOFLATPAKS")),
    ("group.flatpak", ("FP-BASIC", "FP-UPDATES")),
    ("group.network", ("NET-GITHUB", "NET-STORE")),
)


def render_cli(report: Report) -> str:
    locale = report.locale
    marks = _STATUS_MARK_ASCII if report.ascii_mode else _STATUS_MARK
    lines = [f"DeckDoctor {report.version}", ""]
    by = {r.check_id: r for r in report.results}
    for title_key, ids in _GROUPS:
        lines.append(translate(locale, title_key))
        for check_id in ids:
            item = by.get(check_id)
            if not item:
                continue
            mark = marks.get(item.status, "?")
            lines.append(f"  {mark}  {item.finding}")
        lines.append("")

    if report.diagnoses:
        lines.append(translate(locale, "ui.diagnosis"))
        for diag in report.diagnoses:
            kind = translate(locale, "ui.fact") if diag.fact_kind == "fact" else translate(locale, "ui.likely")
            lines.append(f"  [{kind} · {diag.confidence.value}] {diag.title}")
            for para in diag.summary.split(". "):
                if para.strip():
                    bit = para.strip().rstrip(".")
                    lines.append(f"    {bit}.")
            if diag.recommendation:
                lines.append("    " + translate(locale, "ui.recommended", text=diag.recommendation))
            lines.append("")

    problems = report.problems
    lines.append(translate(locale, "ui.problems", count=len(problems)))
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.NONE: 3}
    for item in sorted(problems, key=lambda r: order.get(r.severity, 9)):
        lines.append(f"  {item.severity.value.upper():<6} {item.finding}")
        if item.recommendation:
            lines.append(f"         {item.recommendation}")
    if not problems and not report.diagnoses:
        lines.append("  " + translate(locale, "ui.no_problems"))
    if report.partial:
        lines.append(translate(locale, "ui.partial"))
    lines.append("")
    lines.append(translate(locale, "ui.report_hint"))
    lines.append(translate(locale, "ui.readonly"))
    return "\n".join(lines) + "\n"
