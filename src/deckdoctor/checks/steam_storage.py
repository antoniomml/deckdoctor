from __future__ import annotations

import time

from deckdoctor.checks._util import format_bytes, result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status
from deckdoctor.storage import measure_report, scan

ID = 'STEAM-STORAGE'
TITLE = 'Steam storage leftovers'
# Below this, leftovers are noise (empty prefixes, tiny shader stubs).
NOTEWORTHY_BYTES = 100 * 1024**2


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f'title.{ID}')
    report = scan(ctx)
    if not report.libraries:
        return result(ID, title, Status.UNKNOWN, ctx.tr('storage.no_libraries'), source=EvidenceSource.STEAM_METADATA)
    budget = ctx.remaining_timeout(10.0)
    measure_report(report, leftovers_only=True, deadline=time.monotonic() + budget)
    prefixes = [item for item in report.leftovers if item.kind == 'prefix']
    caches = [item for item in report.leftovers if item.kind == 'shadercache']
    total = report.leftover_bytes
    ctx.facts.storage_leftover_bytes = total
    evidence = [f'{item.kind} {item.appid} ({item.reason}): {item.path} {format_bytes(item.size or 0)}'
                for item in sorted(report.leftovers, key=lambda i: -(i.size or 0))[:40]]
    extra = {
        'leftover_bytes': total,
        'prefix_bytes': report.leftover_bytes_of('prefix'),
        'shadercache_bytes': report.leftover_bytes_of('shadercache'),
        'prefix_count': len(prefixes),
        'shadercache_count': len(caches),
        'all_libraries_accessible': report.all_libraries_accessible,
        'measure_complete': report.measure_complete,
        'game_count': len(report.games),
    }
    explanation = ctx.tr('storage.explain')
    if not report.all_libraries_accessible:
        explanation += ' ' + ctx.tr('storage.library_missing')
    if total < NOTEWORTHY_BYTES:
        return result(ID, title, Status.PASS, ctx.tr('storage.clean', size=format_bytes(total)),
                      explanation=explanation, evidence=evidence, source=EvidenceSource.STEAM_METADATA, extra=extra)
    return result(ID, title, Status.INFO,
                  ctx.tr('storage.leftovers', size=format_bytes(total), prefixes=len(prefixes), caches=len(caches)),
                  explanation=explanation, recommendation=ctx.tr('storage.rec'), evidence=evidence,
                  source=EvidenceSource.STEAM_METADATA, extra={**extra, 'compact_note': True})
