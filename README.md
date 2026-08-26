# DeckDoctor

[![CI](https://github.com/antoniomml/deckdoctor/actions/workflows/ci.yml/badge.svg)](https://github.com/antoniomml/deckdoctor/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/antoniomml/deckdoctor)](https://github.com/antoniomml/deckdoctor/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Diagnose SteamOS, Decky Loader, plugins, and Flatpak — locally, in plain language.**

Decky se rompe, el QAM está vacío, Flatpak está viejo, SteamOS dice una cosa y el Deck hace otra. DeckDoctor mira el sistema y te dice **qué ha visto**, **por qué importa** y **qué es seguro hacer**.

No es un plugin de Decky (funciona aunque Decky esté caído). No telemetría. El diagnóstico no toca nada. Los arreglos son opt-in y hay que pedirlos con `--yes`.

```bash
curl -L https://raw.githubusercontent.com/antoniomml/deckdoctor/main/scripts/install.sh | sh
deckdoctor
```

---

## Qué ves

```text
DeckDoctor 0.3.0
SteamOS 3.7.13  ·  Decky Loader 3.1.11

  ·  Problems  2  ·  Diagnoses  1

Diagnosis
  LIKELY CAUSE · medium
  Decky backend is installed but the service is not running
    plugin_loader.service is disabled or inactive.
    → Enable and start plugin_loader.service.

Problems
  ✗  DECKY-SERVICE  HIGH
      plugin_loader.service is not running
      → deckdoctor fix

  ⚠  FP-UPDATES  MEDIUM
      3 Flatpak apps have updates
      → flatpak update -y

Next
deckdoctor report      sanitised diagnostic report
deckdoctor -v          every check
deckdoctor fix         2 safe fix(es) available
diagnose never mutates the system. fix prints a plan and needs --yes.
```

Español: `deckdoctor --lang es` (o `LANG=es_ES.UTF-8`).

---

## Install / Instalación

Binario **x86_64 Linux** (Steam Deck, Bazzite, etc.). Sin `pacman`, sin Flatpak, sin Decky.

**A — script** (descarga el último release y comprueba `SHA256SUMS`):

```bash
curl -L https://raw.githubusercontent.com/antoniomml/deckdoctor/main/scripts/install.sh | sh
```

**B — a mano:**

```bash
mkdir -p ~/.local/bin
curl -L https://github.com/antoniomml/deckdoctor/releases/latest/download/deckdoctor -o ~/.local/bin/deckdoctor
curl -L https://github.com/antoniomml/deckdoctor/releases/latest/download/SHA256SUMS -o /tmp/SHA256SUMS
( cd ~/.local/bin && sha256sum -c /tmp/SHA256SUMS )
chmod +x ~/.local/bin/deckdoctor
```

**C — desde fuente** (desarrollo):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
deckdoctor --help
```

La primera arrancada del binario PyInstaller tarda unos segundos. CI lo construye en Ubuntu; en SteamOS es best-effort.

---

## Commands / Comandos

```text
deckdoctor                 # diagnose (por defecto) — compacto, solo lectura
deckdoctor -v              # cada check, incluidos PASS / SKIPPED
deckdoctor report          # escribe ./deckdoctor-report.md (sanitizado)
deckdoctor checks          # IDs para --only
deckdoctor fix             # plan de arreglos seguros (no aplica nada)
deckdoctor fix --yes       # aplica ese plan
deckdoctor fix decky-service --yes
deckdoctor --json
deckdoctor --no-network    # sin GitHub / store / remotes Flatpak
deckdoctor --lang es
deckdoctor --ascii         # marcas ASCII (OK / X / !)
deckdoctor --only SYS-DISK,DECKY-INSTALL
deckdoctor --timeout 40    # deadline global en segundos (0 = sin límite; default 60)
```

Código de salida `1`: hay un **FAIL**, o un fix pedido que no se aplicó. Los WARNING no fallan el diagnose. `2` es error interno.

`deckdoctor fix` solo ofrece mutaciones que puede nombrar:

| id | qué hace |
|---|---|
| `pluginloader-exec` | `chmod +x` en PluginLoader (nunca `chmod 777`) |
| `cef-debug` | crea `~/.steam/steam/.cef-enable-remote-debugging` |
| `decky-service` | `systemctl enable --now plugin_loader.service` (puede pedir root; DeckDoctor **nunca** lanza `sudo`) |
| `flatpak-update` | `flatpak update -y` si había actualizaciones listadas |

No reinicia, no mata procesos, no desinstala Flatpaks, no escribe el root de solo lectura, no reinstala Decky.

---

## Platforms / Dónde corre

Objetivo principal: **Steam Deck + SteamOS** (Desktop Mode o SSH).

También arranca en otros Linux x86_64 (Bazzite, ChimeraOS, HoloISO, Nobara, …):

| Stack | Fuera de SteamOS |
|---|---|
| Updater / canal / overlay / reboot A/B de SteamOS | **Omitido** |
| Decky, plugins, Plugin Store | Si existe `~/homebrew` |
| Flatpak (incl. runtimes EOL) | Si `flatpak` está en PATH |
| Cliente Steam / CEF | Si hay datadir (`~/.steam/steam` o `~/.local/share/Steam`) |

Bazzite-on-Deck y Bazzite-on-Ally/Legion Go son **best-effort**: mismos checks de Decky/Flatpak, sin módulo de hardware, sin promesa de cubrir cada imagen.

---

## Network / Red

Solo cuando un check lo necesita (o salvo `--no-network`):

- `https://github.com` (HEAD)
- `https://api.github.com/rate_limit` (no gasta la cuota principal)
- `https://github.com/SteamDeckHomebrew/decky-loader/releases/latest`
- `https://plugins.deckbrew.xyz/plugins`
- remotes Flatpak ya configurados en el dispositivo
- endpoints del updater de SteamOS, si las herramientas locales los consultan

Nada se sube. No hay backend de DeckDoctor.

---

## Privacy / Privacidad

El informe intenta redactar usuario, `/home/<user>`, hostname, emails, IPs privadas, MACs, Steam IDs, tokens, JWTs y claves SSH. Es **best-effort**: léelo antes de pegarlo en Discord o GitHub.

DeckDoctor **no** es:

- un plugin de Decky
- un diagnóstico de hardware (eso es [DeckDoc](https://github.com/deucebucket/deckdoc))
- un troubleshooter de Proton / juegos
- telemetría
- permiso para `chmod 777`, matar procesos o reiniciar por ti

---

## Docs

- [docs/research.md](docs/research.md) — ecosistema (2026)
- [docs/design.md](docs/design.md) — arquitectura
- [docs/checks.md](docs/checks.md) — cada check considerado
- [docs/roadmap.md](docs/roadmap.md) — 0.1 y lo que sigue

Issues: [github.com/antoniomml/deckdoctor/issues](https://github.com/antoniomml/deckdoctor/issues)

---

## License

MIT. Ver [LICENSE](LICENSE).
