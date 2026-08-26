# DeckDoctor

[![CI](https://github.com/antoniomml/deckdoctor/actions/workflows/ci.yml/badge.svg)](https://github.com/antoniomml/deckdoctor/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/antoniomml/deckdoctor)](https://github.com/antoniomml/deckdoctor/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Your Steam Deck, in plain language.**

Decky is down. Apps will not update. SteamOS says one thing and the Deck does another. DeckDoctor looks at **SteamOS, Decky, plugins, and Flatpak**, then tells you what it saw, why it matters, and what is safe to do next.

It does not change anything while it looks. If a safe fix exists, it prints a plan. Nothing is applied until you type `--yes`.

---

## On the Deck

Open **Desktop Mode** (or an SSH terminal) and paste:

```bash
curl -L https://raw.githubusercontent.com/antoniomml/deckdoctor/main/scripts/install.sh | sh
deckdoctor
```

The first launch takes a few seconds. After that, just run `deckdoctor`.

Spanish: `deckdoctor --lang es`.

---

## What it looks like

When something is wrong:

```text
🩺  DeckDoctor 0.3.1
    SteamOS 3.8.14 (build 20260624.1, variant steamdeck) · Installed v3.2.6 (stable)

    2 problem(s)

❗  Problems
  ❌  Decky service  ·  serious
      plugin_loader.service is not running
      The unit exists but is inactive. Decky cannot inject into Steam without this service.
      → `deckdoctor fix` can start it (may need root). DeckDoctor diagnose never starts it.

  ⚠️  Flatpak updates  ·  watch
      2 Flatpak update(s) available
      Listed only. Diagnose did not apply updates.
      → `deckdoctor fix` can run `flatpak update -y` after showing the plan. Or update from Discover when convenient.


✅  19 ok   ❌  1   ⚠️  1

👉  What you can do
    📄  deckdoctor report     save a report you can paste on Discord
    🔍  deckdoctor -v         show every check
    🔧  deckdoctor fix        2 safe fix(es) ready (shows a plan, changes nothing yet)
    Looking around never changes anything. Fixes only run with --yes.
```

When everything is fine, you get **All clear** and a ✅.

---

## The commands that matter

| You want to | You type |
|---|---|
| See what is going on | `deckdoctor` |
| Save a report for Discord | `deckdoctor report` |
| Preview safe fixes (changes nothing) | `deckdoctor fix` |
| Apply that plan | `deckdoctor fix --yes` |

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
