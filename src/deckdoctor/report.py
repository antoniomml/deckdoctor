from __future__ import annotations

from deckdoctor.i18n import translate
from deckdoctor.models import Report, Status
from deckdoctor.sanitizer import Sanitizer


def render_markdown(report: Report, sanitizer: Sanitizer) -> str:
    raw = _markdown(report)
    return sanitizer.apply(raw)


def _markdown(report: Report) -> str:
    def t(key: str, **kwargs: object) -> str:
        return translate(report.locale, key, **kwargs)

    facts = report.facts
    lines = [
        t("report.title"),
        "",
        f"- Tool version: `{report.version}`",
        f"- Generated (UTC): `{report.generated_at}`",
        t("report.posture"),
        t("report.sanitise"),
        "",
        t("report.system"),
        "",
        f"- User home (sanitised later): `{facts.get('decky_home', '')}`",
        f"- SteamOS version: `{facts.get('os_version', 'unknown')}` build `{facts.get('os_build', 'unknown')}`",
        f"- SteamOS channel: `{facts.get('os_channel', 'unknown')}`",
        f"- Steam client: build `{facts.get('steam_version', 'unknown')}` channel `{facts.get('steam_channel', 'unknown')}`",
        f"- Decky: `{facts.get('decky_version', 'unknown')}` channel `{facts.get('decky_channel', 'unknown')}`",
        f"- PluginLoader present: `{facts.get('plugin_loader_present', 'unknown')}`",
        "",
        t("report.summary"),
        "",
        "| Status | ID | Finding |",
        "|---|---|---|",
    ]
    for item in report.results:
        finding = item.finding.replace("|", "\\|")
        lines.append(f"| `{item.status.value}` | `{item.check_id}` | {finding} |")

    lines += ["", t("report.diagnoses"), ""]
    if not report.diagnoses:
        lines.append(t("report.no_diagnoses"))
    for diag in report.diagnoses:
        lines.append(f"### {diag.title}")
        lines.append("")
        lines.append(
            f"- Kind: **{diag.fact_kind}** · confidence **{diag.confidence.value}** · severity **{diag.severity.value}**"
        )
        lines.append(f"- Checks: {', '.join(f'`{c}`' for c in diag.related_checks)}")
        lines.append("")
        lines.append(diag.summary)
        lines.append("")
        if diag.recommendation:
            lines.append(f"**{t('ui.recommended', text=diag.recommendation).split(': ', 1)[-1]}**")
            lines.append("")

    lines += ["", t("report.problems"), ""]
    problems = [r for r in report.results if r.status in {Status.FAIL, Status.WARNING}]
    if not problems:
        lines.append(t("report.none"))
    for item in problems:
        lines.append(f"### {item.check_id}: {item.finding}")
        lines.append("")
        lines.append(
            f"- Status: `{item.status.value}` · severity `{item.severity.value}` · source `{item.source.value}`"
        )
        if item.explanation:
            lines.append("")
            lines.append(item.explanation)
        if item.recommendation:
            lines.append("")
            lines.append(f"**{t('ui.recommended', text=item.recommendation)}**")
        if item.evidence:
            lines.append("")
            lines.append("Evidence:")
            lines.append("")
            lines.append("```")
            lines.extend(item.evidence[:40])
            lines.append("```")
        lines.append("")

    lines += [
        t("report.network"),
        "",
        t("report.network.body"),
        "",
        t("report.plugins"),
        "",
    ]
    plugins = facts.get("plugins") or []
    if not plugins:
        lines.append(t("report.no_plugins"))
    else:
        lines.append("| Name | Version | Directory |")
        lines.append("|---|---|---|")
        for plugin in plugins:
            lines.append(f"| {plugin.get('name')} | {plugin.get('version')} | `{plugin.get('dir')}` |")

    lines += [
        "",
        "---",
        "",
        t("report.footer"),
        "",
    ]
    return "\n".join(lines)
