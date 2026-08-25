from __future__ import annotations

from collections.abc import Callable, Sequence

from deckdoctor.checks import (
    autoflatpaks,
    decky_frontend,
    decky_install,
    decky_logs,
    decky_ports,
    decky_service,
    fp_basic,
    fp_updates,
    net_github,
    net_store,
    plugin_inventory,
    plugin_remote_bin,
    steam_client,
    sys_disk,
    sys_os,
    sys_os_channel,
    sys_os_updater,
    sys_time,
)
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult

CheckFn = Callable[[DiagnosticContext], CheckResult]


# Order matters: later checks reuse ctx.facts populated earlier.
ALL_CHECKS: Sequence[CheckFn] = (
    sys_os.run,
    sys_os_channel.run,
    sys_os_updater.run,
    sys_disk.run,
    sys_time.run,
    steam_client.run,
    decky_install.run,
    decky_service.run,
    decky_ports.run,
    decky_logs.run,
    decky_frontend.run,
    plugin_inventory.run,
    plugin_remote_bin.run,
    fp_basic.run,
    fp_updates.run,
    autoflatpaks.run,
    net_github.run,
    net_store.run,
)

NETWORK_CHECK_IDS = {net_github.ID, net_store.ID}
