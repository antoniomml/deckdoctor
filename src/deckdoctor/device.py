"""Identify the handheld from DMI and CPU metadata. Read-only, no subprocesses."""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# (vendor substring, product/version regex, friendly model, family). Matched case-insensitively.
_MODELS: tuple[tuple[str, str, str, str], ...] = (
    ("valve", r"^jupiter$", "Steam Deck LCD", "steamdeck"),
    ("valve", r"^galileo$", "Steam Deck OLED", "steamdeck"),
    ("asus", r"rc71l", "ROG Ally", "rog-ally"),
    ("asus", r"rc72l", "ROG Ally X", "rog-ally"),
    ("asus", r"rc73x", "ROG Xbox Ally X", "rog-ally"),
    ("asus", r"rc73y", "ROG Xbox Ally", "rog-ally"),
    ("lenovo", r"legion go s|83l3|83n6|83q2|83q3", "Legion Go S", "legion-go"),
    ("lenovo", r"legion go 2", "Legion Go 2", "legion-go"),
    ("lenovo", r"legion go|83e1", "Legion Go", "legion-go"),
    ("micro-star", r"claw 8", "MSI Claw 8 AI+", "msi-claw"),
    ("micro-star", r"claw 7", "MSI Claw 7 AI+", "msi-claw"),
    ("micro-star", r"claw", "MSI Claw", "msi-claw"),
    ("gpd", r"g1618", "GPD Win 4", "gpd"),
    ("gpd", r"g1617", "GPD Win Mini", "gpd"),
    ("gpd", r"g1619", "GPD Win Max 2", "gpd"),
    ("zotac", r"zone", "Zotac Zone", "zotac"),
)
_PREFIXED_VENDORS = {"ayaneo": "AYANEO", "ayn": "AYN", "one-netbook": "OneXPlayer", "aokzoe": "AOKZOE", "gpd": "GPD"}
# SMBIOS chassis types 30-32 are tablet/convertible/detachable; most handhelds report one of them.
_HANDHELD_CHASSIS = {"30", "31", "32"}


@dataclass(frozen=True)
class Device:
    vendor: str
    product: str
    version: str
    board: str
    model: str
    family: str
    apu: str
    known_handheld: bool
    chassis_type: str

    @property
    def is_steam_deck(self) -> bool:
        return self.family == "steamdeck"

    @property
    def likely_handheld(self) -> bool:
        return self.known_handheld or self.chassis_type in _HANDHELD_CHASSIS

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["likely_handheld"] = self.likely_handheld
        return data


def _read(path: Path, limit: int = 4096) -> str:
    try:
        with path.open("rb") as stream:
            return stream.read(limit).decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _apu_name(proc_root: Path) -> str:
    text = _read(proc_root / "cpuinfo", limit=65536)
    for line in text.splitlines():
        if line.lower().startswith("model name"):
            name = line.partition(":")[2].strip()
            return re.sub(r"\s+", " ", name.replace("(R)", "").replace("(TM)", "")).strip()
    return ""


def classify(vendor: str, product: str, version: str = "", family_hint: str = "") -> tuple[str, str, bool]:
    """Return ``(model, family, known)`` for DMI strings."""
    v = vendor.lower()
    haystack = " ".join(part for part in (product, version, family_hint) if part).lower()
    for vendor_key, pattern, model, family in _MODELS:
        if vendor_key in v and re.search(pattern, product.lower() if pattern.startswith("^") else haystack):
            return model, family, True
    for vendor_key, label in _PREFIXED_VENDORS.items():
        if v.startswith(vendor_key):
            name = product or version
            return (f"{label} {name}".strip(), vendor_key, True)
    pretty = " ".join(part for part in (vendor, product) if part) or "Unknown device"
    return pretty, "generic", False


def identify(sys_root: Path = Path("/sys"), proc_root: Path = Path("/proc")) -> Device:
    dmi = sys_root / "class/dmi/id"
    vendor = _read(dmi / "sys_vendor")
    product = _read(dmi / "product_name")
    version = _read(dmi / "product_version")
    board = _read(dmi / "board_name")
    family_hint = _read(dmi / "product_family")
    chassis = _read(dmi / "chassis_type")
    model, family, known = classify(vendor, product, version, family_hint)
    return Device(
        vendor=vendor,
        product=product,
        version=version,
        board=board,
        model=model,
        family=family,
        apu=_apu_name(proc_root),
        known_handheld=known,
        chassis_type=chassis,
    )


def kernel_release() -> str:
    return os.uname().release if hasattr(os, "uname") else ""
