from __future__ import annotations

import os
import subprocess
import sys
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
# Flags that consume the following argv token.
_VALUE_FLAGS = frozenset(
    {
        "-p",
        "-o",
        "-n",
        "-H",
        "-M",
        "--property",
        "--type",
        "--output",
        "--lines",
        "--host",
        "--machine",
        "--columns",
        "--installation",
        "--arch",
        "--timeout",
    }
)


def child_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Environment for system tools launched from diagnose/fix.

    PyInstaller puts bundled OpenSSL on ``LD_LIBRARY_PATH``. Leaking that into
    ``flatpak``, ``ss``, or ``systemctl`` makes those binaries fail on SteamOS
    (``OPENSSL_3.4.0 not found``). Restore the pre-freeze path when possible.
    """
    env = dict(os.environ if base is None else base)
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    orig = env.get("LD_LIBRARY_PATH_ORIG")
    libpath = env.get("LD_LIBRARY_PATH", "")
    frozen = bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")
    mei = "/_MEI" in libpath.replace("\\", "/")
    if orig is not None:
        if orig:
            env["LD_LIBRARY_PATH"] = orig
        else:
            env.pop("LD_LIBRARY_PATH", None)
    elif frozen or mei:
        env.pop("LD_LIBRARY_PATH", None)
    return env


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


def _non_option_args(argv: Sequence[str]) -> list[str]:
    """Skip flags so ``systemctl --user start`` is still recognised as start."""
    out: list[str] = []
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--":
            out.extend(argv[i + 1 :])
            break
        if arg.startswith("-"):
            name, eq, _rest = arg.partition("=")
            if eq:
                i += 1
                continue
            if name in _VALUE_FLAGS and i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                i += 2
                continue
            i += 1
            continue
        out.append(arg)
        i += 1
    return out


def _guard(argv: Sequence[str]) -> None:
    if not argv:
        raise ValueError("empty argv")
    binary = os.path.basename(argv[0])
    if binary in _FORBIDDEN_BINARIES:
        raise PermissionError(f"refusing to run mutating command: {argv[0]}")
    verbs = _non_option_args(argv)
    if binary == "systemctl":
        if verbs and verbs[0] in _FORBIDDEN_SYSTEMCTL:
            raise PermissionError(f"refusing mutating systemctl: {verbs[0]}")
    if binary == "flatpak":
        if verbs and verbs[0] in _FORBIDDEN_FLATPAK:
            if verbs[0] == "repair" and "--dry-run" in argv:
                return
            raise PermissionError(f"refusing mutating flatpak: {verbs[0]}")
    if binary == "steamos-update":
        if any(a in {"-h", "--help"} for a in argv[1:]) and not verbs:
            return
        if not verbs or verbs[0] != "check":
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
        if timeout <= 0:
            return CommandResult(
                argv=argv_t,
                exit_code=124,
                stdout="",
                stderr="timed out",
                timed_out=True,
                error="timeout",
            )
        merged_env = child_env()
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
    """Map exact argv tuples to canned results. Prefix match is exact-tuple first only."""

    def __init__(self, mapping: dict[tuple[str, ...], CommandResult] | None = None) -> None:
        self.mapping: dict[tuple[str, ...], CommandResult] = mapping or {}
        self.calls: list[tuple[str, ...]] = []
        self.default_not_found = True
        self.allow_prefix = False

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
        if timeout <= 0:
            return CommandResult(
                argv=argv_t,
                exit_code=124,
                stdout="",
                stderr="timed out",
                timed_out=True,
                error="timeout",
            )
        if argv_t in self.mapping:
            return self.mapping[argv_t]
        if self.allow_prefix:
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
