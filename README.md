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

## Install / Instalación

Requires a Steam Deck (or similar x86_64 Linux handheld). No `pacman`, no Flatpak, no Decky.

**Option A — install script** (downloads the latest release binary):

```bash
curl -L https://raw.githubusercontent.com/antoniomml/deckdoctor/main/scripts/install.sh | sh
```

**Option B — download the binary** into `~/.local/bin`:

```bash
mkdir -p ~/.local/bin
curl -L https://github.com/antoniomml/deckdoctor/releases/latest/download/deckdoctor -o ~/.local/bin/deckdoctor
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
```

Exit code `1` means at least one **FAIL**. Warnings do not fail the process.

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
