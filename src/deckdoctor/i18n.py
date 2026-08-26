from __future__ import annotations

import os
from typing import Literal

from deckdoctor.i18n_checks import CHECK_EN, CHECK_ES

Locale = Literal["en", "es"]

_EN: dict[str, str] = {
    "cli.description": "Diagnostics for SteamOS, Decky Loader, plugins, and Flatpak. Diagnose is read-only; fix is opt-in.",
    "cli.json": "Print machine-readable JSON",
    "cli.no_network": "Skip checks that need the internet",
    "cli.output": "Report path (for the report command)",
    "cli.command": "diagnose (default), report, fix, or checks",
    "cli.target": "Optional fix id (only with the fix command)",
    "cli.ascii": "Use ASCII status marks (OK/X/!) instead of Unicode",
    "cli.only": "Run only these check IDs (comma-separated)",
    "cli.timeout": "Global deadline in seconds (0 disables). Default: 60",
    "cli.lang": "UI language: en or es (default: from LANG)",
    "cli.verbose": "Show every check, including PASS and SKIPPED",
    "cli.no_color": "Disable ANSI colours",
    "cli.yes": "Apply the printed fix plan (never the default)",
    "skip.no_network": "Skipped (--no-network)",
    "skip.no_network.explain": "This check needs the network or a remote query.",
    "skip.only": "Skipped (--only)",
    "skip.only.explain": "Not in the --only list.",
    "skip.timeout": "Skipped (global timeout)",
    "skip.timeout.explain": "DeckDoctor hit the global deadline; remaining checks were not run.",
    "group.system": "System",
    "group.decky": "Decky Loader",
    "group.plugins": "Plugins",
    "group.flatpak": "Flatpak",
    "group.network": "Network",
    "ui.diagnosis": "What's going on",
    "ui.fact": "What we saw",
    "ui.likely": "Likely cause",
    "ui.recommended": "Recommended: {text}",
    "ui.problems": "Problems",
    "ui.problems_count": "{count} problem(s)",
    "ui.no_problems": "All clear",
    "ui.no_problems.detail": "Nothing failed. Nothing to warn about.",
    "ui.partial": "Stopped early: some checks did not run (time limit).",
    "ui.report_hint": "deckdoctor report     save a report you can paste on Discord",
    "ui.verbose_hint": "deckdoctor -v         show every check",
    "ui.fix_hint": "deckdoctor fix        {count} safe fix(es) ready (shows a plan, changes nothing yet)",
    "ui.fix_none": "deckdoctor fix        no safe automatic fix for these findings",
    "ui.readonly": "Looking around never changes anything. Fixes only run with --yes.",
    "ui.wrote": "Wrote {path}",
    "ui.internal_error": "deckdoctor: internal error: {exc}",
    "ui.summary": "{ok} ok  ·  {fail} fail  ·  {warn} warn  ·  {skip} skipped  ·  {unknown} unknown",
    "ui.tally.ok": "✅  {n} ok",
    "ui.tally.fail": "❌  {n}",
    "ui.tally.warn": "⚠️  {n}",
    "ui.tally.skip": "⏭️  {n}",
    "ui.tally.unknown": "❓  {n}",
    "ui.diag_count": "{count} diagnosis",
    "ui.next": "What you can do",
    "ui.severity.high": "serious",
    "ui.severity.medium": "watch",
    "ui.severity.low": "minor",
    "ui.severity.none": "",
    "ui.confidence.high": "high confidence",
    "ui.confidence.medium": "medium confidence",
    "ui.snapshot.internal": "Internal  {free} free of {total}",
    "ui.snapshot.sd": "microSD   {free} free of {total}",
    "ui.snapshot.sd.missing": "microSD   not inserted",
    "ui.snapshot.games.split": "{total} games  ·  {internal} internal  ·  {sd} microSD",
    "ui.snapshot.games.internal_only": "{total} games (internal)",
    "ui.snapshot.games.none": "No Steam games found",
    "fix.header": "Fix plan",
    "fix.empty": "Nothing safe to change automatically.",
    "fix.empty.detail": (
        "DeckDoctor only applies known, reversible mutations: executable bit on PluginLoader, "
        "CEF debug file, starting plugin_loader.service, and Flatpak updates. "
        "It will not reboot, kill processes, uninstall apps, or chmod 777."
    ),
    "fix.need_yes": "Nothing was changed. If the plan looks right, run it again with --yes.",
    "fix.applying": "Applying {count} fix(es)…",
    "fix.done_ok": "Done  {id}",
    "fix.done_fail": "Failed  {id}",
    "fix.unknown": "Unknown fix id {name}. Known: {known}",
    "fix.not_applicable": "Fix {name} is not applicable to the current diagnosis.",
    "fix.rediagnose": "Re-running diagnosis…",
    "fix.risk.low": "low risk",
    "fix.risk.medium": "medium risk",
    "fix.needs_root": "may need root",
    "fix.mutation": "Will run",
    "fix.undo": "Undo",
    "fix.pluginloader.title": "Make PluginLoader executable",
    "fix.pluginloader.summary": "PluginLoader exists but is not executable, so systemd cannot start Decky.",
    "fix.pluginloader.mutation": "chmod +x {path}",
    "fix.pluginloader.undo": "chmod -x {path}  (the official installer sets +x again)",
    "fix.cef.title": "Enable Steam CEF remote debugging",
    "fix.cef.summary": "Decky injects through the CEF debugger. The enable file is missing.",
    "fix.cef.mutation": "create empty file {path}",
    "fix.cef.undo": "delete {path}",
    "fix.decky.title": "Start plugin_loader.service",
    "fix.decky.summary": "PluginLoader looks valid but the systemd unit is not running.",
    "fix.decky.mutation": "systemctl enable --now plugin_loader.service",
    "fix.decky.undo": "systemctl stop plugin_loader.service",
    "fix.flatpak.title": "Apply Flatpak updates",
    "fix.flatpak.summary": "{count} Flatpak update(s) are available.",
    "fix.flatpak.mutation": "flatpak update -y",
    "fix.flatpak.undo": "not trivially reversible; apps roll forward. Discover can also update them.",
    "fix.exec.ok": "PluginLoader is now executable",
    "fix.exec.fail": "Could not set the executable bit on PluginLoader",
    "fix.cef.ok": "Created {path}",
    "fix.cef.fail": "Could not create {path}",
    "fix.decky.ok": "plugin_loader.service is active",
    "fix.decky.denied": "Permission denied starting the unit. Try: sudo systemctl enable --now plugin_loader.service",
    "fix.decky.fail": "systemctl could not start plugin_loader.service",
    "fix.flatpak.ok": "flatpak update finished",
    "fix.flatpak.fail": "flatpak update failed",
    "checks.header": "Checks",
    "checks.col.id": "ID",
    "checks.col.net": "Network",
    "checks.col.title": "Title",
    "checks.net.yes": "yes",
    "checks.net.no": "no",
    "report.title": "# DeckDoctor report",
    "report.tool_version": "- Tool version: `{version}`",
    "report.generated": "- Generated (UTC): `{when}`",
    "report.posture": "- Posture: diagnose is read-only; `deckdoctor fix --yes` is the only mutating command.",
    "report.sanitise": "- Sanitisation is **best-effort**. Review this file before posting.",
    "report.system": "## System",
    "report.summary": "## Check summary",
    "report.diagnoses": "## Diagnoses",
    "report.no_diagnoses": "_No correlated diagnoses._",
    "report.problems": "## Failed and warning checks",
    "report.none": "_None._",
    "report.network": "## Network checks performed",
    "report.network.body": (
        "DeckDoctor only contacts endpoints required by explicit checks: GitHub "
        "(github.com, api.github.com/rate_limit, optional releases/latest redirect), "
        "the Decky Plugin Store, Flatpak remotes already configured on the device, "
        "and SteamOS updater endpoints if those tools query them. Nothing is uploaded."
    ),
    "report.plugins": "## Plugins",
    "report.no_plugins": "_None detected._",
    "report.overlay": "## Overlay-edited SteamOS files",
    "report.cef": "## CEF / steamloopback.host excerpt",
    "report.no_cef": "_No CEF target list captured._",
    "report.eol": "## Flatpak end-of-life",
    "report.footer": "This report was generated by DeckDoctor. It does not restart services, apply updates, or modify permissions.",
    "diag.incomplete_rate.title": "Incomplete Decky install and GitHub rate limit",
    "diag.incomplete_rate.summary": (
        "FACT: PluginLoader is missing. FACT: GitHub API remaining is 0. "
        "LIKELY CAUSE: the installer could not download PluginLoader because the unauthenticated "
        "GitHub API quota was exhausted (common on CGNAT)."
    ),
    "diag.incomplete_rate.rec": (
        "Wait for the quota reset or switch networks, then reinstall with the official Decky installer. "
        "Do not delete ~/homebrew/plugins unless you intend to. DeckDoctor will not reinstall Decky."
    ),
    "diag.unit_429.title": "systemd unit replaced by GitHub 429 page",
    "diag.unit_429.summary": (
        "FACT: plugin_loader.service contains GitHub's rate-limit HTML. "
        "The installer saved an API error as a unit file, so Decky cannot start."
    ),
    "diag.unit_429.rec": (
        "Reinstall Decky after GitHub API quota recovers. "
        "Do not hand-edit a 429 page into a valid unit unless you know systemd."
    ),
    "diag.incomplete.title": "Incomplete Decky installation",
    "diag.incomplete.summary": "FACT: the homebrew tree exists but PluginLoader was never downloaded.",
    "diag.incomplete.rec": "Re-run the official installer. If it failed before, check NET-GITHUB first.",
    "diag.port.title": "Decky cannot inject: port 8080 conflict",
    "diag.port.summary": (
        "FACT: PluginLoader is present but port 8080 is not Steam's CEF debugger. "
        "Decky injects through localhost:8080; another process is in the way."
    ),
    "diag.port.rec": "Move the conflicting app (Syncthing should use 8384). DeckDoctor will not kill processes.",
    "diag.steam_beta.title": "Backend healthy; frontend may be a Steam client issue",
    "diag.steam_beta.summary": (
        "FACT: PluginLoader is present and plugin_loader.service is active. "
        "FACT: localhost:8080/json looks like Steam CEF. "
        "FACT: Steam client channel appears to be Beta. "
        "LIKELY CAUSE (medium): the Steam client/frontend, not a broken Decky install. "
        "DeckDoctor cannot see whether the QAM tab is actually missing."
    ),
    "diag.steam_beta.rec": (
        "Contrast with Steam Deck Stable, update Decky, and if React error #130 persists, "
        "disable plugins from Desktop Mode."
    ),
    "diag.autoflatpaks.title": "AutoFlatpaks is fine; Flatpak remote listing is not",
    "diag.autoflatpaks.summary": (
        "FACT: AutoFlatpaks is installed. FACT: `flatpak` works. "
        "FACT: `flatpak remote-ls` failed. "
        "The plugin cannot display a remote package list because Flatpak cannot produce one."
    ),
    "diag.autoflatpaks.rec": "Fix or remove the failing Flatpak remote yourself. DeckDoctor will not delete remotes.",
    "diag.autoflatpaks.rec.named": (
        "Fix or remove the '{remote}' Flatpak remote yourself. DeckDoctor will not delete remotes."
    ),
    "diag.overlay.title": "User-overlaid atomupd/rauc config and updater failure",
    "diag.overlay.summary": (
        "FACT: client.conf and/or rauc/system.conf exist under the SteamOS /etc overlay. "
        "FACT: the SteamOS updater could not complete a read-only check. "
        "LIKELY CAUSE (medium): those overlay copies are hiding the image configs the updater expects."
    ),
    "diag.overlay.rec": (
        "If you edited those files, restore the image copies rather than hand-tuning them. "
        "DeckDoctor will not delete overlay files."
    ),
}

_ES: dict[str, str] = {
    "cli.description": "Diagnóstico para SteamOS, Decky Loader, plugins y Flatpak. diagnose es solo lectura; fix es opt-in.",
    "cli.json": "Imprimir JSON legible por máquina",
    "cli.no_network": "Omitir comprobaciones que necesitan Internet",
    "cli.output": "Ruta del informe (comando report)",
    "cli.command": "diagnose (por defecto), report, fix o checks",
    "cli.target": "Id de arreglo (solo con el comando fix)",
    "cli.ascii": "Usar marcas ASCII (OK/X/!) en lugar de Unicode",
    "cli.only": "Ejecutar solo estos IDs de check (separados por comas)",
    "cli.timeout": "Límite global en segundos (0 lo desactiva). Por defecto: 60",
    "cli.lang": "Idioma de la interfaz: en o es (por defecto: LANG)",
    "cli.verbose": "Mostrar cada check, incluidos PASS y SKIPPED",
    "cli.no_color": "Desactivar colores ANSI",
    "cli.yes": "Aplicar el plan de arreglo (nunca por defecto)",
    "skip.no_network": "Omitido (--no-network)",
    "skip.no_network.explain": "Esta comprobación necesita red o una consulta remota.",
    "skip.only": "Omitido (--only)",
    "skip.only.explain": "No está en la lista --only.",
    "skip.timeout": "Omitido (tiempo global agotado)",
    "skip.timeout.explain": "DeckDoctor alcanzó el límite global; no se ejecutaron el resto de checks.",
    "group.system": "Sistema",
    "group.decky": "Decky Loader",
    "group.plugins": "Plugins",
    "group.flatpak": "Flatpak",
    "group.network": "Red",
    "ui.diagnosis": "Qué está pasando",
    "ui.fact": "Lo que vimos",
    "ui.likely": "Causa probable",
    "ui.recommended": "Recomendado: {text}",
    "ui.problems": "Problemas",
    "ui.problems_count": "{count} problema(s)",
    "ui.no_problems": "Todo en orden",
    "ui.no_problems.detail": "Nada falló. Nada de lo que avisar.",
    "ui.partial": "Se paró antes de tiempo: algunas comprobaciones no se ejecutaron.",
    "ui.report_hint": "deckdoctor report     guarda un informe para pegar en Discord",
    "ui.verbose_hint": "deckdoctor -v         ver todas las comprobaciones",
    "ui.fix_hint": "deckdoctor fix        {count} arreglo(s) seguro(s) (enseña el plan, no cambia nada aún)",
    "ui.fix_none": "deckdoctor fix        ningún arreglo automático seguro para esto",
    "ui.readonly": "Mirar no cambia nada. Los arreglos solo se aplican con --yes.",
    "ui.wrote": "Escrito {path}",
    "ui.internal_error": "deckdoctor: error interno: {exc}",
    "ui.summary": "{ok} ok  ·  {fail} fallos  ·  {warn} avisos  ·  {skip} omitidos  ·  {unknown} desconocidos",
    "ui.tally.ok": "✅  {n} bien",
    "ui.tally.fail": "❌  {n}",
    "ui.tally.warn": "⚠️  {n}",
    "ui.tally.skip": "⏭️  {n}",
    "ui.tally.unknown": "❓  {n}",
    "ui.diag_count": "{count} diagnóstico(s)",
    "ui.next": "Qué puedes hacer",
    "ui.severity.high": "grave",
    "ui.severity.medium": "aviso",
    "ui.severity.low": "leve",
    "ui.severity.none": "",
    "ui.confidence.high": "confianza alta",
    "ui.confidence.medium": "confianza media",
    "ui.snapshot.internal": "Interno   {free} libres de {total}",
    "ui.snapshot.sd": "microSD   {free} libres de {total}",
    "ui.snapshot.sd.missing": "microSD   no insertada",
    "ui.snapshot.games.split": "{total} juegos  ·  {internal} en interno  ·  {sd} en microSD",
    "ui.snapshot.games.internal_only": "{total} juegos (interno)",
    "ui.snapshot.games.none": "Ningún juego de Steam encontrado",
    "fix.header": "Plan de arreglo",
    "fix.empty": "Nada que cambiar de forma segura y automática.",
    "fix.empty.detail": (
        "DeckDoctor solo aplica mutaciones conocidas y reversibles: bit de ejecución de PluginLoader, "
        "archivo CEF, arrancar plugin_loader.service y actualizaciones Flatpak. "
        "No reinicia, no mata procesos, no desinstala ni hace chmod 777."
    ),
    "fix.need_yes": "No se ha cambiado nada. Si te encaja el plan, vuelve a ejecutarlo con --yes.",
    "fix.applying": "Aplicando {count} arreglo(s)…",
    "fix.done_ok": "Hecho  {id}",
    "fix.done_fail": "Falló  {id}",
    "fix.unknown": "Id de arreglo desconocido {name}. Conocidos: {known}",
    "fix.not_applicable": "El arreglo {name} no aplica a este diagnóstico.",
    "fix.rediagnose": "Volviendo a diagnosticar…",
    "fix.risk.low": "riesgo bajo",
    "fix.risk.medium": "riesgo medio",
    "fix.needs_root": "puede hacer falta root",
    "fix.mutation": "Ejecutará",
    "fix.undo": "Deshacer",
    "fix.pluginloader.title": "Hacer ejecutable PluginLoader",
    "fix.pluginloader.summary": "PluginLoader existe pero no es ejecutable, así que systemd no puede arrancar Decky.",
    "fix.pluginloader.mutation": "chmod +x {path}",
    "fix.pluginloader.undo": "chmod -x {path}  (el instalador oficial vuelve a poner +x)",
    "fix.cef.title": "Activar el depurador remoto CEF de Steam",
    "fix.cef.summary": "Decky inyecta a través del depurador CEF. Falta el archivo de activación.",
    "fix.cef.mutation": "crear archivo vacío {path}",
    "fix.cef.undo": "borrar {path}",
    "fix.decky.title": "Arrancar plugin_loader.service",
    "fix.decky.summary": "PluginLoader parece válido pero la unidad systemd no está en ejecución.",
    "fix.decky.mutation": "systemctl enable --now plugin_loader.service",
    "fix.decky.undo": "systemctl stop plugin_loader.service",
    "fix.flatpak.title": "Aplicar actualizaciones Flatpak",
    "fix.flatpak.summary": "Hay {count} actualización(es) Flatpak disponible(s).",
    "fix.flatpak.mutation": "flatpak update -y",
    "fix.flatpak.undo": "no es trivialmente reversible; las apps avanzan de versión. Discover también puede actualizarlas.",
    "fix.exec.ok": "PluginLoader ya es ejecutable",
    "fix.exec.fail": "No se pudo poner el bit de ejecución en PluginLoader",
    "fix.cef.ok": "Creado {path}",
    "fix.cef.fail": "No se pudo crear {path}",
    "fix.decky.ok": "plugin_loader.service está activo",
    "fix.decky.denied": "Permiso denegado al arrancar la unidad. Prueba: sudo systemctl enable --now plugin_loader.service",
    "fix.decky.fail": "systemctl no pudo arrancar plugin_loader.service",
    "fix.flatpak.ok": "flatpak update terminó",
    "fix.flatpak.fail": "flatpak update falló",
    "checks.header": "Checks",
    "checks.col.id": "ID",
    "checks.col.net": "Red",
    "checks.col.title": "Título",
    "checks.net.yes": "sí",
    "checks.net.no": "no",
    "report.title": "# Informe DeckDoctor",
    "report.tool_version": "- Versión de la herramienta: `{version}`",
    "report.generated": "- Generado (UTC): `{when}`",
    "report.posture": "- Postura: diagnose es solo lectura; `deckdoctor fix --yes` es el único comando que muta.",
    "report.sanitise": "- La sanitización es **de mejor esfuerzo**. Revisa este archivo antes de publicarlo.",
    "report.system": "## Sistema",
    "report.summary": "## Resumen de checks",
    "report.diagnoses": "## Diagnósticos",
    "report.no_diagnoses": "_Sin diagnósticos correlacionados._",
    "report.problems": "## Checks fallidos y advertencias",
    "report.none": "_Ninguno._",
    "report.network": "## Comprobaciones de red realizadas",
    "report.network.body": (
        "DeckDoctor solo contacta los endpoints que piden checks explícitos: GitHub "
        "(github.com, api.github.com/rate_limit, redirección opcional de releases/latest), "
        "la tienda de plugins de Decky, los remotos Flatpak ya configurados en el dispositivo "
        "y los endpoints del actualizador de SteamOS si esas herramientas los consultan. No se sube nada."
    ),
    "report.plugins": "## Plugins",
    "report.no_plugins": "_Ninguno detectado._",
    "report.overlay": "## Archivos de SteamOS editados en el overlay",
    "report.cef": "## Extracto CEF / steamloopback.host",
    "report.no_cef": "_No se capturó la lista de destinos CEF._",
    "report.eol": "## Flatpak en fin de vida",
    "report.footer": "Este informe lo generó DeckDoctor. No reinicia servicios, no aplica actualizaciones ni cambia permisos.",
    "diag.incomplete_rate.title": "Instalación incompleta de Decky y límite de GitHub",
    "diag.incomplete_rate.summary": (
        "HECHO: falta PluginLoader. HECHO: la cuota de la API de GitHub restante es 0. "
        "CAUSA PROBABLE: el instalador no pudo descargar PluginLoader porque se agotó la cuota "
        "no autenticada de GitHub (habitual en CGNAT)."
    ),
    "diag.incomplete_rate.rec": (
        "Espera a que se reinicie la cuota o cambia de red y reinstala con el instalador oficial de Decky. "
        "No borres ~/homebrew/plugins salvo que sea a propósito. DeckDoctor no reinstala Decky."
    ),
    "diag.unit_429.title": "La unidad systemd fue sustituida por una página 429 de GitHub",
    "diag.unit_429.summary": (
        "HECHO: plugin_loader.service contiene el HTML de límite de GitHub. "
        "El instalador guardó un error de API como archivo de unidad, así que Decky no puede arrancar."
    ),
    "diag.unit_429.rec": (
        "Reinstala Decky cuando se recupere la cuota de GitHub. "
        "No conviertas a mano una página 429 en una unidad válida salvo que sepas systemd."
    ),
    "diag.incomplete.title": "Instalación incompleta de Decky",
    "diag.incomplete.summary": "HECHO: existe el árbol homebrew pero PluginLoader nunca se descargó.",
    "diag.incomplete.rec": "Vuelve a ejecutar el instalador oficial. Si falló antes, mira primero NET-GITHUB.",
    "diag.port.title": "Decky no puede inyectarse: conflicto en el puerto 8080",
    "diag.port.summary": (
        "HECHO: PluginLoader está presente pero el puerto 8080 no es el depurador CEF de Steam. "
        "Decky inyecta a través de localhost:8080; otro proceso lo ocupa."
    ),
    "diag.port.rec": "Mueve la app en conflicto (Syncthing debería usar 8384). DeckDoctor no mata procesos.",
    "diag.steam_beta.title": "El backend está sano; el frontend puede ser un problema del cliente Steam",
    "diag.steam_beta.summary": (
        "HECHO: PluginLoader está presente y plugin_loader.service está activo. "
        "HECHO: localhost:8080/json parece CEF de Steam. "
        "HECHO: el canal del cliente Steam parece Beta. "
        "CAUSA PROBABLE (media): el cliente/frontend de Steam, no una instalación rota de Decky. "
        "DeckDoctor no puede ver si falta la pestaña del QAM."
    ),
    "diag.steam_beta.rec": (
        "Contrasta con Steam Deck Stable, actualiza Decky y, si persiste el error de React #130, "
        "desactiva plugins desde el modo escritorio."
    ),
    "diag.autoflatpaks.title": "AutoFlatpaks está bien; el listado remoto de Flatpak no",
    "diag.autoflatpaks.summary": (
        "HECHO: AutoFlatpaks está instalado. HECHO: `flatpak` funciona. "
        "HECHO: `flatpak remote-ls` falló. "
        "El plugin no puede mostrar el listado remoto porque Flatpak no puede generarlo."
    ),
    "diag.autoflatpaks.rec": "Repara o elimina tú el remoto Flatpak que falla. DeckDoctor no borra remotos.",
    "diag.autoflatpaks.rec.named": (
        "Repara o elimina tú el remoto Flatpak '{remote}'. DeckDoctor no borra remotos."
    ),
    "diag.overlay.title": "Config atomupd/rauc en overlay y fallo del actualizador",
    "diag.overlay.summary": (
        "HECHO: client.conf y/o rauc/system.conf existen en el overlay /etc de SteamOS. "
        "HECHO: el actualizador de SteamOS no pudo completar una consulta de solo lectura. "
        "CAUSA PROBABLE (media): esas copias del overlay ocultan las configs de la imagen que el actualizador espera."
    ),
    "diag.overlay.rec": (
        "Si editaste esos archivos, restaura las copias de la imagen en lugar de retocarlas a mano. "
        "DeckDoctor no borra archivos del overlay."
    ),
}

MESSAGES: dict[str, dict[str, str]] = {
    "en": {**_EN, **CHECK_EN},
    "es": {**_ES, **CHECK_ES},
}


def detect_locale(explicit: str | None = None) -> Locale:
    if explicit in {"en", "es"}:
        return explicit  # type: ignore[return-value]
    for key in ("DECKDOCTOR_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        raw = os.environ.get(key) or ""
        lowered = raw.lower().replace("-", "_")
        if lowered.startswith("es"):
            return "es"
        if lowered.startswith("en"):
            return "en"
    return "en"


def translate(locale: str, key: str, **kwargs: object) -> str:
    table = MESSAGES.get(locale) or MESSAGES["en"]
    tmpl = table.get(key) or MESSAGES["en"].get(key) or key
    if kwargs:
        return tmpl.format(**kwargs)
    return tmpl
