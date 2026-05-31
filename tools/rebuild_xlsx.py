"""Rebuild all xlsx files for a locale from canonical TSVs.

Runs the per-category utils sequentially:
    utils/rebuild_translation_xlsx.py <locale>
    utils/rebuild_texture_xlsx.py     <locale>

Each util writes to Translations/<locale>/<category>.xlsx, overwriting the
existing file. If a category's TSV folder doesn't exist for the locale,
that util prints [SKIP] and returns 0 (not treated as failure).

Usage:
    python tools/rebuild_xlsx.py <locale>
    python tools/rebuild_xlsx.py all           # every directory under Translations/
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent  # tools
REPO_ROOT = SCRIPT_DIR.parent
TRANSLATIONS_ROOT = REPO_ROOT / "Translations"

UTILS = [
    "rebuild_translation_xlsx.py",
    "rebuild_texture_xlsx.py",
]


def _discover_locales() -> list[str]:
    """Every direct subdirectory of Translations/ is treated as a locale."""
    if not TRANSLATIONS_ROOT.exists():
        return []
    return sorted(p.name for p in TRANSLATIONS_ROOT.iterdir() if p.is_dir())


def _rebuild_one(locale: str) -> list[str]:
    """Run all UTILS for one locale. Returns list of failed util names."""
    failed: list[str] = []
    for util in UTILS:
        cmd = [sys.executable, str(SCRIPT_DIR / "utils" / util), locale]
        print(f"=== {util} {locale} ===")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            failed.append(util)
        print()
    return failed


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(f"Usage: python {Path(__file__).name} <locale|all>")
        return 1

    arg = argv[1]
    if arg.lower() == "all":
        locales = _discover_locales()
        if not locales:
            print(f"[ERROR] No locales found under {TRANSLATIONS_ROOT}")
            return 1
        print(f"Rebuilding xlsx for {len(locales)} locale(s): {', '.join(locales)}")
        print()
    else:
        locales = [arg]

    total_failed: dict[str, list[str]] = {}
    for locale in locales:
        failed = _rebuild_one(locale)
        if failed:
            total_failed[locale] = failed

    if total_failed:
        print("=" * 60)
        print("[ERROR] Some rebuilds failed:")
        for locale, utils in total_failed.items():
            print(f"  {locale}: {', '.join(utils)}")
        return 1

    if len(locales) == 1:
        print(f"[OK] All categories rebuilt for {locales[0]}")
    else:
        print(f"[OK] All categories rebuilt for {len(locales)} locale(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
