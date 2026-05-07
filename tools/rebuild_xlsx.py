"""Rebuild all xlsx files for a locale from canonical TSVs.

Runs the three per-category utils sequentially:
    utils/rebuild_translation_xlsx.py <locale>
    utils/rebuild_glossary_xlsx.py    <locale>
    utils/rebuild_texture_xlsx.py     <locale>

Each util writes to <pkg_root>/<locale>/<category>.xlsx, overwriting the
existing file. If a category's TSV folder doesn't exist for the locale,
that util prints [SKIP] and returns 0 (not treated as failure).

Usage:
    python tools/rebuild_xlsx.py <locale>
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent  # tools

UTILS = [
    "rebuild_translation_xlsx.py",
    "rebuild_glossary_xlsx.py",
    "rebuild_texture_xlsx.py",
]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(f"Usage: python {Path(__file__).name} <locale>")
        return 1
    locale = argv[1]

    failed = []
    for util in UTILS:
        cmd = [sys.executable, str(SCRIPT_DIR / "utils" / util), locale]
        print(f"=== {util} {locale} ===")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            failed.append(util)
        print()

    if failed:
        print(f"[ERROR] Failed: {', '.join(failed)}")
        return 1
    print(f"[OK] All categories rebuilt for {locale}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
