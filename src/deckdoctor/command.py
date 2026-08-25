from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


# Commands the tool must never invoke. Defense in depth; checks should not
# construct these argv lists either.
_FORBIDDEN_BINARIES = frozenset(
    {
        "chmod",
        "chown",
        "rm",
        "kill",
        "killall",
        "reboot",
        "shutdown",
    }
)
_FORBIDDEN_SYSTEMCTL = frozenset({"start", "stop", "restart", "reload", "mask", "unmask", "enable", "disable"})
_FORBIDDEN_FLATPAK = frozenset({"update", "uninstall", "install", "remove", "repair", "mask", "pin"})


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and self.error is None


def _guard(argv: Sequence[str]) -> None:
    if not argv:
        raise ValueError("empty argv")
    binary = os.path.basename(argv[0])
    if binary in _FORBIDDEN_BINARIES:
        raise PermissionError(f"refusing to run mutating command: {argv[0]}")
    if binary == "systemctl" and len(argv) > 1 and argv[1] in _FORBIDDEN_SYSTEMCTL:
        raise PermissionError(f"refusing mutating systemctl: {argv[1]}")
    if binary == "flatpak" and len(argv) > 1 and argv[1] in _FORBIDDEN_FLATPAK:
        # repair --dry-run is read-only and is allowed if we ever add it.
        if argv[1] == "repair" and "--dry-run" in argv:
            return
        raise PermissionError(f"refusing mutating flatpak: {argv[1]}")
    if binary == "steamos-update" and (len(argv) == 1 or argv[1] not in {"check", "--help", "-h"}):
        raise PermissionError("refusing steamos-update without check")


class CommandRunner:
    """subprocess wrapper: list argv, no shell, timeout, mockable."""

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float = 15.0,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> CommandResult:
        argv_t = tuple(argv)
        _guard(argv_t)
        merged_env = os.environ.copy()
        merged_env["LANG"] = "C"
        merged_env["LC_ALL"] = "C"
        if env:
            merged_env.update(env)
        try:
            completed = subprocess.run(
                list(argv_t),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=merged_env,
                cwd=cwd,
                check=False,
                shell=False,
            )
            return CommandResult(
                argv=argv_t,
                exit_code=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
        except FileNotFoundError as exc:
            return CommandResult(
                argv=argv_t,
                exit_code=127,
                stdout="",
                stderr=str(exc),
                error="not_found",
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return CommandResult(
                argv=argv_t,
                exit_code=124,
                stdout=stdout,
                stderr=stderr or "timed out",
                timed_out=True,
                error="timeout",
            )
        except OSError as exc:
            return CommandResult(
                argv=argv_t,
                exit_code=1,
                stdout="",
                stderr=str(exc),
                error="os_error",
            )


class FakeCommandRunner(CommandRunner):
    """Map exact argv tuples (or prefixes) to canned results."""

    def __init__(self, mapping: dict[tuple[str, ...], CommandResult] | None = None) -> None:
        self.mapping: dict[tuple[str, ...], CommandResult] = mapping or {}
        self.calls: list[tuple[str, ...]] = []
        self.default_not_found = True

    def add(self, argv: Sequence[str], result: CommandResult) -> None:
        self.mapping[tuple(argv)] = result

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float = 15.0,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> CommandResult:
        argv_t = tuple(argv)
        _guard(argv_t)
        self.calls.append(argv_t)
        if argv_t in self.mapping:
            return self.mapping[argv_t]
        for key, result in self.mapping.items():
            if argv_t[: len(key)] == key:
                return result
        if self.default_not_found:
            return CommandResult(
                argv=argv_t,
                exit_code=127,
                stdout="",
                stderr=f"not mocked: {argv_t!r}",
                error="not_found",
            )
        return super().run(argv, timeout=timeout, env=env, cwd=cwd)
