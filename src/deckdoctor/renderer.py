from __future__ import annotations

from deckdoctor.models import Report, Severity, Status

_STATUS_MARK = {
    Status.PASS: "✓",
    Status.INFO: "•",
    Status.WARNING: "⚠",
    Status.FAIL: "✗",
    Status.SKIPPED: "⊘",
    Status.UNKNOWN: "?",
}

_GROUPS = (
    ("SteamOS / system", ("SYS-OS-VERSION", "SYS-OS-CHANNEL", "SYS-OS-UPDATER", "SYS-DISK", "SYS-TIME", "STEAM-CLIENT")),
    ("Decky Loader", ("DECKY-INSTALL", "DECKY-SERVICE", "DECKY-PORTS", "DECKY-FRONTEND", "DECKY-LOGS")),
    ("Plugins", ("PLUGIN-INVENTORY", "PLUGIN-REMOTE-BIN", "AUTOFLATPAKS")),
    ("Flatpak", ("FP-BASIC", "FP-UPDATES")),
    ("Network", ("NET-GITHUB", "NET-STORE")),
)


def render_cli(report: Report) -> str:
    lines = [f"DeckDoctor {report.version}", ""]
    by = {r.check_id: r for r in report.results}
    for title, ids in _GROUPS:
        lines.append(title)
        for check_id in ids:
            item = by.get(check_id)
            if not item:
                continue
            mark = _STATUS_MARK.get(item.status, "?")
            lines.append(f"  {mark}  {item.finding}")
        lines.append("")

    if report.diagnoses:
        lines.append("Diagnosis")
        for diag in report.diagnoses:
            kind = "FACT" if diag.fact_kind == "fact" else "LIKELY CAUSE"
            lines.append(f"  [{kind} · {diag.confidence.value}] {diag.title}")
            for para in diag.summary.split(". "):
                if para.strip():
                    bit = para.strip().rstrip(".")
                    lines.append(f"    {bit}.")
            if diag.recommendation:
                lines.append(f"    Recommended: {diag.recommendation}")
            lines.append("")

    problems = report.problems
    lines.append(f"Problems found: {len(problems)}")
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.NONE: 3}
    for item in sorted(problems, key=lambda r: order.get(r.severity, 9)):
        lines.append(f"  {item.severity.value.upper():<6} {item.finding}")
        if item.recommendation:
            lines.append(f"         {item.recommendation}")
    if not problems and not report.diagnoses:
        lines.append("  No FAIL or WARNING checks.")
    lines.append("")
    lines.append("Run `deckdoctor report` for a sanitised diagnostic report.")
    lines.append("DeckDoctor is read-only: it does not restart services, update Flatpaks, or upload data.")
    return "\n".join(lines) + "\n"
