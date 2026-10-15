"""Steam storage inventory: games, shader caches, Proton prefixes and leftovers.

Read-only. Sizes come from Steam manifests first (instant) and from a bounded
directory walk for caches/prefixes (``measure``). Nothing here deletes data.
"""
from __future__ import annotations

import os
import struct
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deckdoctor.context import DiagnosticContext
from deckdoctor.steam import library_roots, metadata

_TOOL_HINTS = ("proton", "steam linux runtime", "steamworks common", "easyanticheat", "battleye")
# Steam assigns non-Steam shortcuts IDs with the top bit set.
SHORTCUT_MIN_ID = 2**31
_SYSTEM_IDS = {0}


@dataclass
class Game:
    appid: int
    name: str
    library: str
    library_kind: str
    installdir: str
    size_on_disk: int | None = None
    last_played: int | None = None
    last_updated: int | None = None
    state_flags: int | None = None
    is_tool: bool = False
    update_pending: bool = False
    update_bytes: int | None = None
    playtime_minutes: int | None = None
    cloud_synced: bool | None = None
    proton: str | None = None
    prefix_path: str | None = None
    shader_path: str | None = None
    prefix_bytes: int | None = None
    shader_bytes: int | None = None

    @property
    def total_bytes(self) -> int:
        return sum(v or 0 for v in (self.size_on_disk, self.prefix_bytes, self.shader_bytes))


@dataclass
class Leftover:
    kind: str  # prefix | shadercache
    appid: int
    path: str
    reason: str  # uninstalled | shortcut_removed
    library_kind: str
    size: int | None = None
    cloud_synced: bool | None = None
    last_played: int | None = None


@dataclass
class Library:
    path: str
    kind: str
    accessible: bool
    free: int | None = None
    total: int | None = None
    game_count: int = 0
    games_bytes: int = 0


@dataclass
class StorageReport:
    libraries: list[Library] = field(default_factory=list)
    games: list[Game] = field(default_factory=list)
    tools: list[Game] = field(default_factory=list)
    leftovers: list[Leftover] = field(default_factory=list)
    shortcuts: dict[int, str] = field(default_factory=dict)
    all_libraries_accessible: bool = True
    measured: bool = False
    measure_complete: bool = False

    @property
    def pending_update_bytes(self) -> int:
        return sum(g.update_bytes or 0 for g in self.games if g.update_pending)

    @property
    def leftover_bytes(self) -> int:
        return sum(item.size or 0 for item in self.leftovers)

    def leftover_bytes_of(self, kind: str) -> int:
        return sum(item.size or 0 for item in self.leftovers if item.kind == kind)

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return {
            "libraries": [asdict(item) for item in self.libraries],
            "games": [asdict(item) for item in self.games],
            "tools": [asdict(item) for item in self.tools],
            "leftovers": [asdict(item) for item in self.leftovers],
            "shortcuts": {str(k): v for k, v in self.shortcuts.items()},
            "all_libraries_accessible": self.all_libraries_accessible,
            "measured": self.measured,
            "measure_complete": self.measure_complete,
        }


def _int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def parse_binary_vdf(data: bytes, *, max_depth: int = 16) -> dict[str, Any]:
    """Minimal reader for Steam's binary KeyValues (``shortcuts.vdf``)."""
    pos = 0

    def cstring() -> str:
        nonlocal pos
        end = data.find(b"\x00", pos)
        if end < 0:
            raise ValueError("unterminated string")
        text = data[pos:end].decode("utf-8", errors="replace")
        pos = end + 1
        return text

    def block(depth: int) -> dict[str, Any]:
        nonlocal pos
        if depth > max_depth:
            raise ValueError("binary KeyValues nesting too deep")
        out: dict[str, Any] = {}
        while pos < len(data):
            kind = data[pos]
            pos += 1
            if kind == 0x08:
                return out
            key = cstring().lower()
            if kind == 0x00:
                out[key] = block(depth + 1)
            elif kind == 0x01:
                out[key] = cstring()
            elif kind == 0x02:
                if pos + 4 > len(data):
                    raise ValueError("truncated int32")
                out[key] = struct.unpack_from("<i", data, pos)[0]
                pos += 4
            elif kind == 0x07:
                if pos + 8 > len(data):
                    raise ValueError("truncated uint64")
                out[key] = struct.unpack_from("<Q", data, pos)[0]
                pos += 8
            else:
                raise ValueError(f"unsupported binary KeyValues type {kind}")
        if depth:
            raise ValueError("unterminated binary KeyValues block")
        return out

    return block(0)


def read_shortcuts(ctx: DiagnosticContext, max_bytes: int = 2_000_000) -> dict[int, str]:
    found: dict[int, str] = {}
    try:
        users = sorted((ctx.steam_root / "userdata").iterdir())
    except OSError:
        return found
    for user in users:
        path = user / "config" / "shortcuts.vdf"
        try:
            with path.open("rb") as stream:
                raw = stream.read(max_bytes + 1)
        except OSError:
            continue
        if len(raw) > max_bytes:
            continue
        try:
            data = parse_binary_vdf(raw)
        except ValueError:
            continue
        rows = data.get("shortcuts")
        if not isinstance(rows, dict):
            continue
        for item in rows.values():
            if not isinstance(item, dict):
                continue
            appid = item.get("appid")
            name = item.get("appname") or item.get("exe") or ""
            if isinstance(appid, int):
                found[appid & 0xFFFFFFFF] = str(name).strip('"')
    return found


@dataclass
class LocalApp:
    last_played: int | None = None
    playtime_minutes: int | None = None
    cloud_synced: bool | None = None


def read_local_apps(ctx: DiagnosticContext) -> dict[int, LocalApp]:
    """Per-app play history from each Steam user's ``localconfig.vdf`` (newest wins)."""
    found: dict[int, LocalApp] = {}
    try:
        users = sorted((ctx.steam_root / "userdata").iterdir())
    except OSError:
        return found
    for user in users:
        data = metadata(ctx, user / "config" / "localconfig.vdf", max_bytes=8_000_000)
        node: Any = data
        for key in ("userlocalconfigstore", "software", "valve", "steam", "apps"):
            node = node.get(key) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            continue
        for raw_id, info in node.items():
            appid = _int(raw_id)
            if appid is None or not isinstance(info, dict):
                continue
            played = _int(info.get("lastplayed")) or None
            entry = found.setdefault(appid, LocalApp())
            if played and (entry.last_played or 0) < played:
                entry.last_played = played
            minutes = _int(info.get("playtime"))
            if minutes is not None:
                entry.playtime_minutes = max(entry.playtime_minutes or 0, minutes)
            cloud = info.get("cloud")
            if isinstance(cloud, dict) and isinstance(cloud.get("last_sync_state"), str):
                synced = cloud["last_sync_state"] == "synchronized"
                entry.cloud_synced = synced if entry.cloud_synced is None else entry.cloud_synced and synced
    return found


def _resolved(path: str) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return path


def registered_apps(ctx: DiagnosticContext) -> dict[str, set[int]]:
    """AppIDs per library path as recorded in ``libraryfolders.vdf``."""
    data = metadata(ctx, ctx.steam_root / "steamapps" / "libraryfolders.vdf")
    folders = (data or {}).get("libraryfolders")
    out: dict[str, set[int]] = {}
    if not isinstance(folders, dict):
        return out
    for item in folders.values():
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        apps = item.get("apps")
        ids = {appid for appid in (_int(key) for key in apps)} if isinstance(apps, dict) else set()
        out[item["path"]] = {appid for appid in ids if appid is not None}
    return out


def block_device_name(path: Path, sys_root: Path = Path("/sys")) -> str:
    try:
        dev = os.stat(path).st_dev
    except OSError:
        return ""
    try:
        target = os.readlink(sys_root / f"dev/block/{os.major(dev)}:{os.minor(dev)}")
    except OSError:
        return ""
    return os.path.basename(target)


def library_kind(path: Path, home: Path, sys_root: Path = Path("/sys")) -> str:
    device = block_device_name(path, sys_root)
    text = str(path)
    if device.startswith("mmcblk") or "mmcblk" in text:
        return "microsd"
    if device.startswith("nvme") or text.startswith(str(home)):
        return "internal"
    if device.startswith("sd") or text.startswith(("/run/media", "/media", "/mnt")):
        return "external"
    return "internal"


def _game_from_manifest(root: Path, kind: str, app: dict[str, Any]) -> Game | None:
    appid = _int(app.get("appid"))
    if appid is None:
        return None
    name = str(app.get("name") or appid)
    flags = _int(app.get("stateflags"))
    to_dl = _int(app.get("bytestodownload")) or 0
    done = _int(app.get("bytesdownloaded")) or 0
    lowered = name.lower()
    game = Game(
        appid=appid,
        name=name,
        library=str(root),
        library_kind=kind,
        installdir=str(app.get("installdir") or ""),
        size_on_disk=_int(app.get("sizeondisk")),
        last_played=_int(app.get("lastplayed")) or None,
        last_updated=_int(app.get("lastupdated")) or None,
        state_flags=flags,
        is_tool=any(hint in lowered for hint in _TOOL_HINTS),
        update_pending=bool(flags is not None and flags & 2) or to_dl > done,
    )
    if game.update_pending and to_dl > done:
        game.update_bytes = to_dl - done
    return game


def _numeric_dirs(path: Path) -> Iterator[tuple[int, Path]]:
    try:
        entries = list(os.scandir(path))
    except OSError:
        return
    for entry in entries:
        if entry.name.isdigit() and entry.is_dir(follow_symlinks=False):
            yield int(entry.name), Path(entry.path)


def scan(ctx: DiagnosticContext) -> StorageReport:
    """Fast pass: manifests, library space, prefix/shader locations. No size walk."""
    report = StorageReport(shortcuts=read_shortcuts(ctx))
    local = read_local_apps(ctx)
    roots, _readable = library_roots(ctx)
    installed: set[int] = set()
    seen_paths: set[str] = set()
    for root in roots:
        apps = root / "steamapps"
        accessible = os.access(apps, os.R_OK | os.X_OK)
        kind = library_kind(root, ctx.home, ctx.sys_root)
        library = Library(path=str(root), kind=kind, accessible=accessible)
        report.libraries.append(library)
        if not accessible:
            report.all_libraries_accessible = False
            continue
        usage = ctx.measure_disk(root)
        if usage is not None:
            library.free, library.total = usage.free, usage.total
        try:
            manifests = sorted(apps.glob("appmanifest_*.acf"))[:2000]
        except OSError:
            manifests = []
        for manifest in manifests:
            data = metadata(ctx, manifest, max_bytes=256_000)
            app = (data or {}).get("appstate")
            if not isinstance(app, dict):
                continue
            game = _game_from_manifest(root, kind, app)
            if game is None:
                continue
            installed.add(game.appid)
            history = local.get(game.appid)
            if history is not None:
                game.last_played = max(game.last_played or 0, history.last_played or 0) or None
                game.playtime_minutes = history.playtime_minutes
                game.cloud_synced = history.cloud_synced
            if game.is_tool:
                report.tools.append(game)
            else:
                report.games.append(game)
                library.game_count += 1
                library.games_bytes += game.size_on_disk or 0
    # Games on an unplugged drive have no readable manifest; Steam's catalog still lists their AppIDs.
    reachable_paths = {_resolved(lib.path) for lib in report.libraries if lib.accessible}
    for lib_path, appids in registered_apps(ctx).items():
        if _resolved(lib_path) not in reachable_paths:
            installed.update(appids)
    # Steam may keep prefixes/caches of microSD games on internal storage, so search every library.
    reachable = [Path(lib.path) for lib in report.libraries if lib.accessible]
    for game in report.games + report.tools:
        own = Path(game.library)
        order = [own, *(root for root in reachable if root != own)]
        for root in order:
            prefix = root / "steamapps" / "compatdata" / str(game.appid)
            if game.prefix_path is None and ctx.exists(prefix):
                game.prefix_path = str(prefix)
                version = ctx.read_text(prefix / "config_info", max_bytes=256)
                if version:
                    game.proton = version.splitlines()[0].strip()[:40] or None
                seen_paths.add(str(prefix))
            shader = root / "steamapps" / "shadercache" / str(game.appid)
            if game.shader_path is None and ctx.exists(shader):
                game.shader_path = str(shader)
                seen_paths.add(str(shader))
    for library in report.libraries:
        if not library.accessible:
            continue
        apps = Path(library.path) / "steamapps"
        for kind, folder in (("prefix", "compatdata"), ("shadercache", "shadercache")):
            for appid, path in _numeric_dirs(apps / folder):
                if appid in installed or appid in _SYSTEM_IDS or str(path) in seen_paths:
                    continue
                if appid >= SHORTCUT_MIN_ID:
                    # Without a readable shortcuts.vdf every non-Steam prefix would look orphaned.
                    if not report.shortcuts or appid in report.shortcuts:
                        continue
                    reason = "shortcut_removed"
                else:
                    reason = "uninstalled"
                history = local.get(appid)
                report.leftovers.append(Leftover(kind=kind, appid=appid, path=str(path), reason=reason,
                                                 library_kind=library.kind,
                                                 cloud_synced=history.cloud_synced if history else None,
                                                 last_played=history.last_played if history else None))
    report.games.sort(key=lambda g: g.name.lower())
    return report


def measure(path: Path, *, deadline: float | None = None, max_entries: int = 2_000_000) -> tuple[int, bool]:
    """Allocated bytes under ``path`` without following symlinks. Returns ``(bytes, complete)``."""
    total = 0
    stack = [str(path)]
    seen = 0
    while stack:
        if deadline is not None and time.monotonic() >= deadline:
            return total, False
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    seen += 1
                    if seen > max_entries:
                        return total, False
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        else:
                            st = entry.stat(follow_symlinks=False)
                            total += getattr(st, "st_blocks", 0) * 512 or st.st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total, True


ProgressFn = Callable[[int, int, str], None]


def measure_report(
    report: StorageReport,
    *,
    deadline: float | None = None,
    leftovers_only: bool = False,
    progress: ProgressFn | None = None,
) -> None:
    """Fill prefix/shader sizes in place. Leftovers first: they are what users act on."""
    jobs: list[tuple[str, object, str, str]] = []
    for item in report.leftovers:
        jobs.append((item.path, item, "size", str(item.appid)))
    if not leftovers_only:
        for game in report.games:
            if game.shader_path:
                jobs.append((game.shader_path, game, "shader_bytes", game.name))
            if game.prefix_path:
                jobs.append((game.prefix_path, game, "prefix_bytes", game.name))
    complete = True
    for index, (path, target, attr, label) in enumerate(jobs):
        if progress:
            progress(index, len(jobs), label)
        size, done = measure(Path(path), deadline=deadline)
        setattr(target, attr, size)
        if not done:
            complete = False
            break
    report.measured = True
    report.measure_complete = complete
