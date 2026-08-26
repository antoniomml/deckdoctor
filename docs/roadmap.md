# DeckDoctor roadmap

## 0.1 — Diagnose

Standalone CLI. Read-only. No Decky plugin. No automatic fixes.

Shipped in 0.1: core types, MVP checks, human CLI + `--json` + `report`, pytest fixtures, PyInstaller + `scripts/install.sh`, docs.

## 0.2 — Hardening (this tree)

- Disk check ignores a full A/B root filesystem
- `install.sh` verifies `SHA256SUMS`; tag workflow publishes the binary + checksums
- Command guardrails recognise `systemctl --user start` / `flatpak --user update`
- Shared `flatpak remote-ls -a` probe; exit code 2 on internal errors
- `--lang es|en` (default: English; `LANG` does not switch the UI), `--ascii`/`--plain`, `--only`, `--timeout`
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

## 0.3.2 — Steam Deck false positives

On a real Steam Deck the 0.3.1 binary reported six “serious” problems that were all tool bugs: SteamOS `/var` is a ~230 MB partition (Flatpak is offloaded to `/home`), `ss` hides PluginLoader’s name from a non-root user, and the PyInstaller build leaked bundled OpenSSL into `flatpak` plus an empty CA store into HTTPS.

## 0.3.3 — Same Deck, remaining edges

A broken Flatpak remote (expired GPG) must not hide Flathub updates or AutoFlatpaks’ real cause. SYS-DISK now includes Steam libraries and `/run/media/$USER` and still ignores AppImage fuse mounts. `steamos-select-branch -c` printing `rel` is stable; `package/beta` containing `steamdeck_stable` is not a Beta client. CEF forwarded on `*:8081` is a warning. Username `deck` is not redacted inside plugin directory names. Compact CLI shows a Deck snapshot: internal vs microSD free space and Steam games per library (Proton/runtimes excluded).

## 0.3.4 — Compact English CLI, confirm-before-fix

English unless `--lang es` or `DECKDOCTOR_LANG`. Compact diagnose drops repeated explanations, FACT dumps, and severity labels; inferred (likely) stories stay. `deckdoctor fix` prints the plan and asks `y/N` on a TTY; `-y`/`--yes` skips the question. Non-TTY still needs `-y`.

## 0.3.1 — Public landing

English README aimed at Deck users, not developers. Compact CLI uses emoji marks and plain-language labels. Spanish is opt-in (`--lang es` or `DECKDOCTOR_LANG`).

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
