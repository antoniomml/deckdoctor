# DeckDoctor

Read-only diagnostics for **SteamOS**, **Decky Loader**, plugins, and **Flatpak**.

```bash
deckdoctor
```

DeckDoctor explains what is going on even if you do not use `systemctl`, `journalctl`, or `flatpak`. It does **not** repair your Deck, does **not** depend on Decky (so it still works when Decky is broken), and does **not** phone home.

Spanish / English: this README is bilingual on purpose.

---

## What it is / Qué es

A local CLI that:

1. **Detects** common SteamOS / Decky / plugin / Flatpak problems
2. **Explains** them in plain language (FACT vs LIKELY CAUSE)
3. **Recommends** a safe next step
4. Optionally writes a **sanitised** Markdown report for GitHub or Discord

It is **not**:

- a Decky plugin
- an automatic fixer (`systemctl restart`, `flatpak update`, `chmod`, …)
- a hardware diagnostic (see DeckDoc for that)
- a Proton / game troubleshooter
- telemetry

## Platforms / Dónde corre

Primary target: **Steam Deck + SteamOS** (Desktop Mode or SSH). The PyInstaller binary is x86_64 Linux.

It also **runs** on other x86_64 Linux handhelds and distros (Bazzite, ChimeraOS, HoloISO, Nobara, …). Behaviour:

| Stack | What happens off SteamOS |
|---|---|
| SteamOS updater / channel / overlay / pending A/B reboot | **Skipped** (those tools and paths are SteamOS-specific) |
| Decky, plugins, Plugin Store | Run if `~/homebrew` exists |
| Flatpak (including EOL runtimes) | Run if `flatpak` is on PATH |
| Steam client / CEF | Run if a Steam datadir is found (`~/.steam/steam` or `~/.local/share/Steam`) |

Bazzite-on-Deck and Bazzite-on-Ally/Legion Go are **best-effort**: same Decky/Flatpak checks, no hardware module, no promise to paper over every image difference. `ID=bazzite` (and a few siblings) is recognised so the CLI says so instead of pretending you are on SteamOS.

Objetivo principal: **Steam Deck + SteamOS**. En Bazzite y otras distros x86_64 el binario arranca; los checks de atomupd/RAUC se omiten y Decky/Flatpak siguen si están instalados. No cubre hardware ni diferencias de cada imagen.

## Install / Instalación

Requires a Steam Deck or similar **x86_64 Linux** handheld. No `pacman`, no Flatpak, no Decky.

**Option A — install script** (downloads the latest release binary and verifies `SHA256SUMS`):

```bash
curl -L https://raw.githubusercontent.com/antoniomml/deckdoctor/main/scripts/install.sh | sh
```

**Option B — download the binary** into `~/.local/bin` and check the sums file:

```bash
mkdir -p ~/.local/bin
curl -L https://github.com/antoniomml/deckdoctor/releases/latest/download/deckdoctor -o ~/.local/bin/deckdoctor
curl -L https://github.com/antoniomml/deckdoctor/releases/latest/download/SHA256SUMS -o /tmp/SHA256SUMS
( cd ~/.local/bin && sha256sum -c /tmp/SHA256SUMS )
chmod +x ~/.local/bin/deckdoctor
```

**Option C — from source** (developers):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
deckdoctor --help
```

## Usage / Uso

```text
deckdoctor                 # diagnose (default)
deckdoctor diagnose
deckdoctor report          # writes ./deckdoctor-report.md (sanitised)
deckdoctor --json
deckdoctor --no-network    # skip GitHub / store / remote Flatpak / updater queries
deckdoctor --lang es       # Spanish UI chrome (or LANG=es_ES.UTF-8)
deckdoctor --ascii         # ASCII marks (OK / X / !) instead of Unicode
deckdoctor --only SYS-DISK,DECKY-INSTALL
deckdoctor --timeout 40    # global deadline in seconds (0 disables; default 60)
```

Exit code `1` means at least one **FAIL**. Warnings do not fail the process. Exit code `2` is an internal tool error.

The PyInstaller onefile binary unpacks on first launch; that can take a few seconds. CI builds it on Ubuntu — treat it as best-effort on SteamOS.

## Network / Red

Only when a check needs it (or unless `--no-network`):

- `https://github.com` (HEAD)
- `https://api.github.com/rate_limit` (does **not** consume the primary GitHub quota)
- `https://github.com/SteamDeckHomebrew/decky-loader/releases/latest` (redirect, not the REST list API)
- `https://plugins.deckbrew.xyz/plugins`
- Flatpak remotes already configured on the device
- SteamOS updater endpoints, if those local tools query them

Nothing is uploaded. There is no DeckDoctor backend.

## Privacy / Privacidad

Reports try to redact username, `/home/<user>`, hostname, emails, private IPs, MACs, Steam IDs, tokens, JWTs, and SSH keys. This is **best-effort**. Read the file before you post it.

## Documentation

- [docs/research.md](docs/research.md) — ecosystem research (2026)
- [docs/design.md](docs/design.md) — architecture
- [docs/checks.md](docs/checks.md) — every check considered
- [docs/roadmap.md](docs/roadmap.md) — 0.1 and later

## License

MIT. See [LICENSE](LICENSE).
