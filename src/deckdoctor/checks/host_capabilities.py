from __future__ import annotations

import os

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, Status

ID = 'HOST-CAPABILITIES'
TITLE = 'Hardware and session'
TOOLS = ('steam', 'flatpak', 'gamescope', 'atomupd-manager', 'rpm-ostree', 'bootc', 'pacman', 'inputplumber', 'hhd')


def run(ctx: DiagnosticContext) -> CheckResult:
    vendor = (ctx.read_text(ctx.sys_root / 'class/dmi/id/sys_vendor') or '').strip()
    product = (ctx.read_text(ctx.sys_root / 'class/dmi/id/product_name') or '').strip()
    session = os.environ.get('XDG_SESSION_TYPE', 'unknown')
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')
    available = {tool: ctx.which(tool) for tool in TOOLS}
    services = {}
    for unit in ('inputplumber.service', f'hhd@{ctx.user}.service', 'gamescope-session.service'):
        proc = ctx.run(['systemctl', 'show', unit, '--property=LoadState,ActiveState,SubState'], timeout=3)
        services[unit] = proc.stdout.strip() if proc.ok else 'unknown'
    data = {'vendor': vendor, 'product': product, 'session_type': session, 'desktop': desktop,
            'steam_root': str(ctx.steam_root), 'tools': available, 'services': services, 'os': ctx.load_os_release()}
    evidence = [f'{tool}: {path}' for tool, path in available.items() if path]
    evidence.extend(f'{unit}: {state}' for unit, state in services.items())
    evidence.append(f'Steam: {ctx.steam_root}')
    return result(ID, ctx.tr(f'title.{ID}'), Status.INFO,
                  ctx.tr('host.summary', hardware=' '.join(filter(None, (vendor, product))) or 'unknown',
                         session=f'{desktop} / {session}'),
                  explanation=ctx.tr('host.limits'), evidence=evidence, extra=data)
