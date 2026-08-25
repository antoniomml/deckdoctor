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


def run(ctx: DiagnosticContext) -> CheckResult:
    mounts = []
    seen: set[str] = set()
    for raw in (ctx.home, Path("/home"), Path("/var"), Path("/")):
        path = Path(raw)
        try:
            resolved = str(path.resolve())
        except OSError:
            resolved = str(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        usage = ctx.measure_disk(path)
        if usage is None:
            continue
        mounts.append((str(path), usage.total, usage.used, usage.free))

    if not mounts:
        return result(
            ID,
            TITLE,
            Status.UNKNOWN,
            "Could not measure disk space",
            source=EvidenceSource.FILESYSTEM,
        )

    evidence = [f"{p}: {_fmt(free)} free of {_fmt(total)}" for p, total, _used, free in mounts]
    ctx.facts["disk"] = [{"path": p, "free": free, "total": total} for p, total, _u, free in mounts]

    min_free = min(m[3] for m in mounts)
    min_path = min(mounts, key=lambda m: m[3])[0]
    ctx.facts["disk_min_free"] = min_free

    if min_free < CRITICAL_FREE:
        return result(
            ID,
            TITLE,
            Status.FAIL,
            f"Only {_fmt(min_free)} free on {min_path}",
            explanation=(
                "Very little free space remains. Decky/plugin installs, Flatpak fetches, "
                "and SteamOS updates may fail. This is correlation, not proof of a specific crash."
            ),
            recommendation="Free space on /home and /var (games, Flatpak, Steam downloads) and re-run DeckDoctor.",
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            severity=Severity.HIGH,
        )
    if min_free < WARN_FREE:
        return result(
            ID,
            TITLE,
            Status.WARNING,
            f"{_fmt(min_free)} free on {min_path}",
            explanation="Less than 2 GB free can make Flatpak and OS updates unreliable.",
            recommendation="Free some space before large updates.",
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            severity=Severity.MEDIUM,
        )
    return result(
        ID,
        TITLE,
        Status.PASS,
        f"{_fmt(min_free)} free (lowest mount: {min_path})",
        evidence=evidence,
        source=EvidenceSource.FILESYSTEM,
    )
