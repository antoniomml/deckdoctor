from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Severity, Status

ID = "SYS-OVERLAY"
TITLE = "SteamOS /etc overlay"

# Valve has traced updater breakage to user-edited copies of these files in the
# persistent overlay (SteamOS #1132, #1709). We only name those two; we do not
# dump the whole overlay tree.
WATCHED = (
    "steamos-atomupd/client.conf",
    "rauc/system.conf",
)


def run(ctx: DiagnosticContext) -> CheckResult:
    if ctx.facts.is_steamos is False:
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "Not SteamOS",
            explanation="The /var/lib/overlays/etc/upper tree is a SteamOS A/B overlay.",
            source=EvidenceSource.FILESYSTEM,
        )

    root = ctx.overlay_root
    evidence = [str(root)]
    if not ctx.exists(root):
        return result(
            ID,
            TITLE,
            Status.SKIPPED,
            "SteamOS /etc overlay directory not present",
            explanation="Without the overlay mount there is nothing to inspect. This is normal off-device.",
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
        )

    present: list[str] = []
    for rel in WATCHED:
        path = root / rel
        if ctx.exists(path):
            present.append(rel)
            evidence.append(f"present: {path}")
        else:
            evidence.append(f"absent: {path}")

    ctx.facts.overlay_edited = present
    if not present:
        return result(
            ID,
            TITLE,
            Status.PASS,
            "atomupd/rauc configs are not user-overlaid",
            explanation="Did not find client.conf or rauc/system.conf under the /etc overlay.",
            evidence=evidence,
            source=EvidenceSource.FILESYSTEM,
            extra={"edited": []},
        )

    names = ", ".join(present)
    return result(
        ID,
        TITLE,
        Status.WARNING,
        f"User-edited overlay copies of {names}",
        explanation=(
            "These files in /var/lib/overlays/etc/upper replace the image copies after boot. "
            "A stale client.conf or rauc/system.conf is a known way to break SteamOS updates. "
            "DeckDoctor did not open or modify them."
        ),
        recommendation=(
            "If the updater is failing, restore the image copies (remove those overlay files) "
            "rather than hand-editing them. DeckDoctor will not delete overlay files."
        ),
        evidence=evidence,
        source=EvidenceSource.FILESYSTEM,
        severity=Severity.MEDIUM,
        extra={"edited": present},
    )
