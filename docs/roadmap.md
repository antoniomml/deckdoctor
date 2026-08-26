# DeckDoctor roadmap

## 0.1 — Diagnose

Standalone CLI. Read-only. No Decky plugin. No automatic fixes.

Shipped in 0.1: core types, MVP checks, human CLI + `--json` + `report`, pytest fixtures, PyInstaller + `scripts/install.sh`, docs.

## 0.2 — Hardening (this tree)

- Disk check ignores a full A/B root filesystem
- `install.sh` verifies `SHA256SUMS`; tag workflow publishes the binary + checksums
- Command guardrails recognise `systemctl --user start` / `flatpak --user update`
- Shared `flatpak remote-ls -a` probe; exit code 2 on internal errors
- `--lang es|en`, `--ascii`/`--plain`, `--only`, `--timeout`
- Typed `Facts`, `Check` protocol, ruff + mypy, field-level JSON sanitiser, HTTP host allowlist

## 0.2.x — Deeper software health (this tree)

- Flatpak EOL via `flatpak info --show-metadata` (`EndOfLife`), plus apps that use those runtimes
- Plugin store updates only when the local name/dir maps to **exactly one** store entry
- Pending SteamOS reboot from `/run/steamos-atomupd/reboot_for_update` (RAUC post-install marker)
- Overlay warning if `client.conf` / `rauc/system.conf` are user-copied under `/var/lib/overlays/etc/upper`
- Bounded CEF / `steamloopback.host` excerpt in the report
- Non-SteamOS images (Bazzite, ChimeraOS, …) skip atomupd/RAUC checks and still run Decky/Flatpak

## 0.3 — Opt-in fixes (this tree)

`deckdoctor` stays diagnose-by-default and compact. `deckdoctor fix` prints a plan; `--yes` applies only known reversible mutations (PluginLoader +x, CEF enable file, start `plugin_loader.service`, `flatpak update -y`). Never the default. Still forbidden: reboot, kill, `chmod 777`, `flatpak uninstall`, writing the read-only root, auto-reinstalling Decky.

Also in 0.3: Spanish findings (not just chrome), compact CLI, `--verbose`, `deckdoctor checks`, hostname `steamdeck` no longer redacted, updater “no update available” false positive fixed, SteamOS checks skip unless the OS is actually SteamOS.

## 0.3.1 — Public landing

English README aimed at Deck users, not developers. Compact CLI uses emoji marks and plain-language labels. Spanish remains available with `--lang es`.

## Later / maybe never

- Decky plugin frontend that calls the same core (useful, but the CLI remains the source of truth)
- Hardware module
- Proton/game diagnosis
- Hardcoded Steam×Decky incompatibility matrix
- Telemetry, auto-upload, cloud accounts

## Non-goals that stay non-goals

- Replacing Valve support
- Guaranteeing sanitisation
- Working around every Bazzite/Chimera difference (best-effort only)
- Depending on Decky to diagnose Decky
