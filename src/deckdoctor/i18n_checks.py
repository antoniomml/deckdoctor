"""User-facing strings for individual checks. Merged into i18n.MESSAGES."""

from __future__ import annotations

CHECK_EN: dict[str, str] = {
    "title.SYS-OS-VERSION": "OS version",
    "title.SYS-OS-CHANNEL": "SteamOS channel",
    "title.SYS-OS-UPDATER": "SteamOS updater",
    "title.SYS-OS-REBOOT": "SteamOS pending reboot",
    "title.SYS-OVERLAY": "SteamOS /etc overlay",
    "title.SYS-DISK": "Disk space",
    "title.SYS-TIME": "System time",
    "title.STEAM-CLIENT": "Steam client",
    "title.DECKY-INSTALL": "Decky installation",
    "title.DECKY-SERVICE": "Decky service",
    "title.DECKY-PORTS": "Decky ports",
    "title.DECKY-FRONTEND": "Decky frontend / CEF",
    "title.DECKY-LOGS": "Decky backend logs",
    "title.PLUGIN-INVENTORY": "Plugin inventory",
    "title.PLUGIN-REMOTE-BIN": "Plugin remote binaries",
    "title.PLUGIN-STORE-UPDATES": "Plugin Store updates",
    "title.AUTOFLATPAKS": "AutoFlatpaks",
    "title.FP-BASIC": "Flatpak basics",
    "title.FP-UPDATES": "Flatpak updates",
    "title.FP-EOL": "Flatpak end-of-life",
    "title.NET-GITHUB": "GitHub",
    "title.NET-STORE": "Decky Plugin Store",
    "skip.not_steamos": "Not SteamOS",
    "skip.not_steamos.explain": "This check uses SteamOS tools or paths.",
    "skip.decky_missing": "Decky is not installed",
    "skip.flatpak_missing": "flatpak is not available",
    "sys.os.unknown": "Could not read OS version metadata",
    "sys.os.unknown.explain": "Neither /etc/os-release nor an atomupd manifest was readable.",
    "sys.os.finding": "{name} {version} (build {build}, variant {variant})",
    "sys.os.not_steamos.explain": (
        "This looks like {distro}, not SteamOS. "
        "SteamOS updater, channel, overlay, and pending-reboot checks will be skipped. "
        "Decky, plugin, and Flatpak checks still run when those stacks are present."
    ),
    "sys.os.steamos.explain": "Version is taken from local OS metadata, not from the internet.",
    "sys.channel.timeout": "steamos-select-branch timed out",
    "sys.channel.ok": "Channel: {channel}",
    "sys.channel.ok.explain": "Reported by steamos-select-branch (local).",
    "sys.channel.parse": "Could not parse SteamOS channel",
    "sys.channel.missing": "steamos-select-branch not available",
    "sys.channel.missing.explain": "The SteamOS branch tool is not on PATH. Expected off SteamOS.",
    "sys.updater.timeout": "SteamOS updater timed out while checking for updates",
    "sys.updater.timeout.explain": (
        "The updater did not finish a read-only check in time. This is not the same as being up to date."
    ),
    "sys.updater.timeout.rec": (
        "Retry from Desktop Mode. If it keeps timing out, atomupd or the path to steamdeck-atomupd.steamos.cloud may be failing."
    ),
    "sys.updater.error": "SteamOS updater could not check for updates",
    "sys.updater.error.explain": "A local update query failed. DeckDoctor will not assume the system is current.",
    "sys.updater.error.rec": "Inspect atomupd/rauc journals. Do not treat this as up to date.",
    "sys.updater.available": "A SteamOS update appears to be available",
    "sys.updater.available.explain": "The local updater reported an update. DeckDoctor did not install it.",
    "sys.updater.available.rec": "Apply the update from SteamOS Settings when you are ready. Reboot if the updater asks.",
    "sys.updater.current": "SteamOS updater reports no update available",
    "sys.updater.current.explain": "Based on a local query-only check, not a web scrape.",
    "sys.updater.nonzero": "SteamOS updater returned an error",
    "sys.updater.nonzero.explain": "Non-zero exit while querying updates. This is not interpreted as up to date.",
    "sys.updater.missing": "No SteamOS updater tools found",
    "sys.updater.missing.explain": "atomupd-manager, steamos-update, and steamos-atomupd-client are all missing.",
    "sys.updater.unknown": "Could not determine SteamOS update state",
    "sys.updater.unknown.explain": "A query ran but the output was not a known up-to-date or update-available message.",
    "sys.reboot.none": "No pending SteamOS slot reboot marker",
    "sys.reboot.none.explain": (
        "Looked only for /run/steamos-atomupd/reboot_for_update, which RAUC writes after a successful image install."
    ),
    "sys.reboot.pending": "SteamOS update installed; reboot pending",
    "sys.reboot.pending.build": "SteamOS update {build} installed; reboot pending",
    "sys.reboot.pending.explain": (
        "The inactive A/B slot already has a new image. The running system is still the old slot until you reboot. "
        "DeckDoctor will not reboot."
    ),
    "sys.reboot.pending.rec": "Reboot from SteamOS Settings when you are ready. Do not delete the marker file.",
    "sys.overlay.missing": "No SteamOS /etc overlay tree to inspect",
    "sys.overlay.missing.explain": "Without the overlay mount there is nothing to inspect. Normal off-device.",
    "sys.overlay.clean": "atomupd/rauc configs are not user-overlaid",
    "sys.overlay.clean.explain": "Did not find client.conf or rauc/system.conf under the /etc overlay.",
    "sys.overlay.edited": "User-edited overlay copies of {names}",
    "sys.overlay.edited.explain": (
        "These files in /var/lib/overlays/etc/upper replace the image copies after boot. "
        "A stale client.conf or rauc/system.conf is a known way to break SteamOS updates."
    ),
    "sys.overlay.edited.rec": (
        "If the updater is failing, restore the image copies (remove those overlay files) rather than hand-editing them. "
        "DeckDoctor will not delete overlay files."
    ),
    "sys.disk.unknown": "Could not measure disk space",
    "sys.disk.critical": "Only {free} free on {path}",
    "sys.disk.critical.explain": (
        "Very little free space remains. Decky/plugin installs, Flatpak fetches, and SteamOS updates may fail."
    ),
    "sys.disk.critical.rec": "Free space on /home (games, Flatpak, Steam downloads) and re-run DeckDoctor.",
    "sys.disk.critical.small.explain": (
        "This small system partition is nearly full. Logs and temp files may fail. "
        "On SteamOS, Flatpak and games live on /home, not here."
    ),
    "sys.disk.critical.small.rec": "Clear logs or tmp on this partition if you can. Do not confuse it with /home.",
    "sys.disk.warn": "{free} free on {path}",
    "sys.disk.warn.explain": "Less than 2 GB free can make Flatpak and OS updates unreliable.",
    "sys.disk.warn.rec": "Free some space before large updates.",
    "sys.disk.warn.small.explain": "This small system partition is getting tight. Flatpak and games still live on /home.",
    "sys.disk.warn.small.rec": "Clear logs or tmp on this partition if installs start failing.",
    "sys.disk.ok": "{free} free (lowest mount: {path})",
    "sys.time.past": "System clock year is {year}",
    "sys.time.past.explain": "A clock this far in the past commonly breaks TLS and update checks.",
    "sys.time.past.rec": "Connect to the internet and wait for NTP, or set the time in Desktop Mode. Do not disable TLS verification.",
    "sys.time.no_timedatectl": "Clock year {year} looks sane (timedatectl not available)",
    "sys.time.unknown": "Could not read timedatectl",
    "sys.time.unsynced": "NTP is enabled but the clock is not synchronized",
    "sys.time.unsynced.explain": "Unsynchronized time can cause TLS and GitHub/SteamOS update failures.",
    "sys.time.unsynced.rec": "Wait for time sync or check network connectivity.",
    "sys.time.ok": "System time looks reasonable",
    "sys.time.ok.ntp": "System time looks reasonable (NTP synchronized)",
    "steam.missing": "Steam client metadata not found",
    "steam.missing.explain": "No ~/.steam/steam or ~/.local/share/Steam tree was readable.",
    "steam.finding": "{detail}",
    "steam.beta.explain": (
        "Steam client Beta is a correlation factor for Decky QAM issues, not proof that Beta is broken. "
        "DeckDoctor does not keep a build×Decky matrix."
    ),
    "steam.beta.rec": "If Decky vanished from the QAM after a client update, try Steam Deck Stable as a test, then update Decky.",
    "steam.ok.explain": "Parsed from local Steam files only.",
    "decky.install.absent": "Decky is not installed",
    "decky.install.absent.explain": "No homebrew directory at {home}.",
    "decky.install.absent.rec": "Install Decky with the official installer if you want it: https://github.com/SteamDeckHomebrew/decky-installer",
    "decky.install.unit429": "Decky systemd unit looks like a GitHub rate-limit error page",
    "decky.install.unit429.explain": (
        "plugin_loader.service contains GitHub HTML (429 Too Many Requests) instead of a unit file. "
        "The installer saved an API error as the service."
    ),
    "decky.install.unit429.rec": (
        "Do not reboot-loop the installer on the same network. Check GitHub rate limit with DeckDoctor, "
        "wait for reset or switch networks, then reinstall using the official installer."
    ),
    "decky.install.incomplete": "Decky installation appears incomplete: PluginLoader is missing",
    "decky.install.incomplete.explain": (
        "{home} exists but {loader} does not. This matches a failed installer run that still reported success, "
        "often after GitHub API rate limiting."
    ),
    "decky.install.incomplete.rec": (
        "If GitHub API remaining is 0, wait or change network. Reinstall with the official decky-installer. Do not chmod 777."
    ),
    "decky.install.not_exec": "PluginLoader exists but is not executable",
    "decky.install.not_exec.explain": "systemd cannot spawn a non-executable PluginLoader (Permission denied / EXEC spawn failure).",
    "decky.install.not_exec.rec": "`deckdoctor fix` can set the executable bit. Do not chmod 777 the tree.",
    "decky.install.ok": "Decky",
    "decky.install.newer": "{finding}; latest stable appears to be {latest}",
    "decky.install.newer.explain": "Compared local .loader.version to the GitHub releases/latest redirect (not the REST API).",
    "decky.install.newer.rec": "Update Decky from Desktop Mode with the official installer if the QAM updater is unavailable.",
    "decky.install.ok.explain": "Homebrew tree, PluginLoader binary, and version metadata look present.",
    "decky.service.no_systemctl": "systemctl is not available",
    "decky.service.missing_unit": "plugin_loader.service is not installed",
    "decky.service.missing_unit.explain": "Homebrew files may exist, but systemd has no plugin_loader unit.",
    "decky.service.missing_unit.rec": "Re-run the official Decky installer so it installs the systemd unit.",
    "decky.service.masked": "plugin_loader.service is masked",
    "decky.service.masked.explain": "A masked unit will not start. DeckDoctor will not unmask it.",
    "decky.service.masked.rec": "If you did not mask it on purpose, unmask via systemctl — or reinstall Decky.",
    "decky.service.failed": "plugin_loader.service failed (result={result}, status={status})",
    "decky.service.failed.explain": "The Decky backend service is not running. Often a missing PluginLoader, bad permissions, or a corrupt unit file.",
    "decky.service.failed.rec": "Read the backend logs. `deckdoctor fix` can start the unit only after the install looks valid. It will not restart blindly.",
    "decky.service.inactive": "plugin_loader.service is not running",
    "decky.service.inactive.explain": "The unit exists but is inactive. Decky cannot inject into Steam without this service.",
    "decky.service.inactive.rec": "`deckdoctor fix` can start it (may need root).",
    "decky.service.active": "Service active",
    "decky.service.restarts.explain": "The service is up but has restarted recently. That can indicate a crash loop.",
    "decky.service.ok.explain": "systemd reports plugin_loader.service as active. Diagnose did not restart anything.",
    "decky.service.unknown": "Unexpected service state: enabled={enabled} active={active}",
    "decky.ports.no_ss": "ss is not available; cannot inspect sockets",
    "decky.ports.timeout": "ss timed out",
    "decky.ports.conflict8080": "Port 8080 is in use by {owner}, expected steamwebhelper (Steam CEF debugger).",
    "decky.ports.conflict8080.explain": "A process other than Steam's CEF debugger owns port 8080, so Decky cannot inject.",
    "decky.ports.conflict8080.rec": "Change the other application's port (Syncthing should use 8384). Decky cannot move Steam's CEF port.",
    "decky.ports.conflict1337": "Port 1337 is in use by {owner}, expected PluginLoader.",
    "decky.ports.conflict1337.explain": "A named process other than PluginLoader owns Decky's port.",
    "decky.ports.conflict1337.rec": "Stop or reconfigure the process using 1337. DeckDoctor will not kill it.",
    "decky.ports.missing1337": "Decky service is active but port 1337 is not listening.",
    "decky.ports.missing1337.explain": "plugin_loader.service is up, but nothing is listening on 1337.",
    "decky.ports.unnamed": "listening (process name hidden)",
    "decky.ports.fail.rec": "Inspect listeners; do not kill processes from DeckDoctor.",
    "decky.ports.ok.explain": "8080 belongs to Steam CEF; 1337 belongs to Decky. No process was changed.",
    "decky.ports.cef_forward": "CEF debugger is forwarded on port 8081 beyond localhost",
    "decky.ports.cef_forward.explain": (
        "steam-web-debug-portforward (or equivalent) is listening on 8081 on every interface. "
        "Anyone on the same network can attach to Steam's CEF debugger."
    ),
    "decky.ports.cef_forward.rec": (
        "If you did not turn this on, disable cef_forward in Decky and stop steam-web-debug-portforward.service."
    ),
    "decky.front.no_cef": "CEF remote debugging is not enabled",
    "decky.front.no_cef.explain": (
        "Decky injects into Steam through the CEF debugger. "
        "The installer normally creates ~/.steam/steam/.cef-enable-remote-debugging."
    ),
    "decky.front.no_cef.rec": "`deckdoctor fix` can create that file. Do not expose CEF to the LAN unless you understand the risk.",
    "decky.front.not_cef": "Port 8080 answered but is not Steam's CEF debugger",
    "decky.front.not_cef.explain": (
        "Decky expected Chrome DevTools JSON at http://127.0.0.1:8080/json. "
        "A 404 usually means another program (often Syncthing) owns 8080."
    ),
    "decky.front.not_cef.rec": "Move the conflicting app off port 8080. Syncthing's recommended port is 8384.",
    "decky.front.conflict": "Steam CEF port 8080 is in conflict",
    "decky.front.conflict.explain": "A non-Steam process is listening on 8080, so Decky cannot inject into Game Mode.",
    "decky.front.conflict.rec": "Change the conflicting application's port. DeckDoctor will not kill it.",
    "decky.front.unreachable": "Could not reach Steam CEF debugger on localhost:8080",
    "decky.front.unreachable.explain": (
        "This is expected in Desktop Mode if Game Mode Steam is not running. "
        "If you are in Gaming Mode and Decky is missing from the QAM, CEF may be down or blocked."
    ),
    "decky.front.unreachable.rec": "Re-test from Gaming Mode. Confirm .cef-enable-remote-debugging still exists after Steam updates.",
    "decky.front.beta": "Backend looks healthy and CEF is Steam; Steam client is on Beta",
    "decky.front.beta.explain": (
        "FACT: PluginLoader is present, the service is active, and :8080/json looks like Steam CEF. "
        "LIKELY CAUSE (medium): a Steam client Beta/UI change can hide Decky from the QAM even when the backend is fine."
    ),
    "decky.front.beta.rec": "Try Steam Deck Stable as a contrast, update Decky, and disable plugins one by one if React errors persist.",
    "decky.front.ok": "CEF debugger looks like Steam",
    "decky.front.ok.explain": "localhost:8080/json returned DevTools targets. This does not prove the QAM tab is visible.",
    "decky.front.unknown": "CEF endpoint responded but was not recognized as Steam DevTools JSON",
    "decky.logs.no_journalctl": "journalctl is not available",
    "decky.logs.denied": "System journal for plugin_loader.service is not readable",
    "decky.logs.denied.explain": "DeckDoctor does not request sudo. Add the user to systemd-journal or re-run with privileges you already have.",
    "decky.logs.timeout": "journalctl timed out",
    "decky.logs.clean": "No recent backend ERROR/CRITICAL signatures in the current boot journal",
    "decky.logs.clean.explain": "Warnings alone are not treated as failures. Older boots are ignored (`-b0`).",
    "decky.logs.hits": "{count} relevant backend log line(s); signatures: {signatures}",
    "decky.logs.hits.explain": "Matched concrete signatures, not every warning. Timestamps are from this boot only.",
    "decky.logs.hits.rec": "See the report excerpt. A single old ERROR is weaker evidence than a traceback on this boot.",
    "plugin.inv.no_dir": "No plugins directory yet",
    "plugin.inv.zero": "0 plugins detected",
    "plugin.inv.zero.explain": "Only ~/homebrew/plugins was scanned.",
    "plugin.inv.ok": "{count} plugin(s) detected",
    "plugin.inv.ok.explain": "Inventory from plugin.json / package.json only. Load success is covered by logs.",
    "plugin.bin.missing": "{plugin}: missing remote binary {name}",
    "plugin.bin.log": "Decky logged: Failed Downloading Remote Binaries",
    "plugin.bin.fail.explain": (
        "Plugins can declare extra GitHub/HTTP assets in package.json remote_binary. "
        "A failed download leaves the plugin installed but non-functional. DeckDoctor did not download anything."
    ),
    "plugin.bin.fail.rec": "Fix network/GitHub access, then reinstall the affected plugin from the Decky store. Do not chmod 777.",
    "plugin.bin.ok_declared": "No missing remote binaries ({count} plugin(s) declare them)",
    "plugin.bin.ok_none": "No plugins declare remote binaries",
    "plugin.store.unreachable": "Plugin Store was unreachable",
    "plugin.store.no_plugins": "No installed plugins to compare",
    "plugin.store.empty": "Plugin Store catalog is empty; skipped update matching",
    "plugin.store.empty.explain": "Name matching is only attempted against a parsed store JSON array.",
    "plugin.store.updates": "{count} plugin(s) have a newer uniquely matched store version",
    "plugin.store.updates.explain": (
        "Matched only when the local plugin.json name or directory maps to exactly one store entry. "
        "Ambiguous names are ignored rather than guessed."
    ),
    "plugin.store.updates.rec": "Update from the Decky Plugin Store when you trust the listing. DeckDoctor will not install plugins.",
    "plugin.store.unmatched": "Installed plugins could not be uniquely matched to the Plugin Store",
    "plugin.store.unmatched.explain": "Refusing to guess updates when names do not uniquely match store entries.",
    "plugin.store.ok": "{matched} plugin(s) uniquely matched; none newer in the store",
    "plugin.store.ok.explain": "Compared dotted versions only. Unparseable versions were skipped.",
    "auto.missing": "AutoFlatpaks is not installed",
    "auto.missing.explain": "Optional plugin. No extra Flatpak package-list check was added.",
    "auto.no_flatpak": "AutoFlatpaks is installed but the Flatpak CLI is not working",
    "auto.no_network": "AutoFlatpaks is installed; remote listing skipped (--no-network)",
    "auto.no_network.explain": "Local plugin files were inspected. Flatpak remote-ls was not run.",
    "auto.timeout": "AutoFlatpaks cannot generate a remote package list (flatpak remote-ls timed out)",
    "auto.timeout.explain": "The plugin itself appears installed; Flatpak did not return a remote list in time.",
    "auto.timeout.rec": "Check network and remotes. DeckDoctor will not delete remotes.",
    "auto.remote_fail": "Cannot generate a remote package list",
    "auto.remote_fail.named": "Cannot list remotes because '{remote}' failed",
    "auto.remote_fail.explain": (
        "AutoFlatpaks is installed. Current versions call `flatpak remote-ls` to build the remote package list. "
        "Flatpak reported an error, so the plugin cannot show available packages."
    ),
    "auto.remote_fail.rec": (
        "Inspect `flatpak remotes`. If a remote you do not need is failing, you can remove it yourself. "
        "DeckDoctor will not delete them."
    ),
    "auto.remote_fail.named.rec": "Fix or remove '{remote}' yourself (expired GPG is common).",
    "auto.logs": "AutoFlatpaks logs look unhappy even though remote-ls succeeded now",
    "auto.logs.explain": "The plugin may have failed earlier. Current Flatpak listing works.",
    "auto.ok": "AutoFlatpaks installed; Flatpak remote listing succeeded",
    "auto.ok.explain": "This does not execute AutoFlatpaks' regex parser; it checks the same Flatpak operation the plugin needs.",
    "fp.basic.missing": "flatpak is not installed or not on PATH",
    "fp.basic.missing.explain": "AutoFlatpaks and Desktop software management need the Flatpak CLI.",
    "fp.basic.missing.info.explain": "Flatpak is not on this system. That is expected off SteamOS.",
    "fp.basic.version_fail": "flatpak --version failed",
    "fp.basic.version_fail.explain": (
        "The Flatpak CLI is on PATH but --version failed. "
        "A bundled DeckDoctor binary must not leak its libraries into system tools."
    ),
    "fp.basic.timeout": "flatpak remotes timed out",
    "fp.basic.list_fail": "Could not list Flatpak remotes",
    "fp.basic.list_fail.explain": "The CLI exists but listing remotes failed. Custom remotes are not treated as errors when listing succeeds.",
    "fp.basic.ok": "Flatpak working, {count} remote(s) configured",
    "fp.basic.ok.explain": "Custom remotes are allowed. Disabled or extra remotes are not automatically failures.",
    "fp.upd.timeout": "Flatpak update check timed out",
    "fp.upd.timeout.explain": "A failed or timed-out check is not the same as zero updates.",
    "fp.upd.fail": "Flatpak could not check for updates",
    "fp.upd.fail.remote": "Flatpak could not check for updates (remote {remote})",
    "fp.upd.fail.explain": "The remote query failed. DeckDoctor will not report this as 0 updates.",
    "fp.upd.fail.rec": "Inspect remotes (`flatpak remotes`) and stderr. Stale remotes are a common cause.",
    "fp.upd.fail.remote.rec": (
        "Fix or remove the '{remote}' remote (`flatpak remotes`). Expired GPG keys are a common cause. "
        "DeckDoctor will not delete remotes."
    ),
    "fp.upd.none": "No Flatpak updates reported",
    "fp.upd.none.explain": "remote-ls --updates succeeded with an empty list.",
    "fp.upd.some": "{count} update(s) available",
    "fp.upd.some.explain": "Listed only. Diagnose did not apply updates.",
    "fp.upd.some.rec": "`deckdoctor fix` can apply the updates.",
    "fp.upd.some_and_remote": "{count} update(s) available; remote '{remote}' failed",
    "fp.upd.some_and_remote.rec": "`deckdoctor fix` can apply the updates.",
    "fp.upd.partial.explain": (
        "A broken remote blocked the combined listing. Other remotes were checked one by one, "
        "so updates from healthy remotes are still listed. DeckDoctor will not delete remotes."
    ),
    "fp.eol.timeout": "flatpak list timed out while probing EOL metadata",
    "fp.eol.list_fail": "Could not list installed Flatpak runtimes",
    "fp.eol.list_fail.explain": "EOL is read from `flatpak info --show-metadata`.",
    "fp.eol.empty": "No installed Flatpak refs to inspect for EOL",
    "fp.eol.clean": "No EndOfLife marker on inspected Flatpak runtimes",
    "fp.eol.clean.explain": "Read the EndOfLife key from each runtime's metadata. Missing key means not marked EOL.",
    "fp.eol.some": "{count} Flatpak runtime(s) marked end-of-life{apps}",
    "fp.eol.apps": "; {count} app(s) use them",
    "fp.eol.some.explain": "Flatpak still runs EOL runtimes, but they no longer receive security updates. DeckDoctor did not uninstall anything.",
    "fp.eol.some.rec": "Update or replace the listed apps from Discover/Flathub when you can. DeckDoctor will not uninstall them.",
    "net.gh.down": "github.com is not reachable",
    "net.gh.down.explain": "Decky installs and many plugin remote binaries come from GitHub.",
    "net.gh.down.rec": "Check DNS and connectivity. DeckDoctor does not run speed tests.",
    "net.gh.api_fail": "GitHub is up but the rate-limit API could not be read",
    "net.gh.api_fail.explain": "GET /rate_limit does not consume the primary REST quota. This failure is separate from remaining=0.",
    "net.gh.parse": "Could not parse GitHub rate-limit JSON",
    "net.gh.ok": "GitHub reachable; API {remaining}/{limit} remaining{reset}",
    "net.gh.reset": "; reset in {minutes} min",
    "net.gh.exhausted": "GitHub API rate limit exhausted",
    "net.gh.exhausted.explain": (
        "Unauthenticated GitHub REST allows 60 requests per hour per IP (CGNAT shares that quota). "
        "The Decky GUI installer historically failed in this state and could skip downloading PluginLoader."
    ),
    "net.gh.exhausted.rec": "Wait for the reset time, switch to a different network (phone hotspot), then reinstall. DeckDoctor does not use your GitHub credentials.",
    "net.gh.low.explain": "Low remaining quota can still break the installer if it lists releases via the API.",
    "net.gh.low.rec": "Avoid re-running the installer until the quota resets if install already failed.",
    "net.gh.ok.explain": "Rate-limit lookup uses GET /rate_limit, which does not consume the primary quota.",
    "net.store.down": "Decky Plugin Store is unreachable",
    "net.store.down.explain": "Local Decky can still work while the store is down. Installing or updating plugins from the store will fail.",
    "net.store.down.rec": "Retry later. You can still sideload from a zip if you trust the source.",
    "net.store.not_json": "Plugin Store responded but the body is not JSON",
    "net.store.ok": "Plugin Store endpoint responded with JSON",
    "net.store.ok.explain": "This checks plugins.deckbrew.xyz/plugins only, not each plugin artifact CDN.",
}

CHECK_ES: dict[str, str] = {
    "title.SYS-OS-VERSION": "Versión del sistema",
    "title.SYS-OS-CHANNEL": "Canal de SteamOS",
    "title.SYS-OS-UPDATER": "Actualizador de SteamOS",
    "title.SYS-OS-REBOOT": "Reinicio pendiente de SteamOS",
    "title.SYS-OVERLAY": "Overlay /etc de SteamOS",
    "title.SYS-DISK": "Espacio en disco",
    "title.SYS-TIME": "Hora del sistema",
    "title.STEAM-CLIENT": "Cliente Steam",
    "title.DECKY-INSTALL": "Instalación de Decky",
    "title.DECKY-SERVICE": "Servicio de Decky",
    "title.DECKY-PORTS": "Puertos de Decky",
    "title.DECKY-FRONTEND": "Frontend / CEF de Decky",
    "title.DECKY-LOGS": "Logs del backend de Decky",
    "title.PLUGIN-INVENTORY": "Inventario de plugins",
    "title.PLUGIN-REMOTE-BIN": "Binarios remotos de plugins",
    "title.PLUGIN-STORE-UPDATES": "Actualizaciones de la tienda",
    "title.AUTOFLATPAKS": "AutoFlatpaks",
    "title.FP-BASIC": "Flatpak básico",
    "title.FP-UPDATES": "Actualizaciones Flatpak",
    "title.FP-EOL": "Flatpak en fin de vida",
    "title.NET-GITHUB": "GitHub",
    "title.NET-STORE": "Tienda de plugins de Decky",
    "skip.not_steamos": "No es SteamOS",
    "skip.not_steamos.explain": "Esta comprobación usa herramientas o rutas de SteamOS.",
    "skip.decky_missing": "Decky no está instalado",
    "skip.flatpak_missing": "flatpak no está disponible",
    "sys.os.unknown": "No se pudo leer la versión del sistema",
    "sys.os.unknown.explain": "No se pudo leer /etc/os-release ni un manifiesto atomupd.",
    "sys.os.finding": "{name} {version} (build {build}, variant {variant})",
    "sys.os.not_steamos.explain": (
        "Esto parece {distro}, no SteamOS. "
        "Se omiten actualizador, canal, overlay y reinicio pendiente. "
        "Decky, plugins y Flatpak siguen si están presentes."
    ),
    "sys.os.steamos.explain": "La versión sale de metadatos locales, no de internet.",
    "sys.channel.timeout": "steamos-select-branch agotó el tiempo",
    "sys.channel.ok": "Canal: {channel}",
    "sys.channel.ok.explain": "Lo reporta steamos-select-branch (local).",
    "sys.channel.parse": "No se pudo interpretar el canal de SteamOS",
    "sys.channel.missing": "steamos-select-branch no está disponible",
    "sys.channel.missing.explain": "La herramienta de canal de SteamOS no está en PATH. Normal fuera de SteamOS.",
    "sys.updater.timeout": "El actualizador de SteamOS agotó el tiempo al consultar",
    "sys.updater.timeout.explain": "La consulta de solo lectura no terminó a tiempo. No es lo mismo que estar al día.",
    "sys.updater.timeout.rec": (
        "Reintenta desde el modo escritorio. Si sigue fallando, atomupd o la ruta a steamdeck-atomupd.steamos.cloud pueden estar mal."
    ),
    "sys.updater.error": "El actualizador de SteamOS no pudo consultar actualizaciones",
    "sys.updater.error.explain": "Falló una consulta local. DeckDoctor no asume que el sistema esté al día.",
    "sys.updater.error.rec": "Mira los journals de atomupd/rauc. No lo trates como 'al día'.",
    "sys.updater.available": "Parece haber una actualización de SteamOS",
    "sys.updater.available.explain": "El actualizador local reportó una actualización. DeckDoctor no la instaló.",
    "sys.updater.available.rec": "Aplícala desde Ajustes de SteamOS cuando quieras. Reinicia si el actualizador lo pide.",
    "sys.updater.current": "El actualizador de SteamOS no reporta actualización",
    "sys.updater.current.explain": "Según una consulta local, no un scrape web.",
    "sys.updater.nonzero": "El actualizador de SteamOS devolvió un error",
    "sys.updater.nonzero.explain": "Salida distinta de cero al consultar. No se interpreta como 'al día'.",
    "sys.updater.missing": "No hay herramientas del actualizador de SteamOS",
    "sys.updater.missing.explain": "Faltan atomupd-manager, steamos-update y steamos-atomupd-client.",
    "sys.updater.unknown": "No se pudo determinar el estado de actualización de SteamOS",
    "sys.updater.unknown.explain": "Hubo consulta, pero la salida no era un mensaje conocido de 'al día' o 'hay actualización'.",
    "sys.reboot.none": "No hay marcador de reinicio pendiente de slot SteamOS",
    "sys.reboot.none.explain": "Solo se busca /run/steamos-atomupd/reboot_for_update, que RAUC escribe tras instalar una imagen.",
    "sys.reboot.pending": "Actualización de SteamOS instalada; falta reiniciar",
    "sys.reboot.pending.build": "Actualización de SteamOS {build} instalada; falta reiniciar",
    "sys.reboot.pending.explain": (
        "El slot A/B inactivo ya tiene una imagen nueva. El sistema en ejecución sigue siendo el slot viejo hasta que reinicies. "
        "DeckDoctor no reinicia."
    ),
    "sys.reboot.pending.rec": "Reinicia desde Ajustes de SteamOS cuando quieras. No borres el marcador.",
    "sys.overlay.missing": "No hay árbol de overlay /etc de SteamOS que inspeccionar",
    "sys.overlay.missing.explain": "Sin el montaje de overlay no hay nada que mirar. Normal fuera del Deck.",
    "sys.overlay.clean": "atomupd/rauc no están copiados en el overlay del usuario",
    "sys.overlay.clean.explain": "No aparecen client.conf ni rauc/system.conf bajo el overlay /etc.",
    "sys.overlay.edited": "Copias editadas en overlay de {names}",
    "sys.overlay.edited.explain": (
        "Esos archivos en /var/lib/overlays/etc/upper sustituyen las copias de la imagen al arrancar. "
        "Un client.conf o rauc/system.conf viejo es una forma conocida de romper actualizaciones."
    ),
    "sys.overlay.edited.rec": (
        "Si el actualizador falla, restaura las copias de la imagen (quita esos archivos del overlay) en lugar de retocarlos. "
        "DeckDoctor no borra el overlay."
    ),
    "sys.disk.unknown": "No se pudo medir el espacio en disco",
    "sys.disk.critical": "Solo {free} libres en {path}",
    "sys.disk.critical.explain": "Queda muy poco espacio. Pueden fallar instalaciones de Decky, Flatpak y actualizaciones de SteamOS.",
    "sys.disk.critical.rec": "Libera espacio en /home (juegos, Flatpak, descargas de Steam) y vuelve a ejecutar DeckDoctor.",
    "sys.disk.critical.small.explain": (
        "Esta partición de sistema tan pequeña está casi llena. Pueden fallar logs y temporales. "
        "En SteamOS, Flatpak y los juegos viven en /home, no aquí."
    ),
    "sys.disk.critical.small.rec": "Limpia logs o tmp de esta partición si puedes. No la confundas con /home.",
    "sys.disk.warn": "{free} libres en {path}",
    "sys.disk.warn.explain": "Menos de 2 GB libres puede hacer poco fiables Flatpak y las actualizaciones del SO.",
    "sys.disk.warn.rec": "Libera espacio antes de actualizaciones grandes.",
    "sys.disk.warn.small.explain": "Esta partición de sistema pequeña se está quedando justa. Flatpak y los juegos siguen en /home.",
    "sys.disk.warn.small.rec": "Limpia logs o tmp de esta partición si empiezan a fallar instalaciones.",
    "sys.disk.ok": "{free} libres (peor montaje: {path})",
    "sys.time.past": "El reloj del sistema está en el año {year}",
    "sys.time.past.explain": "Un reloj tan atrasado suele romper TLS y las consultas de actualización.",
    "sys.time.past.rec": "Conéctate a internet y espera NTP, o pon la hora en modo escritorio. No desactives la verificación TLS.",
    "sys.time.no_timedatectl": "El año {year} del reloj parece razonable (no hay timedatectl)",
    "sys.time.unknown": "No se pudo leer timedatectl",
    "sys.time.unsynced": "NTP está activo pero el reloj no está sincronizado",
    "sys.time.unsynced.explain": "La hora sin sincronizar puede romper TLS y actualizaciones de GitHub/SteamOS.",
    "sys.time.unsynced.rec": "Espera a la sincronización o revisa la red.",
    "sys.time.ok": "La hora del sistema parece razonable",
    "sys.time.ok.ntp": "La hora del sistema parece razonable (NTP sincronizado)",
    "steam.missing": "No hay metadatos del cliente Steam",
    "steam.missing.explain": "No se pudo leer ~/.steam/steam ni ~/.local/share/Steam.",
    "steam.finding": "{detail}",
    "steam.beta.explain": (
        "El canal Beta del cliente es un factor de correlación para problemas del QAM de Decky, no una prueba de que Beta esté roto."
    ),
    "steam.beta.rec": "Si Decky desapareció del QAM tras una actualización del cliente, prueba Steam Deck Stable y luego actualiza Decky.",
    "steam.ok.explain": "Solo se parsearon archivos locales de Steam.",
    "decky.install.absent": "Decky no está instalado",
    "decky.install.absent.explain": "No hay directorio homebrew en {home}.",
    "decky.install.absent.rec": "Instala Decky con el instalador oficial si lo quieres: https://github.com/SteamDeckHomebrew/decky-installer",
    "decky.install.unit429": "La unidad systemd de Decky parece una página de error 429 de GitHub",
    "decky.install.unit429.explain": (
        "plugin_loader.service contiene HTML de GitHub (429 Too Many Requests) en lugar de una unidad. "
        "El instalador guardó un error de API como servicio."
    ),
    "decky.install.unit429.rec": (
        "No relances el instalador en bucle en la misma red. Mira la cuota de GitHub con DeckDoctor, "
        "espera o cambia de red, y reinstala con el instalador oficial."
    ),
    "decky.install.incomplete": "Instalación de Decky incompleta: falta PluginLoader",
    "decky.install.incomplete.explain": (
        "Existe {home} pero no {loader}. Encaja con un instalador que dijo éxito y no descargó PluginLoader, "
        "a menudo por cuota de GitHub."
    ),
    "decky.install.incomplete.rec": (
        "Si la cuota de GitHub restante es 0, espera o cambia de red. Reinstala con decky-installer. No hagas chmod 777."
    ),
    "decky.install.not_exec": "PluginLoader existe pero no es ejecutable",
    "decky.install.not_exec.explain": "systemd no puede lanzar un PluginLoader sin bit de ejecución (Permission denied / EXEC).",
    "decky.install.not_exec.rec": "`deckdoctor fix` puede poner el bit de ejecución. No hagas chmod 777 al árbol.",
    "decky.install.ok": "Decky",
    "decky.install.newer": "{finding}; la última estable parece {latest}",
    "decky.install.newer.explain": "Se comparó .loader.version local con la redirección de GitHub releases/latest (no la API REST).",
    "decky.install.newer.rec": "Actualiza Decky desde el modo escritorio con el instalador oficial si el actualizador del QAM no está.",
    "decky.install.ok.explain": "El árbol homebrew, el binario PluginLoader y los metadatos de versión están presentes.",
    "decky.service.no_systemctl": "systemctl no está disponible",
    "decky.service.missing_unit": "plugin_loader.service no está instalado",
    "decky.service.missing_unit.explain": "Puede haber archivos homebrew, pero systemd no tiene la unidad plugin_loader.",
    "decky.service.missing_unit.rec": "Vuelve a ejecutar el instalador oficial de Decky para que instale la unidad systemd.",
    "decky.service.masked": "plugin_loader.service está enmascarado",
    "decky.service.masked.explain": "Una unidad enmascarada no arranca. DeckDoctor no la desenmascara.",
    "decky.service.masked.rec": "Si no la enmascaraste a propósito, desenmáscarala con systemctl — o reinstala Decky.",
    "decky.service.failed": "plugin_loader.service falló (result={result}, status={status})",
    "decky.service.failed.explain": "El backend de Decky no está corriendo. Suele ser PluginLoader ausente, permisos o una unidad corrupta.",
    "decky.service.failed.rec": "Lee los logs del backend. `deckdoctor fix` solo arranca la unidad si la instalación parece válida.",
    "decky.service.inactive": "plugin_loader.service no está en ejecución",
    "decky.service.inactive.explain": "La unidad existe pero está inactiva. Sin este servicio Decky no puede inyectarse en Steam.",
    "decky.service.inactive.rec": "`deckdoctor fix` puede arrancarlo (puede hacer falta root).",
    "decky.service.active": "Servicio activo",
    "decky.service.restarts.explain": "El servicio está arriba pero se ha reiniciado hace poco. Puede ser un bucle de crash.",
    "decky.service.ok.explain": "systemd reporta plugin_loader.service como activo. El diagnóstico no reinició nada.",
    "decky.service.unknown": "Estado inesperado: enabled={enabled} active={active}",
    "decky.ports.no_ss": "ss no está disponible; no se pueden inspeccionar sockets",
    "decky.ports.timeout": "ss agotó el tiempo",
    "decky.ports.conflict8080": "El puerto 8080 lo usa {owner}, se esperaba steamwebhelper (depurador CEF de Steam).",
    "decky.ports.conflict8080.explain": "Un proceso que no es el depurador CEF de Steam ocupa el puerto 8080, así que Decky no puede inyectarse.",
    "decky.ports.conflict8080.rec": "Cambia el puerto de la otra app (Syncthing debería usar 8384). Decky no puede mover el CEF de Steam.",
    "decky.ports.conflict1337": "El puerto 1337 lo usa {owner}, se esperaba PluginLoader.",
    "decky.ports.conflict1337.explain": "Un proceso con nombre distinto de PluginLoader ocupa el puerto de Decky.",
    "decky.ports.conflict1337.rec": "Para o reconfigura el proceso en 1337. DeckDoctor no lo mata.",
    "decky.ports.missing1337": "El servicio de Decky está activo pero el puerto 1337 no escucha.",
    "decky.ports.missing1337.explain": "plugin_loader.service está arriba, pero nada escucha en 1337.",
    "decky.ports.unnamed": "escucha (nombre de proceso oculto)",
    "decky.ports.fail.rec": "Inspecciona quién escucha; no mates procesos desde DeckDoctor.",
    "decky.ports.ok.explain": "8080 es CEF de Steam; 1337 es Decky. No se cambió ningún proceso.",
    "decky.ports.cef_forward": "El depurador CEF está reenviado en el puerto 8081 más allá de localhost",
    "decky.ports.cef_forward.explain": (
        "steam-web-debug-portforward (o equivalente) escucha en 8081 en todas las interfaces. "
        "Cualquiera en la misma red puede engancharse al depurador CEF de Steam."
    ),
    "decky.ports.cef_forward.rec": (
        "Si no lo activaste tú, desactiva cef_forward en Decky y para steam-web-debug-portforward.service."
    ),
    "decky.front.no_cef": "El depurador remoto CEF no está activado",
    "decky.front.no_cef.explain": (
        "Decky se inyecta en Steam por el depurador CEF. "
        "El instalador suele crear ~/.steam/steam/.cef-enable-remote-debugging."
    ),
    "decky.front.no_cef.rec": "`deckdoctor fix` puede crear ese archivo. No expongas CEF a la LAN si no sabes el riesgo.",
    "decky.front.not_cef": "El puerto 8080 respondió pero no es el depurador CEF de Steam",
    "decky.front.not_cef.explain": (
        "Decky espera JSON de Chrome DevTools en http://127.0.0.1:8080/json. "
        "Un 404 suele significar que otro programa (a menudo Syncthing) ocupa el 8080."
    ),
    "decky.front.not_cef.rec": "Quita la app en conflicto del puerto 8080. El puerto recomendado de Syncthing es 8384.",
    "decky.front.conflict": "Conflicto en el puerto CEF 8080 de Steam",
    "decky.front.conflict.explain": "Otro proceso no-Steam escucha en 8080, así que Decky no puede inyectarse en Game Mode.",
    "decky.front.conflict.rec": "Cambia el puerto de la app en conflicto. DeckDoctor no la mata.",
    "decky.front.unreachable": "No se alcanzó el depurador CEF de Steam en localhost:8080",
    "decky.front.unreachable.explain": (
        "Es normal en modo escritorio si Steam de Game Mode no está corriendo. "
        "Si estás en Gaming Mode y falta Decky en el QAM, CEF puede estar caído o bloqueado."
    ),
    "decky.front.unreachable.rec": "Prueba otra vez desde Gaming Mode. Confirma que .cef-enable-remote-debugging sigue existiendo tras actualizar Steam.",
    "decky.front.beta": "El backend está sano y CEF es Steam; el cliente Steam está en Beta",
    "decky.front.beta.explain": (
        "HECHO: PluginLoader está, el servicio está activo y :8080/json parece CEF de Steam. "
        "CAUSA PROBABLE (media): un cambio de UI/Beta de Steam puede ocultar Decky del QAM aunque el backend esté bien."
    ),
    "decky.front.beta.rec": "Contrasta con Steam Deck Stable, actualiza Decky y desactiva plugins uno a uno si persisten errores de React.",
    "decky.front.ok": "El depurador CEF parece Steam",
    "decky.front.ok.explain": "localhost:8080/json devolvió destinos DevTools. Eso no prueba que se vea la pestaña del QAM.",
    "decky.front.unknown": "El endpoint CEF respondió pero no se reconoció como JSON DevTools de Steam",
    "decky.logs.no_journalctl": "journalctl no está disponible",
    "decky.logs.denied": "El journal de sistema de plugin_loader.service no es legible",
    "decky.logs.denied.explain": "DeckDoctor no pide sudo. Añade el usuario a systemd-journal o ejecuta con privilegios que ya tengas.",
    "decky.logs.timeout": "journalctl agotó el tiempo",
    "decky.logs.clean": "Sin firmas ERROR/CRITICAL recientes en el journal de este arranque",
    "decky.logs.clean.explain": "Los avisos solos no se tratan como fallo. Se ignoran arranques anteriores (`-b0`).",
    "decky.logs.hits": "{count} línea(s) relevantes del backend; firmas: {signatures}",
    "decky.logs.hits.explain": "Se buscaron firmas concretas, no cada warning. Las marcas de tiempo son de este arranque.",
    "decky.logs.hits.rec": "Mira el extracto del informe. Un ERROR viejo pesa menos que un traceback de este arranque.",
    "plugin.inv.no_dir": "Aún no hay directorio de plugins",
    "plugin.inv.zero": "0 plugins detectados",
    "plugin.inv.zero.explain": "Solo se ha escaneado ~/homebrew/plugins.",
    "plugin.inv.ok": "{count} plugin(s) detectado(s)",
    "plugin.inv.ok.explain": "Inventario de plugin.json / package.json. Si cargan o no lo cubren los logs.",
    "plugin.bin.missing": "{plugin}: falta el binario remoto {name}",
    "plugin.bin.log": "Decky registró: Failed Downloading Remote Binaries",
    "plugin.bin.fail.explain": (
        "Los plugins pueden declarar assets extra de GitHub/HTTP en package.json remote_binary. "
        "Una descarga fallida deja el plugin instalado pero inútil. DeckDoctor no descargó nada."
    ),
    "plugin.bin.fail.rec": "Arregla red/GitHub y reinstala el plugin desde la tienda de Decky. No hagas chmod 777.",
    "plugin.bin.ok_declared": "No faltan binarios remotos ({count} plugin(s) los declaran)",
    "plugin.bin.ok_none": "Ningún plugin declara binarios remotos",
    "plugin.store.unreachable": "La tienda de plugins no era alcanzable",
    "plugin.store.no_plugins": "No hay plugins instalados que comparar",
    "plugin.store.empty": "El catálogo de la tienda está vacío; no se comparan versiones",
    "plugin.store.empty.explain": "El emparejado de nombres solo se intenta contra un JSON de tienda parseado.",
    "plugin.store.updates": "{count} plugin(s) tienen una versión más nueva emparejada de forma única",
    "plugin.store.updates.explain": (
        "Solo se empareja cuando el nombre o el directorio local apunta a exactamente una entrada de la tienda. "
        "Los nombres ambiguos se ignoran en vez de adivinar."
    ),
    "plugin.store.updates.rec": "Actualiza desde la tienda de Decky si te fías del listado. DeckDoctor no instala plugins.",
    "plugin.store.unmatched": "Los plugins instalados no se pudieron emparejar de forma única con la tienda",
    "plugin.store.unmatched.explain": "No se adivinan actualizaciones si los nombres no coinciden de forma única.",
    "plugin.store.ok": "{matched} plugin(s) emparejado(s) de forma única; ninguno más nuevo en la tienda",
    "plugin.store.ok.explain": "Solo se comparan versiones con puntos. Las no parseables se omiten.",
    "auto.missing": "AutoFlatpaks no está instalado",
    "auto.missing.explain": "Plugin opcional. No se añadió ninguna comprobación extra de listado Flatpak.",
    "auto.no_flatpak": "AutoFlatpaks está instalado pero el CLI de Flatpak no funciona",
    "auto.no_network": "AutoFlatpaks está instalado; listado remoto omitido (--no-network)",
    "auto.no_network.explain": "Se inspeccionaron archivos locales del plugin. No se ejecutó flatpak remote-ls.",
    "auto.timeout": "AutoFlatpaks no puede generar el listado remoto (flatpak remote-ls agotó el tiempo)",
    "auto.timeout.explain": "El plugin parece instalado; Flatpak no devolvió el listado a tiempo.",
    "auto.timeout.rec": "Revisa red y remotos. DeckDoctor no borra remotos.",
    "auto.remote_fail": "No puede generar el listado remoto de paquetes",
    "auto.remote_fail.named": "No puede listar remotos porque falló '{remote}'",
    "auto.remote_fail.explain": (
        "AutoFlatpaks está instalado. Las versiones actuales llaman a `flatpak remote-ls` para armar el listado. "
        "Flatpak devolvió un error, así que el plugin no puede mostrar paquetes disponibles."
    ),
    "auto.remote_fail.rec": (
        "Inspecciona `flatpak remotes`. Si un remoto que no necesitas falla, puedes quitarlo tú. "
        "DeckDoctor no los borra."
    ),
    "auto.remote_fail.named.rec": "Repara o elimina '{remote}' tú (una clave GPG caducada es habitual).",
    "auto.logs": "Los logs de AutoFlatpaks se ven mal aunque remote-ls ahora funciona",
    "auto.logs.explain": "El plugin pudo haber fallado antes. El listado Flatpak actual funciona.",
    "auto.ok": "AutoFlatpaks instalado; el listado remoto de Flatpak funcionó",
    "auto.ok.explain": "No se ejecuta el parser regex de AutoFlatpaks; se comprueba la misma operación Flatpak que necesita el plugin.",
    "fp.basic.missing": "flatpak no está instalado o no está en PATH",
    "fp.basic.missing.explain": "AutoFlatpaks y la gestión de software de escritorio necesitan el CLI de Flatpak.",
    "fp.basic.missing.info.explain": "Flatpak no está en este sistema. Es esperable fuera de SteamOS.",
    "fp.basic.version_fail": "flatpak --version falló",
    "fp.basic.version_fail.explain": (
        "El CLI de Flatpak está en PATH pero --version falló. "
        "El binario empaquetado de DeckDoctor no debe filtrar sus librerías a las herramientas del sistema."
    ),
    "fp.basic.timeout": "flatpak remotes agotó el tiempo",
    "fp.basic.list_fail": "No se pudieron listar los remotos Flatpak",
    "fp.basic.list_fail.explain": "El CLI existe pero listar remotos falló. Un remoto extra no es error si el listado funciona.",
    "fp.basic.ok": "Flatpak funciona, {count} remoto(s) configurado(s)",
    "fp.basic.ok.explain": "Los remotos personalizados están permitidos. Extra o deshabilitados no son fallos automáticos.",
    "fp.upd.timeout": "La comprobación de actualizaciones Flatpak agotó el tiempo",
    "fp.upd.timeout.explain": "Un check fallido o a timeout no es lo mismo que cero actualizaciones.",
    "fp.upd.fail": "Flatpak no pudo comprobar actualizaciones",
    "fp.upd.fail.remote": "Flatpak no pudo comprobar actualizaciones (remoto {remote})",
    "fp.upd.fail.explain": "La consulta remota falló. DeckDoctor no lo reportará como 0 actualizaciones.",
    "fp.upd.fail.rec": "Inspecciona remotos (`flatpak remotes`) y stderr. Los remotos obsoletos son una causa habitual.",
    "fp.upd.fail.remote.rec": (
        "Repara o elimina el remoto '{remote}' (`flatpak remotes`). Las claves GPG caducadas son una causa habitual. "
        "DeckDoctor no borra remotos."
    ),
    "fp.upd.none": "No hay actualizaciones Flatpak reportadas",
    "fp.upd.none.explain": "remote-ls --updates terminó bien con una lista vacía.",
    "fp.upd.some": "{count} actualización(es) disponible(s)",
    "fp.upd.some.explain": "Solo se listan. El diagnóstico no aplicó actualizaciones.",
    "fp.upd.some.rec": "`deckdoctor fix` puede aplicar las actualizaciones.",
    "fp.upd.some_and_remote": "{count} actualización(es) disponible(s); falló el remoto '{remote}'",
    "fp.upd.some_and_remote.rec": "`deckdoctor fix` puede aplicar las actualizaciones.",
    "fp.upd.partial.explain": (
        "Un remoto roto bloqueó el listado conjunto. Se consultaron los demás de uno en uno, "
        "así que las actualizaciones de remotos sanos sí aparecen. DeckDoctor no borra remotos."
    ),
    "fp.eol.timeout": "flatpak list agotó el tiempo al leer metadatos EOL",
    "fp.eol.list_fail": "No se pudieron listar los runtimes Flatpak instalados",
    "fp.eol.list_fail.explain": "El EOL se lee de `flatpak info --show-metadata`.",
    "fp.eol.empty": "No hay refs Flatpak instalados para inspeccionar EOL",
    "fp.eol.clean": "Ningún runtime Flatpak inspeccionado tiene marcador EndOfLife",
    "fp.eol.clean.explain": "Se lee la clave EndOfLife de cada runtime. Si no está, no está marcado EOL.",
    "fp.eol.some": "{count} runtime(s) Flatpak en fin de vida{apps}",
    "fp.eol.apps": "; {count} app(s) los usan",
    "fp.eol.some.explain": "Flatpak sigue ejecutando runtimes EOL, pero ya no reciben parches de seguridad. DeckDoctor no desinstaló nada.",
    "fp.eol.some.rec": "Actualiza o sustituye las apps listadas desde Discover/Flathub cuando puedas. DeckDoctor no las desinstala.",
    "net.gh.down": "github.com no es alcanzable",
    "net.gh.down.explain": "Las instalaciones de Decky y muchos binarios remotos de plugins vienen de GitHub.",
    "net.gh.down.rec": "Revisa DNS y conectividad. DeckDoctor no hace tests de velocidad.",
    "net.gh.api_fail": "GitHub responde pero no se pudo leer la API de cuota",
    "net.gh.api_fail.explain": "GET /rate_limit no consume la cuota REST principal. Este fallo es distinto de remaining=0.",
    "net.gh.parse": "No se pudo interpretar el JSON de cuota de GitHub",
    "net.gh.ok": "GitHub alcanzable; API {remaining}/{limit} restante{reset}",
    "net.gh.reset": "; reinicio en {minutes} min",
    "net.gh.exhausted": "Cuota de la API de GitHub agotada",
    "net.gh.exhausted.explain": (
        "La REST de GitHub sin autenticar permite 60 peticiones por hora y por IP (CGNAT comparte esa cuota). "
        "El instalador gráfico de Decky históricamente fallaba aquí y podía saltarse PluginLoader."
    ),
    "net.gh.exhausted.rec": "Espera al reinicio de cuota, cambia de red (hotspot del móvil) y reinstala. DeckDoctor no usa tus credenciales de GitHub.",
    "net.gh.low.explain": "Poca cuota restante aún puede romper el instalador si lista releases por la API.",
    "net.gh.low.rec": "No relances el instalador hasta que se reinicie la cuota si la instalación ya falló.",
    "net.gh.ok.explain": "La consulta de cuota usa GET /rate_limit, que no consume la cuota principal.",
    "net.store.down": "La tienda de plugins de Decky no es alcanzable",
    "net.store.down.explain": "Decky local puede seguir funcionando con la tienda caída. Instalar o actualizar plugins desde la tienda fallará.",
    "net.store.down.rec": "Reintenta más tarde. Puedes sideloadear un zip si te fías de la fuente.",
    "net.store.not_json": "La tienda respondió pero el cuerpo no es JSON",
    "net.store.ok": "El endpoint de la tienda de plugins respondió con JSON",
    "net.store.ok.explain": "Esto comprueba plugins.deckbrew.xyz/plugins, no el CDN de cada plugin.",
}
