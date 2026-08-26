from __future__ import annotations

import re
from pathlib import Path

from deckdoctor.checks._util import format_bytes, result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "SYS-DISK"
TITLE = "Disk space"

CRITICAL_FREE = 500 * 1024 * 1024
WARN_FREE = 2 * 1024 * 1024 * 1024
# SteamOS /var is ~230 MB by design; bulky dirs are bind-mounted onto /home.
SMALL_CRITICAL_RATIO = 0.10
SMALL_WARN_RATIO = 0.20
SMALL_CRITICAL_FLOOR = 20 * 1024 * 1024
_VDF_PATH = re.compile(r'"path"\s+"([^"]+)"')
_ACF_NAME = re.compile(r'"name"\s+"([^"]+)"')
_SKIP_PREFIXES = ("/dev/", "/proc/", "/sys/", "/run/user/")
_SKIP_PARTS = ("/.mount_",)
_TOOL_HINTS = (
    "proton",
    "steam linux runtime",
    "steamworks",
    "easyanticheat runtime",
    "battleye runtime",
)


def _device_id(path: Path) -> int | None:
    try:
        return path.stat().st_dev
    except OSError:
        return None


def classify(total: int, free: int) -> tuple[Status, Severity]:
    """Absolute thresholds on large volumes; percent on tiny system partitions."""
    if total <= 0:
        return Status.UNKNOWN, Severity.NONE
    if total < WARN_FREE:
        ratio = free / total
        if free < SMALL_CRITICAL_FLOOR or ratio < SMALL_CRITICAL_RATIO:
            return Status.FAIL, Severity.HIGH
        if ratio < SMALL_WARN_RATIO:
            return Status.WARNING, Severity.MEDIUM
        return Status.PASS, Severity.NONE
    if free < CRITICAL_FREE:
        return Status.FAIL, Severity.HIGH
    if free < WARN_FREE:
        return Status.WARNING, Severity.MEDIUM
    return Status.PASS, Severity.NONE


def _rank(status: Status) -> int:
    if status == Status.FAIL:
        return 3
    if status == Status.WARNING:
        return 2
    if status == Status.UNKNOWN:
        return 1
    return 0


def _skip_ephemeral(path: Path) -> bool:
    """AppImage fuse mounts and tmpfs look 100% full and are not user storage."""
    posix = path.as_posix()
    if posix in _SKIP_PREFIXES or any(posix.startswith(p) for p in _SKIP_PREFIXES):
        return True
    return any(part in posix for part in _SKIP_PARTS)


def _is_sd_path(path: Path | str) -> bool:
    posix = Path(path).as_posix().lower()
    return "mmcblk" in posix or "/run/media/" in posix


def _uniq_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        try:
            key = str(path.resolve()) if path.exists() else str(path)
        except OSError:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def _vdf_library_roots(ctx: DiagnosticContext) -> list[Path]:
    found: list[Path] = []
    vdfs = (
        ctx.steam_root / "steamapps" / "libraryfolders.vdf",
        ctx.home / ".local" / "share" / "Steam" / "steamapps" / "libraryfolders.vdf",
    )
    for vdf in vdfs:
        text = ctx.read_text(vdf) or ""
        for match in _VDF_PATH.finditer(text):
            raw = match.group(1).strip()
            if raw:
                found.append(Path(raw))
    return [p for p in _uniq_paths(found) if not _skip_ephemeral(p)]


def _extra_library_paths(ctx: DiagnosticContext) -> list[Path]:
    """Steam libraries and removable media. Skip fuse/tmp mounts — those false-fail."""
    found = list(_vdf_library_roots(ctx))
    media = Path("/run/media") / ctx.user
    if ctx.exists(media):
        try:
            found.extend(p for p in media.iterdir() if p.is_dir())
        except OSError:
            pass
    return [p for p in _uniq_paths(found) if not _skip_ephemeral(p)]


def _is_steam_tool(text: str) -> bool:
    match = _ACF_NAME.search(text or "")
    name = (match.group(1) if match else "").lower()
    return any(hint in name for hint in _TOOL_HINTS)


def _count_games(ctx: DiagnosticContext, library_root: Path) -> int:
    steamapps = library_root / "steamapps"
    if not ctx.exists(steamapps):
        return 0
    count = 0
    try:
        entries = list(steamapps.glob("appmanifest_*.acf"))
    except OSError:
        return 0
    for acf in entries:
        text = ctx.read_text(acf, max_bytes=8000) or ""
        if _is_steam_tool(text):
            continue
        count += 1
    return count


def _record_snapshot(ctx: DiagnosticContext, mounts: list[tuple[str, int, int, int, Status, Severity]]) -> None:
    home_entry = next((m for m in mounts if Path(m[0]) == ctx.home), None)
    sd_entry = next((m for m in mounts if _is_sd_path(m[0])), None)
    if home_entry:
        _path, total, _used, free, _st, _sv = home_entry
        ctx.facts.storage_internal = {"path": _path, "free": free, "total": total}
    if sd_entry:
        _path, total, _used, free, _st, _sv = sd_entry
        ctx.facts.storage_sd = {"path": _path, "free": free, "total": total}

    games_internal = 0
    games_sd = 0
    for root in _vdf_library_roots(ctx):
        n = _count_games(ctx, root)
        if _is_sd_path(root):
            games_sd += n
        else:
            games_internal += n
    ctx.facts.steam_games_internal = games_internal
    ctx.facts.steam_games_sd = games_sd
    ctx.facts.steam_game_count = games_internal + games_sd


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    mounts: list[tuple[str, int, int, int, Status, Severity]] = []
    seen_dev: set[int] = set()
    for path in (ctx.home, Path("/var"), Path("/var/lib/flatpak"), *_extra_library_paths(ctx)):
        if path != ctx.home:
            if not ctx.exists(path) or _skip_ephemeral(path):
                continue
        usage = ctx.measure_disk(path)
        if usage is None:
            continue
        dev = _device_id(path)
        if dev is not None:
            if dev in seen_dev:
                continue
            seen_dev.add(dev)
        status, severity = classify(usage.total, usage.free)
        mounts.append((str(path), usage.total, usage.used, usage.free, status, severity))

    if not mounts:
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("sys.disk.unknown"),
            source=EvidenceSource.FILESYSTEM,
        )

    evidence = [f"{p}: {format_bytes(free)} free of {format_bytes(total)}" for p, total, _used, free, _st, _sv in mounts]
    ctx.facts.disk = [{"path": p, "free": free, "total": total} for p, total, _u, free, _st, _sv in mounts]
    ctx.facts.disk_min_free = min(m[3] for m in mounts)
    _record_snapshot(ctx, mounts)
    if ctx.facts.steam_game_count is not None:
        evidence.append(
            f"steam games: {ctx.facts.steam_game_count} "
            f"({ctx.facts.steam_games_internal} internal, {ctx.facts.steam_games_sd} microSD)"
        )

    worst_status = max(mounts, key=lambda m: _rank(m[4]))[4]
    if worst_status in {Status.FAIL, Status.WARNING}:
        headline = max(mounts, key=lambda m: (_rank(m[4]), 1 - (m[3] / m[1] if m[1] else 1)))
    else:
        large = [m for m in mounts if m[1] >= WARN_FREE]
        pool = large or mounts
        headline = min(pool, key=lambda m: m[3])
    mount_path, total, _used, free, status, severity = headline
    free_s = format_bytes(free)
    small = total < WARN_FREE

    if status == Status.FAIL:
        explain_key = "sys.disk.critical.small.explain" if small else "sys.disk.critical.explain"
        rec_key = "sys.disk.critical.small.rec" if small else "sys.disk.critical.rec"
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("sys.disk.critical", free=free_s, path=mount_path),
            explanation=ctx.tr(explain_key),
            recommendation=ctx.tr(rec_key),
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            severity=severity,
        )
    if status == Status.WARNING:
        explain_key = "sys.disk.warn.small.explain" if small else "sys.disk.warn.explain"
        rec_key = "sys.disk.warn.small.rec" if small else "sys.disk.warn.rec"
        return result(
            ID,
            title,
            Status.WARNING,
            ctx.tr("sys.disk.warn", free=free_s, path=mount_path),
            explanation=ctx.tr(explain_key),
            recommendation=ctx.tr(rec_key),
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            severity=severity,
        )
    return result(
        ID,
        title,
        Status.PASS,
        ctx.tr("sys.disk.ok", free=free_s, path=mount_path),
        evidence=evidence,
        source=EvidenceSource.FILESYSTEM,
    )
