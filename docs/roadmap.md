# DeckDoctor roadmap

## 0.1 — Diagnose (this release)

Standalone CLI. Read-only. No Decky plugin. No automatic fixes.

Ships:

- Core: `Check`, `CheckResult`, `DiagnosticContext`, `CommandRunner`, correlator, sanitizer, report
- MVP checks listed in [checks.md](checks.md)
- Human CLI + `--json` + `deckdoctor report`
- Pytest fixtures for healthy and broken states
- PyInstaller x86_64 binary + `scripts/install.sh`
- Docs: research, design, checks, this roadmap

Success: a user who cannot use `systemctl`/`journalctl`/`flatpak` still gets a useful explanation, including the three product examples:

1. AutoFlatpaks installed and loading, but Flatpak cannot list remotes because a named remote has dead refs.
2. Decky installed, PluginLoader running, frontend not loading; Steam Beta is a likely factor.
3. Incomplete install: PluginLoader missing, GitHub API remaining = 0.

## 0.2 — Deeper software health

- Flatpak EOL via metadata probe (`EndOfLife`), with apps that use those runtimes
- Plugin store update count if name matching can be made reliable
- Decky stable update available via `releases/latest` redirect (no API)
- SteamOS pending-reboot if a stable local signal is confirmed on 3.8+
- Overlay warning if `client.conf` / `rauc/system.conf` are user-edited
- Bounded CEF/`steamloopback.host` excerpt in the report
- `--offline` already exists as `--no-network`; add `--only ID,ID`

## 0.3 — Opt-in fixes (strict contract)

A fix ships only if all of these are true:

1. Exact mutation is known
2. Reversible or trivially recoverable
3. Documented
4. Explicit confirmation (`deckdoctor fix NAME` prints a plan, requires `--yes`)
5. Never the default of `deckdoctor`

Candidates (not promises):

- `decky.service` enable/start **after** showing `systemctl` plan (still controversial; may stay manual)
- Restore a backup unit file if the live unit is GitHub 429 HTML
- Document-only “run the official installer from a different network” for rate limit

Still forbidden without a later design review: `chmod -R 777`, `rm -rf`, killing processes, `flatpak uninstall`, writing the read-only root.

## Later / maybe never

- Decky plugin frontend that calls the same core (useful, but the CLI remains the source of truth)
- Hardware module (that is DeckDoc’s job)
- Proton/game diagnosis
- Hardcoded Steam×Decky incompatibility matrix
- Telemetry, auto-upload, cloud accounts

## Non-goals that stay non-goals

- Replacing Valve support
- Guaranteeing sanitisation
- Working around every Bazzite/Chimera difference (best-effort only)
- Depending on Decky to diagnose Decky
