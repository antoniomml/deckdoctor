# DeckDoctor research

**Date:** 2026-08-25  
**Scope:** SteamOS 3.x on Steam Deck, Decky Loader, Decky plugins, Flatpak, AutoFlatpaks.  
**Method:** official repositories, current source, official docs, recent issues. Community posts used only as secondary evidence.

This document records what is true *now*, not folklore from 2024. An old issue can identify a durable *signature*; it does not prove the bug still exists.

## 1. Product gap

Users and maintainers repeatedly ask the same questions after a SteamOS or Steam client update:

- Is Decky installed, or did the installer lie?
- Is the backend running while the Quick Access Menu (QAM) is empty?
- Is GitHub rate-limiting the installer?
- Are Flatpak remotes breaking AutoFlatpaks?
- Which logs should be attached to a GitHub issue?

Nobody currently answers those questions with a local, read-only, correlating tool.

DeckDoctor exists to turn:

```text
system state → structured checks → correlation → diagnosis
  → human-readable explanation → safe recommendation
```

## 2. Alternatives (and why they are not DeckDoctor)

| Project | What it does | Gap |
|---|---|---|
| [DeckDoc](https://github.com/deucebucket/deckdoc) v3.4 | Hardware/OS incident response: GPU, battery, docks, SMART, display | Explicitly out of DeckDoctor 0.1 scope. No Decky/plugin/Flatpak diagnosis. |
| Deck Toolbox | One-click *fixes* (reset Steam/Gamescope, uninstall Decky) | Mutating, not diagnostic. |
| Decky wiki / Discord | Manual troubleshooting | Maintainers still ask for logs by hand. |
| Decky `#849` | Request for `--version` on the loader | Version dump only; not a diagnostic CLI. |

DeckDoctor must not become DeckDoc. Hardware, Proton, and game diagnostics stay out of 0.1.

## 3. SteamOS (2026)

SteamOS 3 is an image-based A/B system. Updates are **not** `pacman -Syu` on the live root.

### 3.1 Identity

Observed sources (must be probed; do not assume a single path):

- `/etc/os-release` — `NAME`, `ID=steamos`, `VERSION_ID`, `BUILD_ID`, `VARIANT_ID` (typically `steamdeck`)
- `/etc/steamos-atomupd/manifest.json` or `/lib/steamos-atomupd/manifest.json` — `version`, `buildid`, `variant`

Do **not** scrape a website and call the result “up to date”.

### 3.2 Update stack

Current components, confirmed from Valve issues, `atomupd-daemon` source, and SteamOS teardown notes:

| Piece | Role |
|---|---|
| `atomupd-daemon` | D-Bus IPC so unprivileged processes (Steam) can query/apply OS updates |
| `atomupd-manager` | CLI around the daemon (`check`, `get-update-status`, `update`, `switch-variant`, `custom-update` as of SteamOS 3.8) |
| `steamos-atomupd-client` | Python client; `--query-only` asks if an update exists |
| `steamos-update` | User-facing wrapper. `steamos-update check` is the documented read-only query |
| RAUC + casync | Writes the inactive slot |
| `/etc/steamos-atomupd/client.conf` | `QueryUrl`, `ImagesUrl`, `MetaUrl`, `Variants` |

Documented query endpoint in real configs:

```text
https://steamdeck-atomupd.steamos.cloud/updates
```

Also: `https://steamdeck-images.steamos.cloud/` and `https://steamdeck-atomupd.steamos.cloud/meta`.

Channel selection: `steamos-select-branch` (Valve issues use `steamos-select-branch -c` for the current branch: `rel`/`stable`, `beta`, `preview`, `main`).

### 3.3 Failure signatures (still relevant)

| Signature | Source | Notes |
|---|---|---|
| `Failed to check for updates` / missing `client.conf` | ValveSoftware/SteamOS `#1132` (2023, *pattern* still cited) | Overlay-edited `/etc` can break atomupd |
| `atomupd.service` failed; `NameHasNoOwner` | `#1691` | Daemon not running ≠ “up to date” |
| `write() failed: No space left on device` while writing `preferences.conf` | `#1695` | `/var` full breaks the updater |
| Timeout talking to atomupd | user reports + Valve comments | Must surface as updater **ERROR**, never “up to date” |

Pending reboot: **do not** assume `/var/run/reboot-required` (SteamOS 2 wiki). Probe RAUC/atomupd/bootconf; if nothing reliable is found, report `UNKNOWN`.

### 3.4 Filesystem model

- Root filesystem is read-only.
- Persistent overlays live under `/var/lib/overlays/etc/upper`.
- Decky lives under `$HOME/homebrew` (writable). DeckDoctor must never `steamos-readonly disable` or write the overlay.
- Informational only: if `steamos-readonly` reports an unexpected RW root, mention it. Do not “fix” it.

## 4. Steam client

Decky injects into Steam’s Game Mode UI (CEF / SharedJSContext). Steam *client* updates independently of SteamOS and have repeatedly made Decky vanish from the QAM while the backend stayed healthy.

### 4.1 Local identity (no internet required)

Candidates to probe:

- `~/.steam/steam/logs/` (`console_log.txt`, `bootstrap_log.txt`) — `version(...)` / build id
- `~/.steam/steam/package/steam_client_ubuntu12.installed`
- Steam VDF config for the client update channel (Deck Stable vs Beta)

If a parse is fragile, return `UNKNOWN`. Do **not** keep a hardcoded incompatibility matrix of `Steam build X × Decky Y`.

### 4.2 Recurring 2026 issues

| Issue | Date | What happened |
|---|---|---|
| decky-loader `#888` | 2026-03, still open | Steam client beta `1773983034` removed Decky from QAM. Workaround: Deck Stable channel. |
| `#903`, `#918` | 2026 | React error `#130` / “Something went wrong while displaying this content”. Sometimes a *plugin* (Bluetooth, CSS Loader), sometimes the loader vs a new Steam UI. |
| `#926` | 2026-06/07, open | “Latest Steam Update Bricks Decky”. v3.2.6 fixed some cases; later Steam stable updates rebroke others. Maintainers: disable plugins, latest loader, full reboot, then blame Steam/CEF. |

Durable signatures, not one-off versions:

- Backend running + QAM empty
- `Minified React error #130`
- `An error occurred while rendering this content`
- Steam Beta channel as a *correlation factor*, not a verdict

## 5. Decky Loader (current)

**Repo:** [SteamDeckHomebrew/decky-loader](https://github.com/SteamDeckHomebrew/decky-loader)  
**Latest stable as of this research:** `v3.2.6` (2026-06-24)  
**Installer:** [SteamDeckHomebrew/decky-installer](https://github.com/SteamDeckHomebrew/decky-installer) — `dist/` scripts inside decky-loader itself are **deprecated**.

### 5.1 Layout (from installer + `decky.pyi` + systemd unit)

| Item | Path / name |
|---|---|
| `DECKY_HOME` | `$USER_HOME/homebrew` |
| PluginLoader binary | `$HOME/homebrew/services/PluginLoader` (PyInstaller) |
| Version pin | `$HOME/homebrew/services/.loader.version` |
| Channel | settings JSON `branch`: `0` stable, `1` prerelease (`updater.py`) |
| Plugins | `$HOME/homebrew/plugins/<dir>/plugin.json` + `package.json` + `main.py` |
| Settings | `$HOME/homebrew/settings/` |
| Plugin logs | `$HOME/homebrew/logs/<plugin>/plugin.log` |
| systemd unit **on disk** | `/etc/systemd/system/plugin_loader.service` (template `plugin_loader-release.service` is copied and renamed) |
| Unit user | `User=root` |
| CEF enable file | `~/.steam/steam/.cef-enable-remote-debugging` (and Flatpak Steam equivalent) |

Default fallback in `localplatformlinux.py` if env is missing: `/home/deck/homebrew`. DeckDoctor must resolve the real user home, not assume `deck`.

### 5.2 Ports (from current source, not folklore)

| Port | Owner expected | Role |
|---|---|---|
| **8080** | `steamwebhelper` | Steam CEF debugger. `injector.py`: `BASE_ADDRESS = "http://localhost:8080"`. Decky did **not** choose this port. Syncthing is the documented conflict. |
| **1337** | PluginLoader | Decky HTTP server (`SERVER_PORT` default). Frontend: `import('http://localhost:1337/frontend/...')`. |
| **8081** | optional `steam-web-debug-portforward.service` | CEF forwarding to the LAN. Not the local injection port. |

Health of 8080: `GET http://127.0.0.1:8080/json` should look like a Chrome DevTools target list. A `404 page not found` means *something else* is bound to 8080.

### 5.3 Frontend injection

Flow:

1. Steam starts with `.cef-enable-remote-debugging` present.
2. `steamwebhelper` listens on 8080.
3. PluginLoader connects to `/json`, finds the GamepadUI tab, injects JS that imports `http://localhost:1337/frontend/...`.

Reliable **FACT** signals:

- PluginLoader missing / unit failed / unit file is GitHub’s `429: Too Many Requests` HTML
- 8080 owned by a non-Steam process
- `.cef-enable-remote-debugging` missing
- Journal: `Couldn't connect to debugger`, `Failed to inject`, `The request to http://localhost:8080/json`

**LIKELY (medium confidence):** backend healthy + CEF looks like Steam + Steam Beta + React errors in `~/.steam/steam/logs/cef_log.txt`.

**Not reliable in 0.1:** asserting “Decky is missing from QAM” without inspecting CEF tabs. That depends on Game Mode actually running.

### 5.4 Logs maintainers ask for

From decky-loader issue templates and comments (`#631`, `#697`, wiki):

```bash
journalctl -b0 -u plugin_loader.service
# plus
~/.steam/steam/logs/cef_log.txt
~/.steam/steam/logs/cef_log.previous.txt
~/homebrew/logs/**/plugin.log
```

DeckDoctor should collect bounded excerpts (last 15 minutes *or* 100 relevant lines). System journal may be unreadable without `systemd-journal` membership or root → `SKIPPED`/`LIMITED`, not a fake FAIL.

### 5.5 Incomplete install / GitHub rate limit (2026, still open)

**CLI installer** (`cli/install_release.sh`) *does* HEAD `api.github.com/.../releases` and aborts on non-200.

**GUI installer** (`gui/user_install_script.sh`, what `.desktop` runs) historically did **not**. As of 2026-07:

- decky-loader `#940` (OPEN): GUI hits unauthenticated 60 req/h limit → `jq: Cannot index string with string "prerelease"` → empty `DOWNLOADURL` → **PluginLoader never downloaded** → installer still prints “Install finished”.
- It `rm -rf services/` *before* the API call, so a failed “update” destroys a working install.
- `plugin_loader.service` can be replaced with the GitHub `429 Too Many Requests` HTML (`#822` pattern).
- Discussion `#936` (2026-07-05): same `jq` error, same rate limit.
- `decky-installer#28` (OPEN, not merged): skip API for stable (`releases/latest/download/PluginLoader`), validate before `rm -rf`.

Unauthenticated GitHub REST limit: **60 requests/hour/IP**. CGNAT shares that quota.

Correct *check* (does **not** consume primary quota): `GET https://api.github.com/rate_limit`.  
Connectivity: `HEAD https://github.com`.  
Do **not** call `/repos/.../releases` from a health check. For “is a newer stable Decky out?” use the `releases/latest` redirect, which is not the REST API.

## 6. Plugin architecture

- Each plugin directory under `~/homebrew/plugins/` has `plugin.json` (`name`, `author`, `flags`, optional `api_version`) and `package.json` (`version`, optional `remote_binary`).
- Backend: `main.py` loaded by `loader.py`. Failures log `Could not load {file}`.
- Frontend: `dist/index.js` injected into Steam.
- Root plugins: `flags` may include `_root`.
- Remote binaries: `package.json` → `remote_binary[]` with `name`, `url`, `sha256hash`, downloaded into `<plugin>/bin/`. Failure signature (still in `browser.py`): **`Failed Downloading Remote Binaries`**. Historical `#608`; still seen with Framegen-class plugins that ship large GitHub assets.

Plugin inventory must **only** walk `~/homebrew/plugins`, never the whole home directory.

## 7. Plugin Store

- UI store: [plugins.deckbrew.xyz](https://plugins.deckbrew.xyz)
- JSON: `https://plugins.deckbrew.xyz/plugins`
- Testing: `https://testing.deckbrew.xyz`
- Code: [SteamDeckHomebrew/decky-plugin-store](https://github.com/SteamDeckHomebrew/decky-plugin-store)

A reachable local Decky + unreachable store is a distinct diagnosis from “Decky is broken”.

Plugin *updates* via store matching are easy to get wrong (name mismatches). Out of 0.1.

## 8. Flatpak on SteamOS

Default install is **system** Flatpak (`/var/lib/flatpak`), which AutoFlatpaks also assumes. User remotes (`--user`) exist and must not be treated as errors.

Read-only inspection:

| Intent | Command family |
|---|---|
| Binary present | `flatpak --version` |
| Remotes | `flatpak remotes --columns=name,options,url,title,filter` (probe columns) |
| Installed refs | `flatpak list --columns=...` |
| Updates available | `flatpak remote-ls --updates` |
| Remote package list | `flatpak remote-ls --columns=ref,origin -a` |
| Repair dry-run | `flatpak repair --dry-run` |
| Metadata / EOL | `flatpak info --show-metadata` / `EndOfLife` — **do not** assume `flatpak list --columns=end-of-life` exists (not in current man page) |

Never run `flatpak update` (mutating) or `flatpak uninstall`.

Custom remotes are allowed. Disabled/unreachable **Flathub** is a warning; a user’s `kdeapps` remote with dead refs is a *finding*, not a lecture.

A failed update *check* (non-zero exit, fetch error) must be `FAIL`/`UNKNOWN`, never “0 updates”.

## 9. AutoFlatpaks

**Repo:** [jurassicplayer/decky-autoflatpaks](https://github.com/jurassicplayer/decky-autoflatpaks)  
**Latest release researched:** `v1.6.8` (2025-06-14)

### 9.1 Current code (main `getRemotePackageList`)

Uses **`flatpak remote-ls --columns=... -a`**, not `flatpak update --no-deps`.

`getUpdatePackageList` still runs `flatpak update --no-deps` and regex-parses the table. Broken remotes / missing refs / EOL messages make that exit non-zero and the UI look stuck.

Issue `#18` / `#22` (“getRemotePackageList broken”) is **CLOSED** (2025-06). v1.6.8 added a degraded-state notification when the remote list fails. The underlying Flatpak problem (stale remotes like `kdeapps` pointing at NX DNS `distribute.kde.org`) is **not** gone.

DeckDoctor should diagnose **Flatpak**, then, if the plugin is installed, correlate:

- plugin dir present
- recent `backend.log` / plugin.log
- `flatpak remote-ls` exit + stderr (invalid ref, remote fetch error)

Do not reimplement AutoFlatpaks’ regex.

## 10. Recurring signatures DeckDoctor should recognize

Prefer durable log/filesystem signatures over version pin lists.

| Signature | Maps to |
|---|---|
| `PluginLoader` missing after installer “finished” | Incomplete install |
| `jq: Cannot index string with string "prerelease"` | GitHub API returned an error object (usually rate limit) |
| Unit file starts with `429: Too Many Requests` | Installer saved GitHub HTML as systemd unit |
| `chown: cannot access '.../services/*'` | Only dotfiles left in `services/` |
| `plugin_loader.service: Failed at step EXEC` + `No such file or directory` | Missing binary, or dirlock/encryption (`#879`) |
| `Failed at step EXEC` + `Permission denied` | Binary not executable / bad ownership |
| `Failed Downloading Remote Binaries` | Plugin `remote_binary` download failed |
| `Could not load` + traceback in loader | Plugin backend import failure |
| `Couldn't connect to debugger` / `/json` 404 | CEF port conflict or Steam not exposing debugger |
| `Minified React error #130` | Frontend/Steam/plugin render crash |
| `is end-of-life` / ostree fetch errors naming a remote | Flatpak remote/ref problem |
| GitHub `X-RateLimit-Remaining: 0` | Installer/updater cannot use the API |

## 11. Network the tool is allowed to touch

Documented, optional, no telemetry:

- `https://github.com` (HEAD)
- `https://api.github.com/rate_limit` (GET; does not consume primary quota)
- `https://github.com/SteamDeckHomebrew/decky-loader/releases/latest` (redirect only)
- `https://plugins.deckbrew.xyz/plugins`
- Flathub remote URL as configured locally
- SteamOS `QueryUrl` from local `client.conf` (HEAD/GET metadata, no image download)

No DeckDoctor backend. No device IDs. No automatic report upload.

## 12. Implications for the 0.1 implementation

1. CLI first, **not** a Decky plugin — it must work when Decky does not start.
2. Read-only. No `systemctl restart`, `chmod`, `flatpak update`, or installer reruns.
3. Distinguish FACT vs LIKELY. Prefer `UNKNOWN` over a comforting lie.
4. ~16 high-quality checks beat 60 shallow probes.
5. Tests must not need a Steam Deck: mock `CommandRunner` and fixture trees.

## 13. Sources

- https://github.com/SteamDeckHomebrew/decky-loader (backend 2026: `injector.py`, `browser.py`, `updater.py`, `localplatformlinux.py`, `helpers.py`)
- https://github.com/SteamDeckHomebrew/decky-installer (`cli/install_release.sh`, GUI script, PR `#28`)
- https://github.com/SteamDeckHomebrew/decky-plugin-store
- https://wiki.deckbrew.xyz
- https://github.com/jurassicplayer/decky-autoflatpaks (`main.py`, releases, issues `#18`/`#22`)
- https://github.com/evlaV/atomupd-daemon
- https://github.com/ValveSoftware/SteamOS (issues `#1132`, `#1691`, `#1695`, `#1709`)
- GitHub REST rate-limit docs (2026-03-10 API version): `GET /rate_limit` does not count against the primary limit; unauthenticated core limit is 60/hour/IP
- Secondary: DeckDoc README (scope contrast only)
