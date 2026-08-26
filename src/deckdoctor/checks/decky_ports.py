from __future__ import annotations

import json
import re
from pathlib import Path

from deckdoctor.checks._util import first_line, result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "DECKY-PORTS"
TITLE = "Decky ports"

CEF_PORT = 8080
DECKY_PORT = 1337
CEF_FORWARD_PORT = 8081
CEF_EXPECTED = ("steamwebhelper", "steam")
DECKY_EXPECTED = ("pluginloader", "python")
CEF_FORWARD_UNIT = "steam-web-debug-portforward.service"
_CSS_HINTS = ("cssloader", "css-loader", "css loader", "sdh-cssloader", "decky-cssloader")


def _parse_ss(text: str) -> dict[int, list[str | None]]:
    """Map interesting ports to process names. ``None`` means listening, name unknown.

    ``ss -ltnp`` as a regular user omits ``users:(("PluginLoader"...))`` for root
    sockets. The raw listen line is not a process name.
    """
    found: dict[int, list[str | None]] = {}
    port_re = re.compile(r":(\d+)\s")
    users_re = re.compile(r'users:\(\("(.*?)"')
    for line in text.splitlines():
        ports = port_re.findall(line)
        um = users_re.search(line)
        proc: str | None = um.group(1) if um else None
        for p in ports:
            port = int(p)
            if port in {CEF_PORT, DECKY_PORT, CEF_FORWARD_PORT}:
                found.setdefault(port, []).append(proc)
    return found


def _names(owners: list[str | None]) -> list[str]:
    return [o for o in owners if o]


def _matches(owners: list[str | None], expected: tuple[str, ...]) -> bool:
    blob = " ".join(_names(owners)).lower()
    return any(tok in blob for tok in expected)


def _fmt(owners: list[str | None], unnamed: str) -> str:
    if not owners:
        return "not listening"
    return ", ".join(name or unnamed for name in owners)


def _ss_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if any(str(p) in ln for p in (1337, 8080, 8081))]


def _comm_for_pid(ctx: DiagnosticContext, pid: int | None) -> str | None:
    if not pid:
        return None
    text = ctx.read_text(Path(f"/proc/{pid}/comm"))
    name = first_line(text or "")
    return name or None


def _line_exposes(line: str, port: int) -> bool:
    if f":{port}" not in line:
        return False
    if f"127.0.0.1:{port}" in line or f"[::1]:{port}" in line:
        return False
    return True


def _cef_forward_setting(ctx: DiagnosticContext) -> bool | None:
    settings = ctx.settings_dir
    paths = [settings / "loader.json"]
    if ctx.exists(settings):
        try:
            paths.extend(sorted(p for p in settings.glob("*.json") if p.name != "loader.json"))
        except OSError:
            pass
    for path in paths:
        text = ctx.read_text(path)
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "cef_forward" in data:
            return bool(data["cef_forward"])
    return None


def _css_loader_names(ctx: DiagnosticContext) -> list[str]:
    names: list[str] = []
    plugins = list(ctx.facts.plugins)
    if not plugins and ctx.exists(ctx.plugins_dir):
        try:
            for entry in ctx.plugins_dir.iterdir():
                if entry.is_dir():
                    plugins.append({"name": entry.name, "dir": entry.name})
        except OSError:
            pass
    for plugin in plugins:
        blob = f"{plugin.get('name', '')} {plugin.get('dir', '')}".lower()
        if any(hint in blob for hint in _CSS_HINTS):
            names.append(str(plugin.get("name") or plugin.get("dir")))
    return names


def _unit_state(ctx: DiagnosticContext, unit: str) -> tuple[str, str]:
    active = ctx.run(["systemctl", "is-active", unit])
    enabled = ctx.run(["systemctl", "is-enabled", unit])
    active_s = "unknown"
    enabled_s = "unknown"
    if active.error != "not_found":
        active_s = (active.stdout or active.stderr).strip().splitlines()[0] if (active.stdout or active.stderr) else "unknown"
    if enabled.error != "not_found":
        enabled_s = (enabled.stdout or enabled.stderr).strip().splitlines()[0] if (enabled.stdout or enabled.stderr) else "unknown"
    return active_s, enabled_s


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    unnamed = ctx.tr("decky.ports.unnamed")
    proc = ctx.run(["ss", "-ltnp"])
    if proc.error == "not_found":
        proc = ctx.run(["ss", "-ltn"])
    if proc.error == "not_found":
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("decky.ports.no_ss"),
            source=EvidenceSource.SOCKETS,
        )
    if proc.timed_out:
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("decky.ports.timeout"),
            source=EvidenceSource.SOCKETS,
        )

    listeners = _parse_ss(proc.stdout)
    owners_1337 = listeners.get(DECKY_PORT, [])
    if owners_1337 and not _names(owners_1337):
        comm = _comm_for_pid(ctx, ctx.facts.decky_service_pid)
        if comm and (
            "pluginloader" in comm.lower() or comm.lower() == "python" or "plugin" in comm.lower()
        ):
            listeners[DECKY_PORT] = [comm]
            owners_1337 = listeners[DECKY_PORT]
            evidence_note = f"port {DECKY_PORT} process from /proc/{ctx.facts.decky_service_pid}/comm: {comm}"
        else:
            evidence_note = ""
    else:
        evidence_note = ""

    ctx.facts.port_8080 = [n or unnamed for n in listeners.get(CEF_PORT, [])]
    ctx.facts.port_1337 = [n or unnamed for n in listeners.get(DECKY_PORT, [])]
    evidence = [
        f"port {CEF_PORT}: {_fmt(listeners.get(CEF_PORT, []), unnamed)}",
        f"port {DECKY_PORT}: {_fmt(listeners.get(DECKY_PORT, []), unnamed)}",
    ]
    if evidence_note:
        evidence.append(evidence_note)
    owners_8081 = listeners.get(CEF_FORWARD_PORT, [])
    if owners_8081:
        evidence.append(f"port {CEF_FORWARD_PORT}: {_fmt(owners_8081, unnamed)}")
    evidence.extend(_ss_lines(proc.stdout)[:8])

    problems: list[str] = []
    recs: list[str] = []
    explains: list[str] = []

    owners_8080 = listeners.get(CEF_PORT, [])
    if owners_8080:
        if _names(owners_8080) and not _matches(owners_8080, CEF_EXPECTED):
            owner = _names(owners_8080)[0]
            problems.append(ctx.tr("decky.ports.conflict8080", owner=repr(owner)))
            explains.append(ctx.tr("decky.ports.conflict8080.explain"))
            recs.append(ctx.tr("decky.ports.conflict8080.rec"))
            ctx.facts.port_8080_conflict = True
    else:
        ctx.facts.port_8080_listening = False
        evidence.append("8080 not listening — Steam Game Mode CEF debugger may be down (or you are in Desktop Mode).")

    owners_1337 = listeners.get(DECKY_PORT, [])
    if owners_1337:
        named = _names(owners_1337)
        if named and not _matches(owners_1337, DECKY_EXPECTED):
            problems.append(ctx.tr("decky.ports.conflict1337", owner=repr(named[0])))
            explains.append(ctx.tr("decky.ports.conflict1337.explain"))
            recs.append(ctx.tr("decky.ports.conflict1337.rec"))
            ctx.facts.port_1337_conflict = True
    elif ctx.facts.decky_service_active == "active":
        problems.append(ctx.tr("decky.ports.missing1337"))
        explains.append(ctx.tr("decky.ports.missing1337.explain"))
        ctx.facts.port_1337_missing = True

    if problems:
        return result(
            ID,
            title,
            Status.FAIL,
            problems[0],
            explanation=explains[0] if explains else "",
            recommendation=" ".join(recs) or ctx.tr("decky.ports.fail.rec"),
            evidence=evidence,
            source=EvidenceSource.SOCKETS,
            severity=Severity.HIGH,
        )

    finding = f"{CEF_PORT}: {_fmt(owners_8080, unnamed)}; {DECKY_PORT}: {_fmt(owners_1337, unnamed)}"
    exposed_8081 = any(_line_exposes(ln, CEF_FORWARD_PORT) for ln in proc.stdout.splitlines())
    if exposed_8081:
        owner = _names(owners_8081)[0] if _names(owners_8081) else ""
        if not owner:
            comm = None
            pid_m = re.search(rf":{CEF_FORWARD_PORT}\b.*?pid=(\d+)", proc.stdout)
            if pid_m:
                comm = _comm_for_pid(ctx, int(pid_m.group(1)))
            owner = comm or unnamed
        setting = _cef_forward_setting(ctx)
        css = _css_loader_names(ctx)
        active_s, enabled_s = _unit_state(ctx, CEF_FORWARD_UNIT)
        ctx.facts.cef_forward_exposed = True
        ctx.facts.cef_forward_setting = setting
        ctx.facts.cef_forward_owner = owner
        evidence.append(f"cef_forward setting: {setting}")
        evidence.append(f"{CEF_FORWARD_UNIT}: active={active_s} enabled={enabled_s}")
        if css:
            evidence.append("theme plugins: " + ", ".join(css))

        if setting is True:
            why = ctx.tr("decky.ports.cef_forward.why.css", name=css[0]) if css else ctx.tr("decky.ports.cef_forward.why.setting")
            return result(
                ID,
                title,
                Status.INFO,
                ctx.tr("decky.ports.cef_forward.expected", why=why),
                explanation=ctx.tr("decky.ports.cef_forward.expected.explain"),
                recommendation=ctx.tr("decky.ports.cef_forward.expected.rec"),
                evidence=evidence,
                source=EvidenceSource.SOCKETS,
                extra={"cef_forward_exposed": True, "cef_forward_expected": True, "compact_note": True},
            )
        finding_u = ctx.tr("decky.ports.cef_forward.named", owner=owner)
        if css:
            finding_u = ctx.tr("decky.ports.cef_forward.css", name=css[0], owner=owner)
        rec = ctx.tr("decky.ports.cef_forward.rec")
        if setting is False:
            rec = ctx.tr("decky.ports.cef_forward.leftover.rec")
        return result(
            ID,
            title,
            Status.WARNING,
            finding_u,
            explanation=ctx.tr("decky.ports.cef_forward.explain"),
            recommendation=rec,
            evidence=evidence,
            source=EvidenceSource.SOCKETS,
            severity=Severity.MEDIUM,
            extra={"cef_forward_exposed": True, "cef_forward_expected": False},
        )
    status = Status.PASS if owners_1337 or ctx.facts.decky_installed is False else Status.INFO
    return result(
        ID,
        title,
        status if owners_8080 or owners_1337 else Status.INFO,
        finding,
        explanation=ctx.tr("decky.ports.ok.explain"),
        evidence=evidence,
        source=EvidenceSource.SOCKETS,
    )
