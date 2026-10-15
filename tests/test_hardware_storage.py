from __future__ import annotations

import struct
from pathlib import Path

import pytest

from deckdoctor import storage
from deckdoctor.checks import handheld, steam_storage
from deckdoctor.device import classify, identify
from deckdoctor.models import Status
from deckdoctor.sensors import Sampler, read_battery
from tests.conftest import make_ctx


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- device


@pytest.mark.parametrize(
    ("vendor", "product", "version", "model"),
    [
        ("Valve", "Jupiter", "1", "Steam Deck LCD"),
        ("Valve", "Galileo", "1", "Steam Deck OLED"),
        ("ASUSTeK COMPUTER INC.", "ROG Ally RC71L_RC71L", "1.0", "ROG Ally"),
        ("ASUSTeK COMPUTER INC.", "ROG Ally X RC72LA_RC72LA", "1.0", "ROG Ally X"),
        ("LENOVO", "83E1", "Legion Go 8APU1", "Legion Go"),
        ("AYANEO", "KUN", "", "AYANEO KUN"),
    ],
)
def test_classify_known_handhelds(vendor: str, product: str, version: str, model: str) -> None:
    name, _family, known = classify(vendor, product, version)
    assert name == model
    assert known


def test_classify_unknown_desktop_is_not_known() -> None:
    name, _family, known = classify("Dell Inc.", "OptiPlex 7010")
    assert not known
    assert "OptiPlex" in name


def test_identify_reads_dmi_and_cpu(tmp_path: Path) -> None:
    dmi = tmp_path / "sys/class/dmi/id"
    write(dmi / "sys_vendor", "Valve\n")
    write(dmi / "product_name", "Galileo\n")
    write(dmi / "chassis_type", "31\n")
    write(tmp_path / "proc/cpuinfo", "processor : 0\nmodel name : AMD Custom APU 0932\n")
    device = identify(tmp_path / "sys", tmp_path / "proc")
    assert device.model == "Steam Deck OLED"
    assert device.is_steam_deck and device.likely_handheld
    assert device.apu == "AMD Custom APU 0932"


# --------------------------------------------------------------------------- sensors


def fake_deck_sys(root: Path) -> None:
    gpu = root / "class/hwmon/hwmon0"
    write(gpu / "name", "amdgpu")
    write(gpu / "temp1_input", "61000")
    write(gpu / "power1_input", "9500000")
    write(gpu / "power1_cap", "15000000")
    write(gpu / "freq1_input", "1600000000")
    write(gpu / "device/gpu_busy_percent", "73")
    fan = root / "class/hwmon/hwmon1"
    write(fan / "name", "steamdeck_hwmon")
    write(fan / "fan1_input", "3100")
    write(fan / "in0_label", "PD Contract Voltage")
    write(fan / "in0_input", "15000")
    write(fan / "curr1_label", "PD Contract Current")
    write(fan / "curr1_input", "3000")
    write(fan / "temp1_label", "Battery Temp")
    write(fan / "temp1_input", "33000")
    write(fan / "max_battery_charge_level", "80")
    nvme = root / "class/hwmon/hwmon2"
    write(nvme / "name", "nvme")
    write(nvme / "temp1_input", "48000")
    write(nvme / "temp1_max", "84000")
    bat = root / "class/power_supply/BAT1"
    write(bat / "type", "Battery")
    write(bat / "status", "Discharging")
    write(bat / "capacity", "64")
    write(bat / "voltage_now", "8000000")
    write(bat / "voltage_min_design", "7700000")
    write(bat / "current_now", "1000000")
    write(bat / "charge_now", "3000000")
    write(bat / "charge_full", "5000000")
    write(bat / "charge_full_design", "5300000")
    ac = root / "class/power_supply/ACAD"
    write(ac / "type", "Mains")
    write(ac / "online", "0")


def test_battery_health_and_time_left(tmp_path: Path) -> None:
    fake_deck_sys(tmp_path)
    reading = read_battery(tmp_path / "class/power_supply/BAT1")
    assert reading.percent == 64
    assert reading.health_percent == pytest.approx(94.3, abs=0.1)
    assert reading.power_w == pytest.approx(8.0)
    assert reading.hours_left == pytest.approx(3.0)


def test_sampler_reads_deck_telemetry(tmp_path: Path) -> None:
    sys_root, proc = tmp_path / "sys", tmp_path / "proc"
    fake_deck_sys(sys_root)
    write(proc / "stat", "cpu 100 0 100 800 0 0 0 0\n")
    write(proc / "meminfo", "MemTotal: 16000000 kB\nMemAvailable: 4000000 kB\nSwapTotal: 1000 kB\nSwapFree: 1000 kB\n")
    sampler = Sampler(sys_root, proc)
    first = sampler.sample()
    assert first.cpu_percent is None
    write(proc / "stat", "cpu 200 0 200 900 0 0 0 0\n")
    sample = sampler.sample()
    assert sample.cpu_percent == pytest.approx(66.7, abs=0.1)
    assert sample.gpu_percent == 73
    assert sample.apu_power_w == pytest.approx(9.5)
    assert sample.tdp_limit_w == pytest.approx(15)
    assert sample.gpu_freq_mhz == pytest.approx(1600)
    assert sample.fan_rpm == 3100
    assert sample.nvme_temp_c == pytest.approx(48)
    assert sample.charger_w == pytest.approx(45)
    assert sample.on_ac is False
    assert sample.mem_used_percent == pytest.approx(75)
    assert sample.battery is not None
    assert sample.battery.temp_c == pytest.approx(33)
    assert sample.battery.charge_limit == 80


def test_thermal_check_warns_when_hot_with_stopped_fan(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    fake_deck_sys(ctx.sys_root)
    assert handheld.thermals(ctx).status == Status.PASS
    write(ctx.sys_root / "class/hwmon/hwmon0/temp1_input", "93000")
    write(ctx.sys_root / "class/hwmon/hwmon1/fan1_input", "0")
    result = handheld.thermals(ctx)
    assert result.status == Status.WARNING


def test_thermal_check_unknown_without_sensors(tmp_path: Path) -> None:
    assert handheld.thermals(make_ctx(tmp_path)).status == Status.UNKNOWN


# --------------------------------------------------------------------------- storage


def binary_vdf(shortcuts: dict[int, str]) -> bytes:
    out = b"\x00shortcuts\x00"
    for index, (appid, name) in enumerate(shortcuts.items()):
        out += b"\x00" + str(index).encode() + b"\x00"
        out += b"\x02appid\x00" + struct.pack("<i", appid - (1 << 32) if appid >= 1 << 31 else appid)
        out += b"\x01AppName\x00" + name.encode() + b"\x00"
        out += b"\x08"
    return out + b"\x08\x08"


def test_parse_binary_vdf_shortcuts() -> None:
    data = storage.parse_binary_vdf(binary_vdf({3000000000: "Heroic Game"}))
    entry = data["shortcuts"]["0"]
    assert entry["appid"] & 0xFFFFFFFF == 3000000000
    assert entry["appname"] == "Heroic Game"


def test_parse_binary_vdf_rejects_truncated() -> None:
    with pytest.raises(ValueError):
        storage.parse_binary_vdf(b"\x00shortcuts\x00\x01AppName\x00abc")


def steam_library(tmp_path: Path) -> tuple[object, Path]:
    ctx = make_ctx(tmp_path)
    steam = ctx.steam_root
    apps = steam / "steamapps"
    sd = tmp_path / "media/mmcblk0p1"
    write(apps / "libraryfolders.vdf",
          f'"libraryfolders" {{ "0" {{ "path" "{steam}" "apps" {{ "10" "1" }} }}'
          f' "1" {{ "path" "{sd}" "apps" {{ "20" "1" }} }} }}')
    write(apps / "appmanifest_10.acf",
          '"AppState" { "appid" "10" "name" "Internal Game" "installdir" "IG" "SizeOnDisk" "1000"'
          ' "StateFlags" "6" "BytesToDownload" "500" "BytesDownloaded" "100" }')
    write(sd / "steamapps/appmanifest_20.acf",
          '"AppState" { "appid" "20" "name" "SD Game" "installdir" "SG" "SizeOnDisk" "2000" "StateFlags" "4" }')
    write(sd / "steamapps/appmanifest_228980.acf",
          '"AppState" { "appid" "228980" "name" "Steamworks Common Redistributables" "StateFlags" "4" }')
    write(apps / "compatdata/10/config_info", "GE-Proton9-20\n/path\n")
    write(apps / "compatdata/20/pfx/system.reg", "x" * 300)  # microSD game, prefix on internal
    write(apps / "compatdata/30/pfx/user.reg", "y" * 700)  # uninstalled
    write(apps / "compatdata/0/pfx/user.reg", "z")  # Steam's own
    write(apps / "compatdata/3000000000/pfx/user.reg", "s" * 50)  # live shortcut
    write(apps / "compatdata/3100000000/pfx/user.reg", "s" * 60)  # removed shortcut
    write(apps / "shadercache/40/cache.bin", "c" * 900)
    user = steam / "userdata/123/config"
    user.mkdir(parents=True)
    (user / "shortcuts.vdf").write_bytes(binary_vdf({3000000000: "Heroic Game"}))
    write(user / "localconfig.vdf",
          '"UserLocalConfigStore" { "Software" { "Valve" { "Steam" { "apps" {'
          ' "10" { "LastPlayed" "1760000000" "Playtime" "125" "cloud" { "last_sync_state" "synchronized" } }'
          ' "30" { "LastPlayed" "1700000000" "cloud" { "last_sync_state" "synchronized" } }'
          ' } } } } }')
    return ctx, sd


def test_scan_finds_games_history_and_leftovers(tmp_path: Path) -> None:
    ctx, _sd = steam_library(tmp_path)
    report = storage.scan(ctx)  # type: ignore[arg-type]
    names = {g.name: g for g in report.games}
    assert set(names) == {"Internal Game", "SD Game"}
    assert [t.name for t in report.tools] == ["Steamworks Common Redistributables"]
    internal = names["Internal Game"]
    assert internal.proton == "GE-Proton9-20"
    assert internal.update_pending and internal.update_bytes == 400
    assert internal.playtime_minutes == 125 and internal.last_played == 1760000000
    assert internal.cloud_synced is True
    assert names["SD Game"].library_kind == "microsd"
    assert names["SD Game"].prefix_path and names["SD Game"].prefix_path.endswith("compatdata/20")
    leftovers = {(item.kind, item.appid): item for item in report.leftovers}
    assert set(leftovers) == {("prefix", 30), ("prefix", 3100000000), ("shadercache", 40)}
    assert leftovers[("prefix", 30)].reason == "uninstalled"
    assert leftovers[("prefix", 30)].cloud_synced is True
    assert leftovers[("prefix", 3100000000)].reason == "shortcut_removed"
    assert report.pending_update_bytes == 400
    storage.measure_report(report)
    assert report.measured and report.measure_complete
    # Sizes are allocated blocks (space a deletion would free), so at least the apparent size.
    assert (leftovers[("prefix", 30)].size or 0) >= 700
    assert report.leftover_bytes == sum(item.size or 0 for item in report.leftovers)


def test_unplugged_library_games_are_never_leftovers(tmp_path: Path) -> None:
    ctx, sd = steam_library(tmp_path)
    for path in sorted(sd.rglob("*"), reverse=True):
        path.unlink() if path.is_file() else path.rmdir()
    sd.rmdir()
    report = storage.scan(ctx)  # type: ignore[arg-type]
    assert not report.all_libraries_accessible
    assert 20 not in {item.appid for item in report.leftovers}


def test_shortcut_prefixes_kept_when_shortcuts_unreadable(tmp_path: Path) -> None:
    ctx, _sd = steam_library(tmp_path)
    (ctx.steam_root / "userdata/123/config/shortcuts.vdf").unlink()
    report = storage.scan(ctx)  # type: ignore[arg-type]
    assert all(item.appid < storage.SHORTCUT_MIN_ID for item in report.leftovers)


def test_library_kind_by_path(tmp_path: Path) -> None:
    home = tmp_path / "home"
    assert storage.library_kind(home / ".local/share/Steam", home, tmp_path) == "internal"
    assert storage.library_kind(Path("/run/media/mmcblk0p1"), home, tmp_path) == "microsd"
    assert storage.library_kind(Path("/run/media/deck/USB"), home, tmp_path) == "external"


def test_measure_respects_deadline(tmp_path: Path) -> None:
    write(tmp_path / "a/b/c.bin", "x" * 10)
    size, complete = storage.measure(tmp_path / "a")
    assert size >= 10 and complete
    _size, complete = storage.measure(tmp_path / "a", deadline=0.0)
    assert not complete


def test_storage_check_reports_leftovers(tmp_path: Path) -> None:
    ctx, _sd = steam_library(tmp_path)
    result = steam_storage.run(ctx)  # type: ignore[arg-type]
    assert result.status in {Status.PASS, Status.INFO}
    assert (ctx.facts.storage_leftover_bytes or 0) >= 700 + 60 + 900  # type: ignore[attr-defined]
