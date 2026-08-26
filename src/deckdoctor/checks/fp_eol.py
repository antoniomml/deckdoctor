from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "FP-EOL"
TITLE = "Flatpak end-of-life"

MAX_METADATA_PROBES = 24


def _metadata_value(text: str, key: str) -> str:
    prefix = f"{key}="
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _ref_key(ref: str) -> str:
    value = ref.strip()
    for prefix in ("runtime/", "app/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    if ctx.facts.flatpak_available is False:
        return result(
            ID,
            title,
            Status.SKIPPED,
            ctx.tr("skip.flatpak_missing"),
            source=EvidenceSource.FLATPAK,
        )

    runtimes = ctx.run(
        ["flatpak", "list", "--runtime", "--columns=ref,application,origin"],
        timeout=20.0,
    )
    apps = ctx.run(
        ["flatpak", "list", "--app", "--columns=ref,application,runtime,origin"],
        timeout=20.0,
    )
    evidence = [
        f"list --runtime exit {runtimes.exit_code}",
        f"list --app exit {apps.exit_code}",
    ]
    if runtimes.error == "not_found":
        return result(ID, title, Status.SKIPPED, ctx.tr("skip.flatpak_missing"), source=EvidenceSource.FLATPAK)
    if runtimes.timed_out or apps.timed_out:
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("fp.eol.timeout"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
        )
    if not runtimes.ok:
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("fp.eol.list_fail"),
            explanation=ctx.tr("fp.eol.list_fail.explain"),
            evidence=evidence + [runtimes.stderr.strip()[:400]],
            source=EvidenceSource.FLATPAK,
        )

    runtime_rows = _parse_rows(runtimes.stdout, header="ref")
    app_rows = _parse_rows(apps.stdout if apps.ok else "", header="ref")
    if not runtime_rows and not app_rows:
        ctx.facts.flatpak_eol = []
        return result(
            ID,
            title,
            Status.PASS,
            ctx.tr("fp.eol.empty"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
            extra={"count": 0},
        )

    eol_runtimes: list[tuple[str, str]] = []
    probed = 0
    for row in runtime_rows:
        if probed >= MAX_METADATA_PROBES:
            evidence.append(f"stopped after {MAX_METADATA_PROBES} metadata probes")
            break
        ref = row[0]
        probed += 1
        meta = ctx.run(["flatpak", "info", "--show-metadata", ref], timeout=10.0)
        if not meta.ok:
            continue
        note = _metadata_value(meta.stdout, "EndOfLife")
        if note:
            eol_runtimes.append((ref, note))
            evidence.append(f"EOL runtime {ref}: {note[:160]}")

    eol_keys = {_ref_key(ref) for ref, _ in eol_runtimes}
    eol_apps: list[str] = []
    for row in app_rows:
        ref = row[0]
        runtime = row[2] if len(row) > 2 else ""
        app_name = row[1] if len(row) > 1 else ref
        if _ref_key(runtime) in eol_keys or runtime in eol_keys:
            eol_apps.append(f"{app_name} ({ref}) runtime={runtime}")
            evidence.append(f"app on EOL runtime: {app_name} → {runtime}")

    findings = [f"{ref}: {note[:80]}" for ref, note in eol_runtimes]
    ctx.facts.flatpak_eol = findings + eol_apps
    if not eol_runtimes:
        return result(
            ID,
            title,
            Status.PASS,
            ctx.tr("fp.eol.clean"),
            explanation=ctx.tr("fp.eol.clean.explain"),
            evidence=evidence,
            source=EvidenceSource.FLATPAK,
            extra={"count": 0},
        )

    app_bit = ctx.tr("fp.eol.apps", count=len(eol_apps)) if eol_apps else ""
    return result(
        ID,
        title,
        Status.WARNING,
        ctx.tr("fp.eol.some", count=len(eol_runtimes), apps=app_bit),
        explanation=ctx.tr("fp.eol.some.explain"),
        recommendation=ctx.tr("fp.eol.some.rec"),
        evidence=evidence[:40],
        source=EvidenceSource.FLATPAK,
        severity=Severity.LOW,
        extra={"runtimes": len(eol_runtimes), "apps": len(eol_apps)},
    )


def _parse_rows(stdout: str, *, header: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split("\t") if "\t" in raw else raw.split()
        if parts and parts[0].lower() == header:
            continue
        rows.append(parts)
    return rows
