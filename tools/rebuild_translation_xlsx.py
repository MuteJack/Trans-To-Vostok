"""Phase 1 step — rebuild Translation.xlsx for one or more locales from canonical TSVs.

Wraps tools/utils/rebuild_translation_xlsx.py for the workflow's input
convention (single locale / Template / all). For each target it runs the
util once; the util writes Translations/<locale>/Translation.xlsx,
overwriting the existing file.

Texture.xlsx is rebuilt separately by tools/rebuild_texture_xlsx.py
(both replace the older combined tools/rebuild_xlsx.py wrapper).

Input convention (Phase 1):
  <locale>   single locale
  Template   Template's Translation.xlsx (developer flow)
  all        every locale with enabled=true in src/locale.json
             (English/Template excluded)

Usage:
  python tools/rebuild_translation_xlsx.py Korean
  python tools/rebuild_translation_xlsx.py Template
  python tools/rebuild_translation_xlsx.py all
"""
import argparse
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


SCRIPT_DIR = Path(__file__).resolve().parent  # tools/
REPO = SCRIPT_DIR.parent
TRANSLATIONS_ROOT = REPO / "Translations"
IMPL = SCRIPT_DIR / "utils" / "rebuild_translation_xlsx.py"

sys.path.insert(0, str(SCRIPT_DIR))
from utils.locale_config import load_locales  # noqa: E402

TEMPLATE_LOCALE = "Template"
SOURCE_LOCALE = "English"


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _discover_enabled_locales() -> list[str]:
    out: list[str] = []
    for loc in load_locales():
        name = loc.get("dir")
        if loc.get("enabled") and name and name not in (SOURCE_LOCALE, TEMPLATE_LOCALE):
            out.append(name)
    return out


def _rebuild_one(locale: str) -> int:
    cmd = [sys.executable, str(IMPL), locale]
    return subprocess.run(cmd).returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("locale", help="Locale name, 'Template', or 'all'")
    args = parser.parse_args(argv[1:])

    if not IMPL.exists():
        _say(f"[ERROR] implementation missing: {IMPL.relative_to(REPO)}")
        return 1

    if args.locale == "all":
        locales = _discover_enabled_locales()
        if not locales:
            _say("[ERROR] no enabled locales found in src/locale.json")
            return 1
    else:
        if not (TRANSLATIONS_ROOT / args.locale).exists():
            _say(f"[ERROR] locale directory not found: Translations/{args.locale}")
            return 1
        locales = [args.locale]

    _say(f"=== rebuild_translation_xlsx ({len(locales)} target(s)) ===")
    _say(f"  Targets: {', '.join(locales)}")
    _say()

    failed: list[str] = []
    for locale in locales:
        _say(f"--- {locale} ---")
        rc = _rebuild_one(locale)
        if rc != 0:
            failed.append(locale)
        _say()

    if failed:
        _say(f"[ERROR] failed: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
