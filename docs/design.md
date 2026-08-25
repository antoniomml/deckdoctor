# DeckDoctor design

**Version:** 0.1  
**Language:** Python 3.11+  
**License:** MIT  
**Default posture:** read-only, local-first, no telemetry.

## 1. Goals

A user can run `deckdoctor` on a Steam Deck (Desktop Mode or SSH) and get, in seconds:

1. Whether SteamOS, Decky, plugins, and Flatpak look healthy.
2. If something is wrong: **what** we observed, **why** it matters, and a **safe** next step.
3. A sanitised Markdown report suitable for GitHub issues / Discord.

Non-goals for 0.1: automatic repair, hardware diagnostics, Proton/game troubleshooting, a Decky plugin UI.

## 2. CLI

```text
deckdoctor                 # same as diagnose
deckdoctor diagnose        # run checks, print human summary
deckdoctor report          # diagnose + write deckdoctor-report.md
deckdoctor --json          # machine-readable result on stdout
deckdoctor --no-network    # skip checks that need the internet
deckdoctor --output PATH   # report path (default: ./deckdoctor-report.md)
deckdoctor --version
```

Exit codes:

| Code | Meaning |
|---|---|
| 0 | No FAIL results (WARNING/INFO/SKIPPED/UNKNOWN allowed) |
| 1 | One or more FAIL |
| 2 | Tool error (could not start) |

Never prompt for sudo. Never mutate the system.

## 3. Pipeline

```text
collect context (paths, os-release, user)
    → run independent checks (CommandRunner)
    → correlator (FACT vs LIKELY)
    → renderer (CLI / Markdown / JSON)
    → sanitizer (reports only)
```

## 4. Core types

Keep this small. Protocols and dataclasses; no inheritance trees.

### 4.1 Status

`PASS | INFO | WARNING | FAIL | SKIPPED | UNKNOWN`

`LIMITED` (missing privileges) is encoded as `SKIPPED` with an explanation, not a seventh user-facing status.

### 4.2 CheckResult

| Field | Role |
|---|---|
| `check_id` | Stable ID (`DECKY-INSTALL`) |
| `title` | Short section label |
| `status` | See above |
| `severity` | `high` / `medium` / `low` / `none` (used when status is WARNING/FAIL) |
| `finding` | One-line result |
| `evidence` | Raw snippets (commands, paths, log lines) |
| `explanation` | Human language |
| `recommendation` | Safe next step or empty |
| `source` | `systemd` / `journal` / `filesystem` / `flatpak` / `network` / `steam_metadata` / `decky_metadata` / `os_metadata` |
| `confidence` | Optional `high` / `medium` on correlated diagnoses only |

### 4.3 Check protocol

```python
class Check(Protocol):
    id: str
    title: str
    requires_network: bool
    def run(self, ctx: DiagnosticContext) -> CheckResult: ...
```

Checks must not catch-all and return PASS. Unknown command, missing file, or denied journal → `UNKNOWN` or `SKIPPED`.

### 4.4 CommandRunner

All subprocess work goes through one type:

- `argv: list[str]` — never `shell=True`, never string interpolation of user paths into a shell
- timeout (default 15s, longer for Flatpak remote-ls)
- `stdout`, `stderr`, `exit_code`, `timed_out`
- `env` overlay optional; `LANG=C` for parseable CLI tools
- mockable in tests

Forbidden: `systemctl restart/start/stop`, `chmod`/`chown`, `rm`, `flatpak update` (mutating), `flatpak uninstall`, `kill`.

Allowed mutating *nothing*. Creating `deckdoctor-report.md` in the cwd (or `--output`) is the only write.

### 4.5 DiagnosticContext

Built once, shared:

- `home`, `user`, `hostname`
- `decky_home` (`$HOME/homebrew`)
- parsed `/etc/os-release`
- `online` flag (`--no-network`)
- cached command results when two checks would repeat the same argv
- plugin inventory (list of dirs + parsed json)

Checks may add facts (`ctx.facts["plugin_loader_exists"] = True`) for the correlator.

## 5. Correlation

The correlator is a short list of explicit rules, not an LLM and not a historical bug database.

Examples encoded in 0.1:

1. PluginLoader missing **and** GitHub `remaining == 0`  
   → incomplete install; rate limit is a **likely cause** (medium/high depending on unit-file 429).
2. PluginLoader present, service active, backend logs clean, 8080 is not Steam CEF  
   → FACT: port conflict; Decky cannot inject.
3. PluginLoader present, service active, backend clean, CEF looks like Steam, Steam channel is Beta, CEF/React errors  
   → LIKELY: Steam/frontend compatibility, not a broken install.
4. AutoFlatpaks installed, `flatpak` works, `remote-ls` non-zero with a named remote in stderr  
   → plugin is fine; Flatpak remote is not.

Each diagnosis cites the check IDs it used.

## 6. Output (human)

Grouped, scanable, no dump of every PASS by default beyond a compact tick:

```text
DeckDoctor 0.1
SteamOS
  ✓  3.8.x  (BUILD_ID …)  channel stable
  ✗  Updater could not check for updates (timeout)
Decky Loader
  ✓  Installed  v3.2.6  stable
  ✗  Service failed
  …
Problems
  HIGH    Decky service is not running
  MEDIUM  …
Run `deckdoctor report` for a sanitised diagnostic report.
```

FACT vs LIKELY is printed on correlated items.

JSON mirrors `CheckResult` + diagnoses + versions.

## 7. Report

`deckdoctor report` writes Markdown:

- tool version, timestamp (UTC)
- system / SteamOS / Steam client / Decky / plugins
- check summary table
- FAIL and WARNING details with evidence
- log excerpts (already bounded)
- network checks
- Flatpak remotes
- disclaimer: sanitisation is best-effort; review before posting

The sanitizer runs on the **rendered text**, with stable replacements:

| Pattern | Replacement |
|---|---|
| `/home/<username>` | `/home/<USER>` |
| username token | `<USER>` |
| hostname | `<HOSTNAME>` |
| emails | `<EMAIL>` |
| RFC1918 / link-local IPs | `<PRIVATE_IP_N>` |
| MAC | `<MAC>` |
| Steam ID (17-digit) | `<STEAM_ID>` |
| GitHub tokens, bearer, JWT | `<REDACTED>` |
| URLs with `user:pass@` | credentials stripped |
| SSH private key blocks | `<SSH_KEY>` |
| `AKIA…` / generic `*_TOKEN=` | `<REDACTED>` |

Do not claim perfect sanitisation.

## 8. Privilege model

Most checks run as the login user.

| Situation | Status |
|---|---|
| `journalctl -u plugin_loader.service` denied | SKIPPED, explain that the system journal is not readable |
| `flatpak` system remotes need extra privileges | report what *is* readable; do not sudo |
| SteamOS updater needs root and D-Bus unprivileged path failed | SKIPPED/UNKNOWN |

Never spawn `sudo`.

## 9. Package layout

```text
src/deckdoctor/
  __init__.py
  __main__.py          # python -m deckdoctor
  cli.py
  models.py            # Status, CheckResult, Diagnosis
  command.py           # CommandRunner
  context.py
  runner.py            # DiagnosticRunner
  correlator.py
  sanitizer.py
  report.py
  renderer.py
  checks/
    __init__.py        # registry
    sys_os.py
    sys_disk.py
    sys_time.py
    steam_client.py
    decky_install.py
    decky_service.py
    decky_ports.py
    decky_frontend.py
    decky_logs.py
    plugin_inventory.py
    plugin_remote_bin.py
    net_github.py
    net_store.py
    fp_basic.py
    fp_updates.py
    autoflatpaks.py
```

Fixes in a later version live in `deckdoctor/fixes/` with an explicit contract (what changes, reversibility, confirmation). None ship in 0.1.

## 10. Testing

Pytest, no Steam Deck required.

- Fake `CommandRunner` keyed by argv
- Temporary home trees for `healthy`, `decky_missing`, `decky_service_failed`, `decky_frontend_missing`, `github_rate_limited`, `flatpak_broken_remote`, `plugin_remote_binary_failure`, `low_disk_space`
- Sanitizer golden tests
- Correlator unit tests for the three example diagnoses in the product brief

## 11. Distribution

Must work when Decky is completely broken. Must not require `pacman` or a working Flatpak.

0.1:

1. `pip install` / `uv tool install` from the repo for developers
2. PyInstaller onefile x86_64 Linux (same approach PluginLoader uses)
3. `scripts/install.sh` downloads the release binary into `~/.local/bin/deckdoctor`

Not primary: Flatpak, AppImage, Nuitka, zipapp.

## 12. Privacy

- No analytics, no crash reporter, no persistent device ID
- Network only when a check that needs it runs (or unless `--no-network`)
- Reports stay on disk until the user copies them
