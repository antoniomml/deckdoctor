# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a single-file Linux x86_64 CLI.

Build (from repo root, on Linux x86_64):

    pip install .[dev]
    pyinstaller pack/deckdoctor.spec
"""

from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("deckdoctor")

a = Analysis(
    ["../src/deckdoctor/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="deckdoctor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=True,
    disable_windowed_traceback=True,
)
