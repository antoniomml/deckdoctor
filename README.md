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
🩺  DeckDoctor 0.3.4
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

When everything is fine, you get **All clear** and a ✅.

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

Only a few concrete, reversible things:

- Start Decky when it is installed but not running
- Update Flatpak apps
- Create the file Decky needs to show up in Steam
- Make PluginLoader executable

It will not reboot the Deck, uninstall apps, or type your password for you.

---

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
