from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

ID = "SYS-OS-VERSION"
TITLE = "SteamOS version"


def run(ctx: DiagnosticContext) -> CheckResult:
    osr = ctx.load_os_release()
    manifest = ctx.load_atomupd_manifest()
    name = osr.get("PRETTY_NAME") or osr.get("NAME") or "unknown"
    version = osr.get("VERSION_ID") or manifest.get("version") or "unknown"
    build = osr.get("BUILD_ID") or manifest.get("buildid") or "unknown"
    variant = osr.get("VARIANT_ID") or manifest.get("variant") or "unknown"
    distro_id = osr.get("ID", "")

    ctx.facts.os_version = str(version)
    ctx.facts.os_build = str(build)
    ctx.facts.os_variant = str(variant)
    ctx.facts.os_id = distro_id

    evidence: list[str] = []
    if ctx.exists(ctx.os_release_path):
        evidence.append(f"{ctx.os_release_path}: VERSION_ID={version} BUILD_ID={build} ID={distro_id}")
    if manifest:
        evidence.append(f"atomupd manifest: version={manifest.get('version')} buildid={manifest.get('buildid')}")

    if not osr and not manifest:
        return result(
            ID,
            TITLE,
            Status.UNKNOWN,
            "Could not read OS version metadata",
            explanation="Neither /etc/os-release nor an atomupd manifest was readable.",
            source=EvidenceSource.OS_METADATA,
            extra={"steamos": False},
        )

    is_steamos = distro_id == "steamos" or "SteamOS" in name
    ctx.facts.is_steamos = is_steamos
    finding = f"{name} {version} (build {build}, variant {variant})"
    if not is_steamos:
        return result(
            ID,
            TITLE,
            Status.INFO,
            finding,
            explanation="This does not look like SteamOS. SteamOS-specific updater checks will be skipped.",
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
            extra={"steamos": False},
        )
    return result(
        ID,
        TITLE,
        Status.PASS,
        finding,
        explanation="Version is taken from local OS metadata, not from the internet.",
        evidence=evidence,
        source=EvidenceSource.OS_METADATA,
        extra={"steamos": True, "version": version, "build": build},
    )
