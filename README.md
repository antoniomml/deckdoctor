# DeckDoctor

[![CI](https://github.com/antoniomml/deckdoctor/actions/workflows/ci.yml/badge.svg)](https://github.com/antoniomml/deckdoctor/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/antoniomml/deckdoctor)](https://github.com/antoniomml/deckdoctor/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Your Steam Deck, in plain language.**

Decky se ha caído, las apps no actualizan, SteamOS dice una cosa y el Deck hace otra. DeckDoctor mira **SteamOS, Decky, los plugins y Flatpak** y te lo cuenta en claro: qué ha visto, por qué importa y qué puedes hacer.

No toca nada al mirar. Si hay un arreglo seguro, te enseña el plan. Solo se aplica si tú escribes `--yes`.

---

## En el Deck

Abre el **modo escritorio** (o una terminal por SSH) y pega esto:

```bash
curl -L https://raw.githubusercontent.com/antoniomml/deckdoctor/main/scripts/install.sh | sh
deckdoctor --lang es
```

La primera vez tarda unos segundos. Después, cuando quieras, escribe `deckdoctor`.

---

## Cómo se ve

Esto es la salida real de DeckDoctor (no un mock):

```text
🩺  DeckDoctor 0.3.0
    SteamOS 3.8.14 (build 20260624.1, variant steamdeck) · Instalado v3.2.6 (stable)

    2 problema(s)

❗  Problemas
  ❌  Servicio de Decky  ·  grave
      plugin_loader.service no está en ejecución
      La unidad existe pero está inactiva. Sin este servicio Decky no puede inyectarse en Steam.
      → `deckdoctor fix` puede arrancarlo (puede hacer falta root). El diagnóstico nunca lo arranca.

  ⚠️  Actualizaciones Flatpak  ·  aviso
      2 actualización(es) Flatpak disponible(s)
      Solo se listan. El diagnóstico no aplicó actualizaciones.
      → `deckdoctor fix` puede ejecutar `flatpak update -y` tras mostrar el plan. O actualiza desde Discover.


✅  19 bien   ❌  1   ⚠️  1

👉  Qué puedes hacer
    📄  deckdoctor report     guarda un informe para pegar en Discord
    🔍  deckdoctor -v         ver todas las comprobaciones
    🔧  deckdoctor fix        2 arreglo(s) seguro(s) (enseña el plan, no cambia nada aún)
    Mirar no cambia nada. Los arreglos solo se aplican con --yes.
```

Si todo va bien, ves **Todo en orden** y un ✅.

¿Prefieres inglés? `deckdoctor --lang en` (o deja que use el idioma del sistema).

---

## Los tres comandos que importan

| Lo que quieres | Lo que escribes |
|---|---|
| Que mire y te lo explique | `deckdoctor` |
| Un informe para pegar en Discord | `deckdoctor report` |
| Ver el plan de arreglos (sin aplicar nada) | `deckdoctor fix` |
| Aplicar ese plan | `deckdoctor fix --yes` |

`deckdoctor -v` enseña cada comprobación, también las que están bien.

---

## Qué puede arreglar (si se lo pides)

Solo cosas concretas y reversibles:

- Arrancar Decky si está instalado pero parado
- Actualizar las apps de Flatpak
- Crear el archivo que Decky necesita para aparecer en Steam
- Marcar PluginLoader como ejecutable

Nunca reinicia el Deck. Nunca borra apps. Nunca escribe la contraseña por ti.

---

## Dónde corre

Está hecho para el **Steam Deck**. También arranca en otros Linux de mano; ahí hace lo que puede.

---

## Privacidad

Todo ocurre en tu máquina. No hay cuenta, no hay nube, no se sube nada.

A veces consulta GitHub o la tienda de Decky para comparar versiones. Si no quieres red: `deckdoctor --no-network`.

El informe intenta ocultar tu usuario, IPs y tokens. Léelo antes de pegarlo.

---

## License

MIT. See [LICENSE](LICENSE).

---

<details>
<summary>Si programas</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
deckdoctor --help
```

Docs: [design](docs/design.md) · [checks](docs/checks.md) · [roadmap](docs/roadmap.md)

Issues: [github.com/antoniomml/deckdoctor/issues](https://github.com/antoniomml/deckdoctor/issues)

</details>
