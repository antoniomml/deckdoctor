# DeckDoctor checks

All checks considered for DeckDoctor. MVP = 0.1. Commands are **candidates**; the implementation probes what exists and never treats a missing binary as “healthy”.

Status model: `PASS | INFO | WARNING | FAIL | SKIPPED | UNKNOWN`.

Severity applies to WARNING/FAIL: `high | medium | low`.

False-positive risk: `low | medium | high`.

## MVP checks

| ID | Description | Evidence | Command / API | Severity (if bad) | FP risk | Network | Root | MVP |
|---|---|---|---|---|---|---|---|---|
| SYS-OS-VERSION | SteamOS version and build | `/etc/os-release`, atomupd manifest if present | read files | info | low | no | no | yes |
| SYS-OS-CHANNEL | SteamOS update channel | `steamos-select-branch` output | `steamos-select-branch` / `-c` | info | low | no | no | yes |
| SYS-OS-UPDATER | Updater can *check*; pending update vs broken vs unknown | atomupd D-Bus / manager / `steamos-update check` / `--query-only`; never scrape the web | `atomupd-manager check` or `get-update-status`; `steamos-update check`; `steamos-atomupd-client --query-only` | high if check fails | medium (exit codes vary) | optional (check talks to Valve) | no if D-Bus works; else SKIPPED | yes |
| SYS-DISK | Free space on `/home` and `/var` | `df` | `df -Pk /home /var /` | high if &lt;500MB; warn &lt;2GB | low | no | no | yes |
| SYS-TIME | Clock clearly wrong / NTP not synced | `timedatectl` | `timedatectl show` | medium | medium | no | no | yes |
| STEAM-CLIENT | Steam client build and channel | logs / package manifest / VDF | read `~/.steam/steam/logs`, `package/`, config VDF | info; warn on Beta as correlation factor only | medium (parse) | no | no | yes |
| DECKY-INSTALL | Homebrew tree, PluginLoader binary, version, channel | filesystem | stat/read `$HOME/homebrew/services/PluginLoader`, `.loader.version`, settings `branch` | high if incomplete | low | no | no | yes |
| DECKY-SERVICE | systemd unit exists/enabled/active/failed | systemd | `systemctl is-enabled/is-active/status plugin_loader.service` (no start/stop) | high | low | no | no (status often works) | yes |
| DECKY-PORTS | 8080 and 1337 LISTEN + process name | sockets | `ss -ltnp` or `ss -ltn` + `/proc` | high on 8080 conflict | low | no | no (process name may be LIMITED) | yes |
| DECKY-FRONTEND | CEF enable file, `/json` health, injection log signatures | fs + HTTP localhost + journal | read `.cef-enable-remote-debugging`; HTTP GET `127.0.0.1:8080/json`; journal snippets | high for port/CEF facts; medium for Steam Beta correlation | medium | no (localhost only) | no | yes |
| DECKY-LOGS | Recent backend ERROR/CRITICAL/Traceback | journal | `journalctl -b0 -u plugin_loader.service` bounded | medium–high | medium (old errors) | no | maybe SKIPPED | yes |
| PLUGIN-INVENTORY | Installed plugins name/version/dir | `plugin.json` / `package.json` | list `$HOME/homebrew/plugins` only | info | low | no | no | yes |
| PLUGIN-REMOTE-BIN | Declared `remote_binary` vs `bin/` + log signature | package.json, `bin/`, plugin/loader logs | read files; grep signature `Failed Downloading Remote Binaries` | high if declared asset missing | low | no | no | yes |
| NET-GITHUB | github.com reachable; API quota remaining | HTTP | `HEAD https://github.com`; `GET https://api.github.com/rate_limit` | high if remaining=0 | low | yes | no | yes |
| NET-STORE | Plugin Store JSON reachable | HTTP | `GET https://plugins.deckbrew.xyz/plugins` | medium | low | yes | no | yes |
| FP-BASIC | flatpak binary, remotes listable; custom remotes ≠ error | CLI | `flatpak --version`; `flatpak remotes` | medium–high if binary/remotes fail | low | no | no | yes |
| FP-UPDATES | Updates available vs **check failed** | CLI | `flatpak remote-ls --updates` (`LANG=C`); non-zero ≠ 0 updates | medium | low | yes (remote fetch) | no | yes |
| AUTOFLATPAKS | If plugin installed: remote-ls health + plugin logs | plugin dir + flatpak + logs | detect plugin; `flatpak remote-ls --columns=ref,origin -a`; read plugin log | medium–high | low | yes (same as remote-ls) | no | yes |

## Considered, not MVP (0.2+)

| ID | Description | Evidence | Command / API | Severity | FP risk | Network | Root | MVP | Why deferred |
|---|---|---|---|---|---|---|---|---|---|
| SYS-OS-REBOOT | Pending reboot to new slot | RAUC/atomupd/bootconf files | probe known paths | medium | high (paths vary) | no | maybe | no | No stable SteamOS 3 file confirmed; UNKNOWN worse than a lie |
| SYS-READONLY | Root unexpectedly RW | `steamos-readonly status` | `steamos-readonly` | low | medium | no | no | no | Informational; easy to misread overlays |
| SYS-OVERLAY | Edited atomupd/rauc in overlay | `/var/lib/overlays/etc/upper` | list specific files | medium | medium | no | maybe | no | Useful but invasive to explain; 0.2 |
| DECKY-UPDATE | Newer Decky stable available | local version vs `releases/latest` redirect | HTTP redirect, no `/releases` API | low | low | yes | no | no | Nice-to-have; folded into DECKY-INSTALL as INFO if cheap |
| DECKY-CEF-FORWARD | 8081 portforward unit | systemd | `systemctl status steam-web-debug-portforward.service` | info | low | no | no | no | Optional developer feature |
| PLUGIN-STORE-UPDATES | N plugins have store updates | store JSON vs local names | GET store + match `plugin.json` name | low | **high** | yes | no | no | Name matching is brittle |
| PLUGIN-LOAD-STATE | Backend loaded vs failed per plugin | loader journal lines | journal + inventory | medium | medium | no | maybe | no | Partially covered by DECKY-LOGS + inventory |
| FP-EOL | EOL runtimes + apps using them | metadata `EndOfLife` | `flatpak info --show-metadata`; **not** assumed `--columns=end-of-life` | low | medium | maybe | no | no | Column not in current man page; probe in 0.2 |
| FP-BROKEN-REF | Named invalid ref in a remote | remote-ls / repair dry-run stderr | `flatpak remote-ls`; `flatpak repair --dry-run` | medium | medium | yes | no | no | Covered in spirit by FP-UPDATES + AUTOFLATPAKS |
| FP-FLATHUB | Flathub specifically reachable | remotes + HTTP | HEAD configured Flathub URL | medium | low | yes | no | no | Folded into FP-BASIC/FP-UPDATES |
| NET-DNS | Resolver works | `getaddrinfo` for github.com | libc, not a scanner | medium | low | yes | no | no | Implied by NET-GITHUB |
| NET-ATOMUPD | SteamOS update endpoint reachable | client.conf QueryUrl | HEAD QueryUrl | medium | low | yes | no | no | Part of SYS-OS-UPDATER when it talks to the network |
| HW-* | Battery, SMART, GPU, fan, Wi-Fi perf | sysfs/smartctl | — | — | — | — | — | no | Out of scope (DeckDoc) |
| GAME-* | Proton, shaders, prefixes | Steam compatdata | — | — | — | — | — | no | Out of scope |

## Notes for implementers

- **SYS-OS-UPDATER:** if the check command times out or the daemon is dead, status is `FAIL` or `UNKNOWN`, never PASS “up to date”.
- **DECKY-PORTS:** expected owner of 8080 is `steamwebhelper`; of 1337 is `PluginLoader`. Do not kill the occupant.
- **DECKY-FRONTEND:** localhost HTTP is not “network” in the privacy sense; `--no-network` still allows it.
- **AUTOFLATPAKS:** SKIPPED with INFO if the plugin directory is absent. Do not copy AutoFlatpaks’ regex parser.
- **GitHub:** only `rate_limit` + `github.com` HEAD (+ optional latest-release redirect). No user credentials.
