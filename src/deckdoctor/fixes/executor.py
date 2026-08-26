from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from deckdoctor.command import CommandResult, child_env
from deckdoctor.context import DiagnosticContext

_ALLOWED_SYSTEMCTL = {
    ("systemctl", "enable", "--now", "plugin_loader.service"),
    ("systemctl", "start", "plugin_loader.service"),
    ("systemctl", "--user", "enable", "--now", "plugin_loader.service"),
    ("systemctl", "--user", "start", "plugin_loader.service"),
}
_ALLOWED_FLATPAK = {
    ("flatpak", "update", "-y"),
    ("flatpak", "--user", "update", "-y"),
}


def _argv_t(argv: Sequence[str]) -> tuple[str, ...]:
    return tuple(argv)


class FixExecutor:
    """Whitelisted mutations only. Diagnose still uses CommandRunner (read-only)."""

    def chmod_plus_x(self, ctx: DiagnosticContext, path: Path) -> CommandResult:
        self._assert_pluginloader(ctx, path)
        argv = ("chmod", "+x", str(path))
        try:
            mode = path.stat().st_mode
            path.chmod(mode | 0o111)
            return CommandResult(argv, 0, "", "")
        except OSError as exc:
            return CommandResult(argv, 1, "", str(exc), error="os_error")

    def touch_empty(self, ctx: DiagnosticContext, path: Path) -> CommandResult:
        self._assert_cef(ctx, path)
        argv = ("touch", str(path))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
            return CommandResult(argv, 0, "", "")
        except OSError as exc:
            return CommandResult(argv, 1, "", str(exc), error="os_error")

    def run(self, argv: Sequence[str], *, timeout: float = 60.0) -> CommandResult:
        argv_t = _argv_t(argv)
        self._assert_allowed(argv_t)
        env = child_env()
        try:
            completed = subprocess.run(
                list(argv_t),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=False,
                shell=False,
            )
            return CommandResult(
                argv_t,
                completed.returncode,
                completed.stdout or "",
                completed.stderr or "",
            )
        except FileNotFoundError as exc:
            return CommandResult(argv_t, 127, "", str(exc), error="not_found")
        except subprocess.TimeoutExpired:
            return CommandResult(argv_t, 124, "", "timed out", timed_out=True, error="timeout")
        except OSError as exc:
            return CommandResult(argv_t, 1, "", str(exc), error="os_error")

    def _assert_allowed(self, argv: tuple[str, ...]) -> None:
        if argv in _ALLOWED_SYSTEMCTL or argv in _ALLOWED_FLATPAK:
            return
        raise PermissionError(f"refusing unlisted fix command: {argv}")

    def _assert_pluginloader(self, ctx: DiagnosticContext, path: Path) -> None:
        try:
            if path.resolve() != ctx.plugin_loader.resolve():
                raise PermissionError(f"refusing chmod on {path}")
        except OSError as exc:
            raise PermissionError(f"refusing chmod on {path}") from exc

    def _assert_cef(self, ctx: DiagnosticContext, path: Path) -> None:
        allowed = ctx.steam_root / ".cef-enable-remote-debugging"
        try:
            if path.resolve() != allowed.resolve() and path != allowed:
                # steam_root may not exist yet; allow the canonical relative path
                if path.name != ".cef-enable-remote-debugging":
                    raise PermissionError(f"refusing touch on {path}")
                if path.parent != ctx.steam_root:
                    raise PermissionError(f"refusing touch on {path}")
        except OSError as exc:
            raise PermissionError(f"refusing touch on {path}") from exc


class FakeFixExecutor(FixExecutor):
    def __init__(self) -> None:
        self.chmod_ok = True
        self.touch_ok = True
        self.mapping: dict[tuple[str, ...], CommandResult] = {}
        self.calls: list[tuple[str, ...]] = []

    def chmod_plus_x(self, ctx: DiagnosticContext, path: Path) -> CommandResult:
        self._assert_pluginloader(ctx, path)
        argv = ("chmod", "+x", str(path))
        self.calls.append(argv)
        if self.chmod_ok:
            try:
                path.chmod(path.stat().st_mode | 0o111)
            except OSError:
                pass
            return CommandResult(argv, 0, "", "")
        return CommandResult(argv, 1, "", "chmod failed", error="os_error")

    def touch_empty(self, ctx: DiagnosticContext, path: Path) -> CommandResult:
        self._assert_cef(ctx, path)
        argv = ("touch", str(path))
        self.calls.append(argv)
        if not self.touch_ok:
            return CommandResult(argv, 1, "", "touch failed", error="os_error")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        return CommandResult(argv, 0, "", "")

    def run(self, argv: Sequence[str], *, timeout: float = 60.0) -> CommandResult:
        argv_t = _argv_t(argv)
        self._assert_allowed(argv_t)
        self.calls.append(argv_t)
        if argv_t in self.mapping:
            return self.mapping[argv_t]
        return CommandResult(argv_t, 0, "", "")
