from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "SYS-OS-REBOOT"
TITLE = "SteamOS pending reboot"

# Confirmed in steamos-customizations RAUC post-install (SteamOS 3.5+):
# /run/steamos-atomupd/reboot_for_update contains the inactive slot's BUILD_ID.
# Do not use Debian's /var/run/reboot-required — that is a different, noisier signal.


def run(ctx: DiagnosticContext) -> CheckResult:
    if ctx.facts.is_steamos is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Not SteamOS",
            explanation="Pending A/B slot reboot is a SteamOS atomupd/RAUC signal.",
            source=EvidenceSource.OS_METADATA,
        )

    path = ctx.reboot_for_update_path
    evidence = [str(path)]
    if not ctx.exists(path):
        ctx.facts.pending_reboot = False
        return result(
            ID,
            TITLE,
            Status.PASS,
            "No pending SteamOS slot reboot marker",
            explanation=(
                "Looked only for /run/steamos-atomupd/reboot_for_update, which RAUC writes "
                "after a successful image install. Absence of Debian's reboot-required is ignored."
            ),
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
            extra={"pending": False},
        )

    text = (ctx.read_text(path, max_bytes=256) or "").strip()
    ctx.facts.pending_reboot = True
    ctx.facts.pending_reboot_build = text or None
    finding = "SteamOS update installed; reboot pending"
    if text:
        finding = f"SteamOS update {text} installed; reboot pending"
        evidence.append(f"buildid={text}")
    return result(
        ID,
        TITLE,
        Status.WARNING,
        finding,
        explanation=(
            "The inactive A/B slot already has a new image. The running system is still the old slot "
            "until you reboot. DeckDoctor will not reboot."
        ),
        recommendation="Reboot from SteamOS Settings or `sudo reboot` when you are ready. Do not delete the marker file.",
        evidence=evidence,
        source=EvidenceSource.OS_METADATA,
        severity=Severity.MEDIUM,
        extra={"pending": True, "build": text},
    )
