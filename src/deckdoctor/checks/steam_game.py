from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, Status
from deckdoctor.steam import library_roots, metadata

ID = 'STEAM-GAME'
TITLE = 'Selected game'


def _mapping(data: dict[str, Any]) -> dict[str, Any]:
    for key in ('installconfigstore', 'software', 'valve', 'steam', 'compattoolmapping'):
        child = data.get(key)
        if not isinstance(child, dict):
            return {}
        data = child
    return data


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f'title.{ID}')
    if ctx.appid is None:
        return result(ID, title, Status.SKIPPED, ctx.tr('game.select'))
    appid = str(ctx.appid)
    roots, _ = library_roots(ctx)
    matches: list[tuple[Path, dict[str, Any]]] = []
    for root in roots:
        data = metadata(ctx, root / f'steamapps/appmanifest_{appid}.acf')
        app = (data or {}).get('appstate')
        if isinstance(app, dict) and app.get('appid') == appid:
            matches.append((root, app))
    if not matches:
        return result(ID, title, Status.UNKNOWN, ctx.tr('game.missing', appid=appid),
                      recommendation=ctx.tr('game.missing.rec'), extra={'appid': ctx.appid})
    root, app = matches[0]
    dirname = app.get('installdir')
    safe = isinstance(dirname, str) and bool(dirname) and dirname not in {'.', '..'} and '/' not in dirname and '\\' not in dirname
    install = root / 'steamapps/common' / str(dirname) if safe else None
    exists = bool(install and ctx.exists(install))
    config = metadata(ctx, ctx.steam_root / 'config/config.vdf')
    mapping = _mapping(config or {})
    selection = mapping.get(appid, mapping.get('0', {}))
    tool = selection.get('name') if isinstance(selection, dict) else None
    evidence = [f'AppID: {appid}', f'Manifest: {root}/steamapps/appmanifest_{appid}.acf',
                f'Install: {install or "invalid installdir"}',
                f'StateFlags: {app.get("stateflags", "unknown")}',
                f'Compat tool override: {tool or "not observed (Steam automatic selection is not resolved)"}']
    runtimes: list[str] = []
    for library in roots:
        try:
            manifests = sorted((library / 'steamapps').glob('appmanifest_*.acf'))[:1000]
        except OSError:
            continue
        for manifest in manifests:
            if ctx.timed_out():
                break
            runtime_data = metadata(ctx, manifest, max_bytes=64_000)
            state = (runtime_data or {}).get('appstate')
            name = state.get('name', '') if isinstance(state, dict) else ''
            if isinstance(name, str) and (name.lower().startswith('proton') or 'steam linux runtime' in name.lower()):
                runtimes.append(name)
    evidence.append('Installed compatibility/runtime manifests (not proof of use): ' + ', '.join(runtimes))
    prefix = root / f'steamapps/compatdata/{appid}/pfx'
    evidence.append(f'Proton prefix present: {ctx.exists(prefix)}')
    log = ctx.home / f'steam-{appid}.log'
    log_info: dict[str, Any] = {'path': str(log), 'present': False}
    try:
        stat = log.stat()
        log_info.update(present=True, size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat())
        evidence.append(f'Proton log: {log} ({stat.st_size} bytes, {log_info["modified"]})')
        header = ctx.read_text(log, max_bytes=4096) or ''
        log_info['header'] = [line[:300] for line in header.splitlines() if line.startswith(('Proton:', 'SteamGameId:', 'Command:', 'Options:'))][:8]
        evidence.extend(log_info['header'])
    except OSError:
        pass
    return result(ID, title, Status.INFO if exists and len(matches) == 1 else Status.WARNING,
                  ctx.tr('game.found', name=app.get('name', appid), appid=appid) if exists else ctx.tr('game.install_missing', appid=appid),
                  explanation=ctx.tr('game.limits'), recommendation=ctx.tr('game.rec'), evidence=evidence,
                  extra={'appid': ctx.appid, 'name': app.get('name'), 'library': str(root),
                         'install_present': exists, 'manifest_count': len(matches), 'compat_tool_override': tool,
                         'installed_runtimes': runtimes, 'prefix_present': ctx.exists(prefix), 'log': log_info, 'compact_note': True})
