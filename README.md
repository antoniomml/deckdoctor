# DeckDoctor

[![CI](https://github.com/antoniomml/deckdoctor/actions/workflows/ci.yml/badge.svg)](https://github.com/antoniomml/deckdoctor/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/antoniomml/deckdoctor)](https://github.com/antoniomml/deckdoctor/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Your Steam Deck, in plain language.**

Decky is down. Apps will not update. SteamOS says one thing and the Deck does another. DeckDoctor looks at **SteamOS, Decky, plugins, and Flatpak**, then tells you what it saw, why it matters, and what is safe to do next.

It does not change anything while it looks. If a safe fix exists, `deckdoctor fix` shows the plan and asks **y/N**. Pass `-y` to skip the question.

---

## On the Deck

Open **Desktop Mode** (or an SSH terminal) and paste:

```bash
curl -L https://raw.githubusercontent.com/antoniomml/deckdoctor/main/scripts/install.sh | sh
deckdoctor
```

The first launch takes a few seconds. After that, just run `deckdoctor`.

The UI is English. Use `--lang es` only if you want Spanish.

---

## What it looks like

When something is wrong:

```text
🩺  DeckDoctor 0.4.0
    SteamOS 3.8.14 (build 20260624.1, variant steamdeck) · Decky v3.2.6 (stable)
    Internal  81.8 GB free of 224.0 GB
    microSD   292.4 GB free of 469.0 GB
    45 games  ·  16 internal  ·  29 microSD

❌  Decky service
    plugin_loader.service is not running
    → `deckdoctor fix` can start it (may need root).

⚠️  Flatpak updates
    2 update(s) available
    → `deckdoctor fix` can apply the updates.

    ✅  19 ok    ❌  1    ⚠️  1

    📄  deckdoctor report     Discord report
    🔍  deckdoctor -v         every check
    🔧  deckdoctor fix        2 safe plan(s)
    Diagnose never changes anything. `deckdoctor fix` asks first.
```

The summary distinguishes observed issues, unknown results and skipped checks. No issues detected does not imply that every component was verified.

---

## The commands that matter

| You want to | You type |
|---|---|
| See what is going on | `deckdoctor` |
| Save a report for Discord | `deckdoctor report` |
| See the plan, then confirm y/N | `deckdoctor fix` |
| Apply without asking | `deckdoctor fix -y` |

`deckdoctor -v` shows every check, including the ones that passed.

---

## What it can fix (if you ask)

Only a few concrete actions, with their effects and reversibility shown before confirmation:

- Start Decky when it is installed but not running
- Update Flatpak apps
- Create the file Decky needs to show up in Steam
- Make PluginLoader executable

It will not reboot the Deck, uninstall apps, or type your password for you.

---

## Diagnose a symptom

```bash
deckdoctor --symptom library --lang es
deckdoctor --appid 268910 --lang es -v
deckdoctor --symptom controller
deckdoctor --symptom battery
deckdoctor --symptom resume -v
```

Other symptom IDs: `decky`, `updates`, `audio`, `dock`, `performance`. `--appid` selects the game workflow automatically; `--symptom game` requires an AppID. `--only` and `--symptom` are mutually exclusive. Reports retain the selected scope, AppID and network setting. Use `--no-network` for offline diagnostics.

Libraries include registered but missing paths, access/free-space checks and mount metadata when available. Game inspection reads the installed manifest, install folder, explicit compatibility-tool mapping, runtime inventory, prefix presence and default Proton log metadata/header. It does not establish that a game launches or resolve Steam's automatic compatibility selection.

Battery, controller, resume, audio, display and system-pressure checks provide observations and guided next steps. They do not measure button functionality, battery life, audible sound, dock stability or game FPS. The CLI is independent of Decky; a controller-native Gaming Mode interface is still pending.

Save and compare incident reports using identical arguments and language:

```bash
deckdoctor --symptom library --json -o before.json
# Reconnect the missing drive, then run:
deckdoctor --symptom library --json --compare before.json -o after.json
```

Comparison distinguishes changed status/findings/observations and excludes checks that were unknown or skipped in either report. JSON includes detailed before/after observations. A changed observation is not necessarily an improvement. Markdown reports include scope, coverage, evidence and limitations.

Repairs recheck the printed plan before each mutation and run diagnosis afterwards. JSON `repair_results` separates command success (`ok`) from observed resolution (`verified`: true, false or null). A command that completed without verified resolution returns exit 1. Diagnostic exit codes remain: 0 for no FAIL (inspect coverage), 1 for FAIL, 2 for usage/internal errors.

The release executable is available through the installer above. Contributors can also build it locally with `.venv/bin/python pack/build_pyinstaller.py` and run it as `./dist/deckdoctor`.

## Where it runs

Built for the **Steam Deck** (x86_64 Linux). It also starts on other handheld Linux images and does what it can there.

It is not a Windows or macOS app.

---

## Privacy

Everything stays on your machine. No account, no cloud, nothing uploaded.

It may contact GitHub or the Decky store to compare versions. Stay offline with `deckdoctor --no-network`.

Reports try to hide your username, IPs, and tokens. Read the file before you paste it.

---

## License

MIT. See [LICENSE](LICENSE).

---

<details>
<summary>For developers</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
deckdoctor --help
```

Docs: [design](docs/design.md) · [checks](docs/checks.md) · [roadmap](docs/roadmap.md)

Issues: [github.com/antoniomml/deckdoctor/issues](https://github.com/antoniomml/deckdoctor/issues)

</details>
