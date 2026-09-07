from __future__ import annotations

import json
import os

from deckdoctor.checks._util import format_bytes, result
from deckdoctor.checks.sys_disk import classify
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, Status
from deckdoctor.steam import library_roots

ID = 'STEAM-LIBRARIES'
TITLE = 'Steam libraries'


def run(ctx: DiagnosticContext) -> CheckResult:
    roots, readable = library_roots(ctx)
    evidence: list[str] = []
    libraries = []
    issues = 0
    for root in roots:
        apps = root / 'steamapps'
        accessible = os.access(apps, os.R_OK | os.X_OK)
        writable = os.access(apps, os.W_OK | os.X_OK)
        usage = ctx.measure_disk(root) if accessible else None
        state = 'ok'
        if not accessible:
            state = 'missing_or_unreadable'
        elif not writable:
            state = 'not_writable'
        elif usage is None:
            state = 'space_unknown'
        elif classify(usage.total, usage.free)[0] in {Status.WARNING, Status.FAIL}:
            state = 'low_space'
        issues += state != 'ok'
        mount = None
        if accessible:
            proc = ctx.run(['findmnt', '--json', '--target', str(root), '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS'], timeout=3)
            if proc.ok:
                try:
                    data = json.loads(proc.stdout)
                    rows = data.get('filesystems', []) if isinstance(data, dict) else []
                    mount = rows[0] if rows and isinstance(rows[0], dict) else None
                except (ValueError, TypeError, KeyError):
                    pass
        item = {'mount': mount, 'path': str(root), 'state': state, 'free': usage.free if usage else None,
                'total': usage.total if usage else None}
        libraries.append(item)
        if mount:
            evidence.append(f'{root}: mount={mount.get("target")} type={mount.get("fstype")} source={mount.get("source")}')
        evidence.append(f'{root}: {state}' + (f' ({format_bytes(usage.free)} free)' if usage else ''))
    return result(ID, ctx.tr(f'title.{ID}'), Status.WARNING if issues else Status.INFO if readable else Status.UNKNOWN,
                  ctx.tr('libraries.summary', count=len(roots), issues=issues) if readable or roots else ctx.tr('libraries.unknown'),
                  explanation=ctx.tr('libraries.unknown') if not readable else '',
                  recommendation=ctx.tr('libraries.rec') if issues else ctx.tr('libraries.detail'),
                  evidence=evidence, extra={'libraries': libraries, 'catalog_readable': readable,
                                           'compact_note': True})
