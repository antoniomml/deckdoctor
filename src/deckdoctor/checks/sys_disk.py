from __future__ import annotations

from pathlib import Path

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "SYS-DISK"
TITLE = "Disk space"

CRITICAL_FREE = 500 * 1024 * 1024
WARN_FREE = 2 * 1024 * 1024 * 1024


def _fmt(num: int) -> str:
    for unit, size in (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)):
        if num >= size:
            return f"{num / size:.1f} {unit}"
    return f"{num} B"


def _device_id(path: Path) -> int | None:
    try:
        return path.stat().st_dev
    except OSError:
        return None


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
    mounts: list[tuple[str, int, int, int]] = []
    seen_dev: set[int] = set()
    for path in (ctx.home, Path("/var")):
        usage = ctx.measure_disk(path)
        if usage is None:
            continue
        dev = _device_id(path)
        if dev is not None:
            if dev in seen_dev:
                continue
            seen_dev.add(dev)
        mounts.append((str(path), usage.total, usage.used, usage.free))

    if not mounts:
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("sys.disk.unknown"),
            source=EvidenceSource.FILESYSTEM,
        )

    evidence = [f"{p}: {_fmt(free)} free of {_fmt(total)}" for p, total, _used, free in mounts]
    ctx.facts.disk = [{"path": p, "free": free, "total": total} for p, total, _u, free in mounts]

    min_free = min(m[3] for m in mounts)
    min_path = min(mounts, key=lambda m: m[3])[0]
    ctx.facts.disk_min_free = min_free
    free_s = _fmt(min_free)

    if min_free < CRITICAL_FREE:
        return result(
            ID,
            title,
            Status.FAIL,
            ctx.tr("sys.disk.critical", free=free_s, path=min_path),
            explanation=ctx.tr("sys.disk.critical.explain"),
            recommendation=ctx.tr("sys.disk.critical.rec"),
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            severity=Severity.HIGH,
        )
    if min_free < WARN_FREE:
        return result(
            ID,
            title,
            Status.WARNING,
            ctx.tr("sys.disk.warn", free=free_s, path=min_path),
            explanation=ctx.tr("sys.disk.warn.explain"),
            recommendation=ctx.tr("sys.disk.warn.rec"),
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            severity=Severity.MEDIUM,
        )
    return result(
        ID,
        title,
        Status.PASS,
        ctx.tr("sys.disk.ok", free=free_s, path=min_path),
        evidence=evidence,
        source=EvidenceSource.FILESYSTEM,
    )
