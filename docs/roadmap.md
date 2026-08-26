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
