from __future__ import annotations

from deckdoctor.checks._util import result
from deckdoctor.context import DiagnosticContext
from deckdoctor.models import CheckResult, EvidenceSource, Status

KNOWN_DISTROS = {
    "steamos": "SteamOS",
    "bazzite": "Bazzite",
    "chimeraos": "ChimeraOS",
    "holoiso": "HoloISO",
    "nobara": "Nobara",
}

ID = "SYS-OS-VERSION"
TITLE = "OS version"


def run(ctx: DiagnosticContext) -> CheckResult:
    title = ctx.tr(f"title.{ID}")
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
        ctx.facts.is_steamos = False
        ctx.facts.os_family = "unknown"
        return result(
            ID,
            title,
            Status.UNKNOWN,
            ctx.tr("sys.os.unknown"),
            explanation=ctx.tr("sys.os.unknown.explain"),
            source=EvidenceSource.OS_METADATA,
            extra={"steamos": False},
        )

    is_steamos = distro_id == "steamos" or "SteamOS" in name
    family = distro_id if distro_id in KNOWN_DISTROS else "other"
    if is_steamos:
        family = "steamos"
    ctx.facts.is_steamos = is_steamos
    ctx.facts.os_family = family
    distro_label = KNOWN_DISTROS.get(family, name)
    finding = ctx.tr("sys.os.finding", name=name, version=version, build=build, variant=variant)
    if not is_steamos:
        return result(
            ID,
            title,
            Status.INFO,
            finding,
            explanation=ctx.tr("sys.os.not_steamos.explain", distro=distro_label),
            evidence=evidence,
            source=EvidenceSource.OS_METADATA,
            extra={"steamos": False, "os_family": family},
        )
    return result(
        ID,
        title,
        Status.PASS,
        finding,
        explanation=ctx.tr("sys.os.steamos.explain"),
        evidence=evidence,
        source=EvidenceSource.OS_METADATA,
        extra={"steamos": True, "version": version, "build": build, "os_family": "steamos"},
    )
