"""Live hardware telemetry from sysfs/procfs. Read-only and vendor-neutral.

Every reading is optional: a missing file means "not exposed by this kernel/device",
never zero. Callers must render ``None`` as unavailable.
"""
from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_CPU_TEMP_CHIPS = ("k10temp", "zenpower", "coretemp", "cpu_thermal")
_CHARGER_NAMES = ("ac", "acad", "adp", "usb", "ucsi")


@dataclass
class BatteryReading:
    name: str
    percent: float | None = None
    status: str = ""
    power_w: float | None = None
    health_percent: float | None = None
    cycles: int | None = None
    hours_left: float | None = None
    temp_c: float | None = None
    charge_limit: int | None = None
    design_wh: float | None = None
    full_wh: float | None = None

    @property
    def charging(self) -> bool:
        return self.status.lower() == "charging"


@dataclass
class ProcessUsage:
    pid: int
    name: str
    cpu_percent: float
    rss_bytes: int
    count: int = 1


@dataclass
class Sample:
    timestamp: float
    cpu_percent: float | None = None
    cpu_freq_mhz: float | None = None
    cpu_temp_c: float | None = None
    gpu_percent: float | None = None
    gpu_freq_mhz: float | None = None
    gpu_temp_c: float | None = None
    apu_power_w: float | None = None
    tdp_limit_w: float | None = None
    tdp_max_w: float | None = None
    fan_rpm: int | None = None
    nvme_temp_c: float | None = None
    nvme_temp_max_c: float | None = None
    vram_used: int | None = None
    vram_total: int | None = None
    mem_total: int | None = None
    mem_available: int | None = None
    swap_total: int | None = None
    swap_free: int | None = None
    on_ac: bool | None = None
    charger_w: float | None = None
    battery: BatteryReading | None = None
    load: tuple[float, float, float] | None = None
    processes: list[ProcessUsage] = field(default_factory=list)

    @property
    def apu_temp_c(self) -> float | None:
        values = [v for v in (self.cpu_temp_c, self.gpu_temp_c) if v is not None]
        return max(values) if values else None

    @property
    def mem_used_percent(self) -> float | None:
        if not self.mem_total or self.mem_available is None:
            return None
        return 100.0 * (self.mem_total - self.mem_available) / self.mem_total

    @property
    def swap_used(self) -> int | None:
        if self.swap_total is None or self.swap_free is None:
            return None
        return self.swap_total - self.swap_free

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["apu_temp_c"] = self.apu_temp_c
        return data


def _read(path: Path, limit: int = 8192) -> str | None:
    try:
        with path.open("rb") as stream:
            return stream.read(limit).decode("utf-8", errors="replace").strip()
    except OSError:
        return None


def _num(path: Path) -> float | None:
    text = _read(path, 64)
    if not text:
        return None
    try:
        return float(text.split()[0])
    except (ValueError, IndexError):
        return None


def read_battery(path: Path) -> BatteryReading:
    reading = BatteryReading(name=path.name, status=_read(path / "status", 64) or "")
    reading.percent = _num(path / "capacity")
    cycles = _num(path / "cycle_count")
    reading.cycles = int(cycles) if cycles else None
    volts = _num(path / "voltage_now")
    volts_design = _num(path / "voltage_min_design") or volts
    power = _num(path / "power_now")
    current = _num(path / "current_now")
    if power is not None:
        reading.power_w = abs(power) / 1e6
    elif current is not None and volts is not None:
        reading.power_w = abs(current) * volts / 1e12
    energy_full = _num(path / "energy_full")
    energy_design = _num(path / "energy_full_design")
    energy_now = _num(path / "energy_now")
    charge_full = _num(path / "charge_full")
    charge_design = _num(path / "charge_full_design")
    charge_now = _num(path / "charge_now")
    if energy_full and energy_design:
        reading.health_percent = 100.0 * energy_full / energy_design
        reading.full_wh, reading.design_wh = energy_full / 1e6, energy_design / 1e6
    elif charge_full and charge_design:
        reading.health_percent = 100.0 * charge_full / charge_design
        if volts_design:
            reading.full_wh = charge_full * volts_design / 1e12
            reading.design_wh = charge_design * volts_design / 1e12
    if reading.health_percent is not None:
        reading.health_percent = min(reading.health_percent, 100.0)
    status = reading.status.lower()
    if status == "discharging":
        if energy_now and power:
            reading.hours_left = energy_now / abs(power)
        elif charge_now and current:
            reading.hours_left = charge_now / abs(current)
    elif status == "charging":
        if energy_full and energy_now is not None and power:
            reading.hours_left = max(0.0, energy_full - energy_now) / abs(power)
        elif charge_full and charge_now is not None and current:
            reading.hours_left = max(0.0, charge_full - charge_now) / abs(current)
    if reading.hours_left is not None and not 0 <= reading.hours_left < 72:
        reading.hours_left = None
    if reading.temp_c is None:
        temp = _num(path / "temp")
        reading.temp_c = temp / 10.0 if temp is not None else None
    limit = _num(path / "charge_control_end_threshold")
    if limit and 0 < limit < 100:
        reading.charge_limit = int(limit)
    return reading


@dataclass
class _Hwmon:
    name: str
    path: Path


class Sampler:
    """Keeps the previous CPU/process counters so each ``sample()`` returns rates."""

    def __init__(self, sys_root: Path = Path("/sys"), proc_root: Path = Path("/proc")) -> None:
        self.sys_root = sys_root
        self.proc_root = proc_root
        self._prev_cpu: tuple[int, int] | None = None
        self._prev_proc: dict[int, int] = {}
        self._prev_proc_time: float | None = None
        self._clock_ticks = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
        self._page_size = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096
        self._hwmons = self._discover()

    def _discover(self) -> list[_Hwmon]:
        found: list[_Hwmon] = []
        try:
            entries = sorted((self.sys_root / "class/hwmon").iterdir())
        except OSError:
            return found
        for entry in entries:
            name = _read(entry / "name", 128)
            if name:
                found.append(_Hwmon(name, entry))
        return found

    def _chip(self, *names: str) -> _Hwmon | None:
        for chip in self._hwmons:
            if chip.name in names:
                return chip
        return None

    def _cpu_percent(self) -> float | None:
        text = _read(self.proc_root / "stat", 4096)
        if not text:
            return None
        first = text.splitlines()[0].split()
        if not first or first[0] != "cpu":
            return None
        try:
            values = [int(x) for x in first[1:]]
        except ValueError:
            return None
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values[:8])
        prev = self._prev_cpu
        self._prev_cpu = (total, idle)
        if prev is None or total <= prev[0]:
            return None
        busy = (total - prev[0]) - (idle - prev[1])
        return max(0.0, min(100.0, 100.0 * busy / (total - prev[0])))

    def _cpu_freq(self) -> float | None:
        freqs: list[float] = []
        try:
            cpus = list((self.sys_root / "devices/system/cpu").glob("cpu[0-9]*"))
        except OSError:
            return None
        for cpu in cpus:
            value = _num(cpu / "cpufreq/scaling_cur_freq")
            if value:
                freqs.append(value / 1000.0)
        return sum(freqs) / len(freqs) if freqs else None

    def _cpu_temp(self) -> float | None:
        for name in _CPU_TEMP_CHIPS:
            chip = self._chip(name)
            if chip is None:
                continue
            for idx in range(1, 6):
                label = (_read(chip.path / f"temp{idx}_label", 64) or "").lower()
                if idx == 1 or label in {"tctl", "tdie", "package id 0"}:
                    value = _num(chip.path / f"temp{idx}_input")
                    if value is not None:
                        return value / 1000.0
        return None

    def _gpu(self, sample: Sample) -> None:
        chip = self._chip("amdgpu")
        if chip is None:
            return
        temp = _num(chip.path / "temp1_input")
        sample.gpu_temp_c = temp / 1000.0 if temp is not None else None
        power = _num(chip.path / "power1_input")
        if power is None:
            power = _num(chip.path / "power1_average")
        sample.apu_power_w = power / 1e6 if power is not None else None
        cap = _num(chip.path / "power1_cap")
        sample.tdp_limit_w = cap / 1e6 if cap else None
        cap_max = _num(chip.path / "power1_cap_max")
        sample.tdp_max_w = cap_max / 1e6 if cap_max else None
        freq = _num(chip.path / "freq1_input")
        sample.gpu_freq_mhz = freq / 1e6 if freq is not None else None
        device = chip.path / "device"
        busy = _num(device / "gpu_busy_percent")
        sample.gpu_percent = busy
        used = _num(device / "mem_info_vram_used")
        total = _num(device / "mem_info_vram_total")
        sample.vram_used = int(used) if used is not None else None
        sample.vram_total = int(total) if total is not None else None

    def _fan(self) -> int | None:
        for chip in self._hwmons:
            for idx in range(1, 4):
                value = _num(chip.path / f"fan{idx}_input")
                if value is not None:
                    return int(value)
        return None

    def _nvme(self, sample: Sample) -> None:
        chip = self._chip("nvme")
        if chip is None:
            return
        temp = _num(chip.path / "temp1_input")
        sample.nvme_temp_c = temp / 1000.0 if temp is not None else None
        limit = _num(chip.path / "temp1_max")
        sample.nvme_temp_max_c = limit / 1000.0 if limit else None

    def _memory(self, sample: Sample) -> None:
        text = _read(self.proc_root / "meminfo", 16384) or ""
        values: dict[str, int] = {}
        for line in text.splitlines():
            key, _, rest = line.partition(":")
            parts = rest.split()
            if parts and parts[0].isdigit():
                values[key] = int(parts[0]) * 1024
        sample.mem_total = values.get("MemTotal")
        sample.mem_available = values.get("MemAvailable")
        sample.swap_total = values.get("SwapTotal")
        sample.swap_free = values.get("SwapFree")

    def _power(self, sample: Sample) -> None:
        root = self.sys_root / "class/power_supply"
        try:
            supplies = sorted(root.iterdir())
        except OSError:
            supplies = []
        battery: BatteryReading | None = None
        for supply in supplies:
            kind = (_read(supply / "type", 64) or "").lower()
            if kind == "battery" and battery is None and (_read(supply / "scope", 64) or "").lower() != "device":
                battery = read_battery(supply)
            elif kind in {"mains", "usb", "usb_pd"} or supply.name.lower().startswith(_CHARGER_NAMES):
                online = _num(supply / "online")
                if online is not None:
                    sample.on_ac = bool(online) or bool(sample.on_ac)
        # Steam Deck exposes the negotiated USB-PD contract; other devices rarely do.
        for chip in self._hwmons:
            labels = {(_read(chip.path / f"{kind}_label", 64) or "").lower(): kind for kind in ("in0", "curr1")}
            if "pd contract voltage" in labels and "pd contract current" in labels:
                volts = _num(chip.path / "in0_input")
                amps = _num(chip.path / "curr1_input")
                if volts and amps:
                    sample.charger_w = round(volts / 1000.0 * amps / 1000.0, 1)
                if battery is not None:
                    temp = _num(chip.path / "temp1_input")
                    label = (_read(chip.path / "temp1_label", 64) or "").lower()
                    if temp is not None and "battery" in label:
                        battery.temp_c = temp / 1000.0
                    limit = _num(chip.path / "max_battery_charge_level")
                    if limit and 0 < limit < 100:
                        battery.charge_limit = int(limit)
        sample.battery = battery

    def _load(self) -> tuple[float, float, float] | None:
        text = _read(self.proc_root / "loadavg", 256)
        try:
            parts = (text or "").split()
            return float(parts[0]), float(parts[1]), float(parts[2])
        except (ValueError, IndexError):
            return None

    def _processes(self, limit: int) -> list[ProcessUsage]:
        now = time.monotonic()
        current: dict[int, int] = {}
        meta: dict[int, tuple[str, int]] = {}
        try:
            entries = os.scandir(self.proc_root)
        except OSError:
            return []
        with entries:
            for entry in entries:
                if not entry.name.isdigit():
                    continue
                pid = int(entry.name)
                text = _read(Path(entry.path) / "stat", 2048)
                if not text or ")" not in text:
                    continue
                name = text[text.find("(") + 1:text.rfind(")")]
                fields = text[text.rfind(")") + 2:].split()
                try:
                    ticks = int(fields[11]) + int(fields[12])
                    rss = int(fields[21]) * self._page_size
                except (IndexError, ValueError):
                    continue
                current[pid] = ticks
                meta[pid] = (name, rss)
        prev, prev_time = self._prev_proc, self._prev_proc_time
        self._prev_proc, self._prev_proc_time = current, now
        if prev_time is None or now <= prev_time:
            return []
        elapsed = (now - prev_time) * self._clock_ticks * (os.cpu_count() or 1)
        grouped: dict[str, ProcessUsage] = {}
        for pid, ticks in current.items():
            name, rss = meta[pid]
            pct = 100.0 * (ticks - prev[pid]) / elapsed if pid in prev and ticks >= prev[pid] else 0.0
            row = grouped.get(name)
            if row is None:
                grouped[name] = ProcessUsage(pid, name, pct, rss)
            else:
                row.cpu_percent += pct
                row.rss_bytes += rss
                row.count += 1
        rows = sorted(grouped.values(), key=lambda row: (row.cpu_percent, row.rss_bytes), reverse=True)
        return rows[:limit]

    def sample(self, *, processes: int = 0) -> Sample:
        sample = Sample(timestamp=time.time())
        sample.cpu_percent = self._cpu_percent()
        sample.cpu_freq_mhz = self._cpu_freq()
        sample.cpu_temp_c = self._cpu_temp()
        self._gpu(sample)
        sample.fan_rpm = self._fan()
        self._nvme(sample)
        self._memory(sample)
        self._power(sample)
        sample.load = self._load()
        if processes:
            if self._prev_proc_time is None:
                self._processes(0)
                time.sleep(0.25)
            sample.processes = self._processes(processes)
        else:
            # A baseline from minutes ago would average CPU over the whole gap.
            self._prev_proc_time = None
        return sample


def snapshot(sys_root: Path = Path("/sys"), proc_root: Path = Path("/proc"), *, interval: float = 0.25) -> Sample:
    """Two readings ``interval`` apart so CPU usage is a rate rather than unknown."""
    sampler = Sampler(sys_root, proc_root)
    sampler.sample()
    time.sleep(interval)
    return sampler.sample()
