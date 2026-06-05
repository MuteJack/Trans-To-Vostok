"""Phase 1 step 3 wrapper — convert Translation.xlsx + Texture.xlsx to canonical TSVs.

Calls the per-category exporters in tools/translation/ for each target:
    tools/translation/build_translation_tsv.py <locale>
    tools/translation/build_texture_tsv.py     <locale>

Each exporter reads Translations/<locale>/<Category>.xlsx and writes to
Translations/<locale>/tsv/<Category>/<sheet>.tsv. Locale-specific xlsx
missing for either category is handled per-exporter (prints [SKIP] and
returns 0).

Input convention (Phase 1):
    <locale>   single locale
    Template   Template's xlsx files
    all        every locale with enabled=true (English/Template excluded)

Usage:
    python tools/build_canonical_tsv.py Korean
    python tools/build_canonical_tsv.py Template
    python tools/build_canonical_tsv.py all
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
TRANSLATION_DIR = SCRIPT_DIR / "translation"

sys.path.insert(0, str(SCRIPT_DIR))
from helper.helper_locale_config import load_locales  # noqa: E402
from helper.helper_log import setup_logpath, make_log_path  # noqa: E402

SUB_TOOLS = [
    TRANSLATION_DIR / "build_translation_tsv.py",
    TRANSLATION_DIR / "build_texture_tsv.py",
]
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


def _run_one(locale: str, log_path: Path | None = None) -> list[str]:
    """Run every sub-tool for one locale. Returns list of failed sub-tool names."""
    failed: list[str] = []
    for tool in SUB_TOOLS:
        _say(f"=== {tool.name} {locale} ===")
        cmd = [sys.executable, str(tool), locale]
        if log_path is not None:
            cmd += ["--logpath", str(log_path)]
        rc = subprocess.run(cmd).returncode
        if rc != 0:
            failed.append(tool.name)
        _say()
    return failed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("locale", help="Locale name, 'Template', or 'all'")
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file. "
                             "If omitted, a fresh log is created at "
                             ".log/build_canonical_tsv_<timestamp>.log")
    args = parser.parse_args(argv[1:])

    log_path = Path(args.logpath) if args.logpath else make_log_path(REPO, "build_canonical_tsv")
    setup_logpath(str(log_path))
    _say(f"  log: {log_path.relative_to(REPO)}")
    _say()

    for tool in SUB_TOOLS:
        if not tool.exists():
            _say(f"[ERROR] sub-tool missing: {tool.relative_to(REPO)}")
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

    _say(f"=== build_canonical_tsv ({len(locales)} target(s)) ===")
    _say(f"  Targets: {', '.join(locales)}")
    _say()

    any_failed: list[tuple[str, list[str]]] = []
    for locale in locales:
        failed = _run_one(locale, log_path=log_path)
        if failed:
            any_failed.append((locale, failed))

    if any_failed:
        _say("[ERROR] failures:")
        for locale, fails in any_failed:
            _say(f"  {locale}: {', '.join(fails)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
