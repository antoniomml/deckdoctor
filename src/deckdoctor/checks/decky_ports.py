from __future__ import annotations

import re

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "DECKY-PORTS"
TITLE = "Decky ports"

CEF_PORT = 8080
DECKY_PORT = 1337
CEF_EXPECTED = "steamwebhelper"
DECKY_EXPECTED = "PluginLoader"


def _parse_ss(text: str) -> dict[int, list[str]]:
    found: dict[int, list[str]] = {}
    port_re = re.compile(r":(\d+)\s")
    users_re = re.compile(r'users:\(\("(.*?)"')
    for line in text.splitlines():
        ports = port_re.findall(line)
        proc = None
        um = users_re.search(line)
        if um:
            proc = um.group(1)
        for p in ports:
            port = int(p)
            if port in {CEF_PORT, DECKY_PORT}:
                label = proc or line.strip()
                found.setdefault(port, []).append(label)
    return found


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
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
    ctx.facts.port_8080 = listeners.get(CEF_PORT, [])
    ctx.facts.port_1337 = listeners.get(DECKY_PORT, [])
    evidence = []
    for port in (CEF_PORT, DECKY_PORT):
        owners = listeners.get(port) or ["(not listening)"]
        evidence.append(f"port {port}: {', '.join(owners)}")

    problems: list[str] = []
    recs: list[str] = []

    owners_8080 = listeners.get(CEF_PORT, [])
    if owners_8080:
        joined = " ".join(owners_8080)
        if CEF_EXPECTED not in joined and "steam" not in joined.lower():
            problems.append(ctx.tr("decky.ports.conflict8080", owner=repr(owners_8080[0])))
            recs.append(ctx.tr("decky.ports.conflict8080.rec"))
            ctx.facts.port_8080_conflict = True
    else:
        ctx.facts.port_8080_listening = False
        evidence.append("8080 not listening — Steam Game Mode CEF debugger may be down (or you are in Desktop Mode).")

    owners_1337 = listeners.get(DECKY_PORT, [])
    if owners_1337:
        joined = " ".join(owners_1337)
        if DECKY_EXPECTED.lower() not in joined.lower() and "pluginloader" not in joined.lower() and "python" not in joined.lower():
            problems.append(ctx.tr("decky.ports.conflict1337", owner=repr(owners_1337[0])))
            recs.append(ctx.tr("decky.ports.conflict1337.rec"))
            ctx.facts.port_1337_conflict = True
    elif ctx.facts.decky_service_active == "active":
        problems.append(ctx.tr("decky.ports.missing1337"))
        ctx.facts.port_1337_missing = True

    if problems:
        return result(
            ID,
            title,
            Status.FAIL,
            problems[0],
            explanation=" ".join(problems),
            recommendation=" ".join(recs) or ctx.tr("decky.ports.fail.rec"),
            evidence=evidence + [proc.stdout.strip()[:500]],
            source=EvidenceSource.SOCKETS,
            severity=Severity.HIGH,
        )

    finding = (
        f"{CEF_PORT}: {', '.join(owners_8080) if owners_8080 else 'not listening'}; "
        f"{DECKY_PORT}: {', '.join(owners_1337) if owners_1337 else 'not listening'}"
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
