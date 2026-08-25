#!/usr/bin/env python3
"""Optional helper: python pack/build_pyinstaller.py"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    spec = root / "pack" / "deckdoctor.spec"
    return subprocess.call([sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec)], cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
