"""Read-only observations; device presence does not establish functional health."""
from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, Status


def battery(ctx: DiagnosticContext) -> CheckResult:
    batteries = []
    try:
        supplies = sorted((ctx.sys_root / 'class/power_supply').iterdir())
    except OSError:
        supplies = []
    for path in supplies:
        if (ctx.read_text(path / 'type') or '').strip() != 'Battery':
            continue
        values = {key: (ctx.read_text(path / key) or '').strip() or None
                  for key in ('status', 'capacity', 'energy_now', 'energy_full', 'energy_full_design', 'charge_now', 'charge_full', 'charge_full_design', 'voltage_now', 'current_now', 'power_now', 'cycle_count')}
        batteries.append({'name': path.name, **values})
    readings = '; '.join(f'{b["name"]}: {b["capacity"] or "?"}% ({b["status"] or "?"})' for b in batteries)
    return result('HW-BATTERY', ctx.tr('title.HW-BATTERY'), Status.INFO if batteries else Status.UNKNOWN,
                  ctx.tr('battery.summary', count=len(batteries), readings=readings), recommendation=ctx.tr('battery.rec'),
                  evidence=[str(b) for b in batteries], extra={'batteries': batteries, 'compact_note': bool(ctx.symptom == 'battery')})


def controllers(ctx: DiagnosticContext) -> CheckResult:
    text = ctx.read_text(ctx.proc_root / 'bus/input/devices')
    devices = []
    for block in (text or '').split('\n\n'):
        rows = block.splitlines()
        name = next((r.partition('=')[2].strip('"') for r in rows if r.startswith('N: Name=')), '')
        handlers = next((r.partition('=')[2] for r in rows if r.startswith('H: Handlers=')), '')
        # Only label joystick handlers; a keyboard/touchpad is not necessarily a controller.
        if any(h.startswith('js') and h[2:].isdigit() for h in handlers.split()):
            devices.append({'name': name, 'handlers': handlers})
    return result('HW-INPUT', ctx.tr('title.HW-INPUT'), Status.INFO if devices else Status.UNKNOWN,
                  ctx.tr('input.summary', count=len(devices)), recommendation=ctx.tr('input.rec'),
                  evidence=[f'{d["name"]}: {d["handlers"]}' for d in devices],
                  extra={'devices': devices, 'source_readable': text is not None, 'compact_note': bool(ctx.symptom == 'controller')})


def resume(ctx: DiagnosticContext) -> CheckResult:
    proc = ctx.run(['journalctl', '-b', '-k', '--no-pager', '-n', '400', '-o', 'short-iso'], timeout=5)
    lines = [line for line in proc.stdout.splitlines() if any(term in line.lower() for term in
             ('suspend', 'resume', 'wakeup', 'acpi: pm'))][-30:]
    return result('HW-RESUME', ctx.tr('title.HW-RESUME'), Status.INFO if proc.ok and lines else Status.UNKNOWN,
                  ctx.tr('resume.summary', count=len(lines)), recommendation=ctx.tr('resume.rec'),
                  evidence=lines if proc.ok else [proc.stderr[:500] or proc.error or f'exit {proc.exit_code}'],
                  extra={'events': lines, 'journal_readable': proc.ok, 'compact_note': bool(ctx.symptom == 'resume')})


def displays(ctx: DiagnosticContext) -> CheckResult:
    connectors = []
    for path in sorted((ctx.sys_root / 'class/drm').glob('card*-*')):
        status = (ctx.read_text(path / 'status') or '').strip()
        if status:
            connectors.append({'connector': path.name, 'status': status,
                               'modes': (ctx.read_text(path / 'modes') or '').splitlines()[:8]})
    return result('HW-DISPLAY', ctx.tr('title.HW-DISPLAY'), Status.INFO if connectors else Status.UNKNOWN,
                  ctx.tr('display.summary', count=sum(c['status'] == 'connected' for c in connectors)),
                  recommendation=ctx.tr('display.rec'), evidence=[str(c) for c in connectors],
                  extra={'connectors': connectors, 'compact_note': ctx.symptom == 'dock'})


def audio(ctx: DiagnosticContext) -> CheckResult:
    proc = ctx.run(['pactl', 'info'], timeout=5)
    lines = [line for line in proc.stdout.splitlines() if line.startswith(('Server Name:', 'Default Sink:', 'Default Source:', 'Server Version:'))]
    return result('HW-AUDIO', ctx.tr('title.HW-AUDIO'), Status.INFO if proc.ok and lines else Status.UNKNOWN,
                  ctx.tr('audio.summary' if proc.ok and lines else 'audio.unknown'),
                  recommendation=ctx.tr('audio.rec'), evidence=lines or [proc.stderr[:300]],
                  extra={'server': lines, 'compact_note': ctx.symptom == 'audio'})


def performance(ctx: DiagnosticContext) -> CheckResult:
    readings = {name: (ctx.read_text(ctx.proc_root / name, max_bytes=8192) or '').strip()
                for name in ('loadavg', 'pressure/cpu', 'pressure/memory', 'pressure/io')}
    return result('HW-PERFORMANCE', ctx.tr('title.HW-PERFORMANCE'), Status.INFO if any(readings.values()) else Status.UNKNOWN,
                  ctx.tr('performance.summary'), recommendation=ctx.tr('performance.rec'),
                  evidence=[f'{key}: {value}' for key, value in readings.items() if value],
                  extra={'readings': readings, 'compact_note': ctx.symptom == 'performance'})
