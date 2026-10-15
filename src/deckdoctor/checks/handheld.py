"""Read-only observations; device presence does not establish functional health."""
from __future__ import annotations

from typing import Any

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, Status
from deckdoctor.sensors import Sampler, read_battery

WORN_BATTERY_PERCENT = 70.0
HOT_APU_C = 90.0
HOT_BATTERY_C = 50.0
FAN_EXPECTED_ABOVE_C = 75.0


def battery(ctx: DiagnosticContext) -> CheckResult:
    batteries = []
    try:
        supplies = sorted((ctx.sys_root / 'class/power_supply').iterdir())
    except OSError:
        supplies = []
    for path in supplies:
        if (ctx.read_text(path / 'type') or '').strip() != 'Battery':
            continue
        values: dict[str, Any] = {key: (ctx.read_text(path / key) or '').strip() or None
                                  for key in ('status', 'capacity', 'energy_now', 'energy_full', 'energy_full_design', 'charge_now', 'charge_full', 'charge_full_design', 'voltage_now', 'current_now', 'power_now', 'cycle_count')}
        derived = read_battery(path)
        values.update(health_percent=_round(derived.health_percent), power_w=_round(derived.power_w, 2),
                      hours_left=_round(derived.hours_left, 2))
        batteries.append({'name': path.name, **values})

    def describe(b: dict[str, Any]) -> str:
        text = f'{b["name"]}: {b["capacity"] or "?"}% ({b["status"] or "?"})'
        if b['health_percent'] is not None:
            text += ', ' + ctx.tr('battery.health', health=f'{b["health_percent"]:.0f}')
        return text

    readings = '; '.join(describe(b) for b in batteries)
    worn = [b for b in batteries if b['health_percent'] is not None and b['health_percent'] < WORN_BATTERY_PERCENT]
    status = Status.WARNING if worn else Status.INFO if batteries else Status.UNKNOWN
    return result('HW-BATTERY', ctx.tr('title.HW-BATTERY'), status,
                  ctx.tr('battery.summary', count=len(batteries), readings=readings),
                  explanation=ctx.tr('battery.worn.explain') if worn else '',
                  recommendation=ctx.tr('battery.worn.rec' if worn else 'battery.rec'),
                  evidence=[str(b) for b in batteries],
                  extra={'batteries': batteries, 'compact_note': bool(ctx.symptom == 'battery')})


def _round(value: float | None, digits: int = 1) -> float | None:
    return round(value, digits) if value is not None else None


def thermals(ctx: DiagnosticContext) -> CheckResult:
    sample = Sampler(ctx.sys_root, ctx.proc_root).sample()
    battery_temp = sample.battery.temp_c if sample.battery else None
    readings = {'apu_c': sample.apu_temp_c, 'cpu_c': sample.cpu_temp_c, 'gpu_c': sample.gpu_temp_c,
                'nvme_c': sample.nvme_temp_c, 'nvme_max_c': sample.nvme_temp_max_c,
                'battery_c': battery_temp, 'fan_rpm': sample.fan_rpm,
                'apu_power_w': sample.apu_power_w, 'tdp_limit_w': sample.tdp_limit_w}
    parts = []
    if sample.apu_temp_c is not None:
        parts.append(f'APU {sample.apu_temp_c:.0f} °C')
    if sample.nvme_temp_c is not None:
        parts.append(f'NVMe {sample.nvme_temp_c:.0f} °C')
    if battery_temp is not None:
        parts.append(f'{ctx.tr("thermal.battery")} {battery_temp:.0f} °C')
    if sample.fan_rpm is not None:
        parts.append(f'{ctx.tr("thermal.fan")} {sample.fan_rpm} RPM')
    title = ctx.tr('title.HW-THERMAL')
    evidence = [f'{key}: {value}' for key, value in readings.items() if value is not None]
    if not parts:
        return result('HW-THERMAL', title, Status.UNKNOWN, ctx.tr('thermal.unknown'), evidence=evidence,
                      extra={'readings': readings})
    issues = []
    if sample.apu_temp_c is not None and sample.apu_temp_c >= HOT_APU_C:
        issues.append(ctx.tr('thermal.apu_hot', temp=f'{sample.apu_temp_c:.0f}'))
    if sample.nvme_temp_c is not None and sample.nvme_temp_max_c and sample.nvme_temp_c >= sample.nvme_temp_max_c:
        issues.append(ctx.tr('thermal.nvme_hot', temp=f'{sample.nvme_temp_c:.0f}', limit=f'{sample.nvme_temp_max_c:.0f}'))
    if battery_temp is not None and battery_temp >= HOT_BATTERY_C:
        issues.append(ctx.tr('thermal.battery_hot', temp=f'{battery_temp:.0f}'))
    if sample.fan_rpm == 0 and sample.apu_temp_c is not None and sample.apu_temp_c >= FAN_EXPECTED_ABOVE_C:
        issues.append(ctx.tr('thermal.fan_stopped', temp=f'{sample.apu_temp_c:.0f}'))
    finding = ' · '.join(parts)
    if issues:
        return result('HW-THERMAL', title, Status.WARNING, '; '.join(issues), explanation=finding,
                      recommendation=ctx.tr('thermal.rec'), evidence=evidence, extra={'readings': readings})
    return result('HW-THERMAL', title, Status.PASS, finding, explanation=ctx.tr('thermal.limits'),
                  evidence=evidence, extra={'readings': readings, 'compact_note': ctx.symptom == 'performance'})


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
