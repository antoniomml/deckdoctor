from __future__ import annotations

from deckdoctor.checks import (
    autoflatpaks,
    decky_frontend,
    decky_install,
    decky_logs,
    decky_ports,
    decky_service,
    fp_basic,
    fp_eol,
    fp_updates,
    net_github,
    net_store,
    plugin_inventory,
    plugin_remote_bin,
    plugin_store_updates,
    steam_client,
    sys_disk,
    sys_os,
    sys_os_channel,
    sys_os_reboot,
    sys_os_updater,
    sys_overlay,
    sys_time,
)
from deckdoctor.checks.protocol import Check, FnCheck

# Order matters: later checks reuse ctx.facts populated earlier.
ALL_CHECKS: tuple[FnCheck, ...] = (
    FnCheck(sys_os.ID, sys_os.TITLE, False, sys_os.run),
    FnCheck(sys_os_channel.ID, sys_os_channel.TITLE, False, sys_os_channel.run),
    FnCheck(sys_os_updater.ID, sys_os_updater.TITLE, False, sys_os_updater.run),
    FnCheck(sys_os_reboot.ID, sys_os_reboot.TITLE, False, sys_os_reboot.run),
    FnCheck(sys_overlay.ID, sys_overlay.TITLE, False, sys_overlay.run),
    FnCheck(sys_disk.ID, sys_disk.TITLE, False, sys_disk.run),
    FnCheck(sys_time.ID, sys_time.TITLE, False, sys_time.run),
    FnCheck(steam_client.ID, steam_client.TITLE, False, steam_client.run),
    FnCheck(decky_install.ID, decky_install.TITLE, False, decky_install.run),
    FnCheck(decky_service.ID, decky_service.TITLE, False, decky_service.run),
    FnCheck(decky_ports.ID, decky_ports.TITLE, False, decky_ports.run),
    FnCheck(decky_logs.ID, decky_logs.TITLE, False, decky_logs.run),
    FnCheck(decky_frontend.ID, decky_frontend.TITLE, False, decky_frontend.run),
    FnCheck(plugin_inventory.ID, plugin_inventory.TITLE, False, plugin_inventory.run),
    FnCheck(plugin_remote_bin.ID, plugin_remote_bin.TITLE, False, plugin_remote_bin.run),
    FnCheck(fp_basic.ID, fp_basic.TITLE, False, fp_basic.run),
    FnCheck(fp_updates.ID, fp_updates.TITLE, True, fp_updates.run),
    FnCheck(fp_eol.ID, fp_eol.TITLE, False, fp_eol.run),
    FnCheck(autoflatpaks.ID, autoflatpaks.TITLE, False, autoflatpaks.run),
    FnCheck(net_github.ID, net_github.TITLE, True, net_github.run),
    FnCheck(net_store.ID, net_store.TITLE, True, net_store.run),
    FnCheck(plugin_store_updates.ID, plugin_store_updates.TITLE, True, plugin_store_updates.run),
)

NETWORK_CHECK_IDS = {check.id for check in ALL_CHECKS if check.requires_network}

__all__ = ["ALL_CHECKS", "NETWORK_CHECK_IDS", "Check", "FnCheck"]
