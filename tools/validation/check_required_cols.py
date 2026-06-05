"""Required-columns check for canonical Translation / Texture TSVs.

For every TSV under Translations/<locale>/tsv/{Translation,Texture}/, verify
that the header contains the columns this codebase depends on. Each category
has its own required set; running this against Template catches schema drift
introduced by hand-editing xlsx, copy-pasting from older snapshots, or a
mid-migration build_translation_tsv that hasn't been re-run.

Required columns per category (everything else is treated as optional metadata):
  Translation: identifier, method, filename, filetype, location, parent,
               name, type, unique_id, text, translation, untranslatable
  Texture:     identifier, method, Text, Translation,
               File Directory, File Name, size, sha256

Reports:
  ERROR  MISSING_COLUMN  — one or more required column headers absent

Exit codes:
  0  every TSV has every required column
  1  at least one TSV is missing one or more required columns

Usage:
  python tools/validation/check_req_cols.py Template
  python tools/validation/check_req_cols.py Korean
  python tools/validation/check_req_cols.py all      # Template + enabled locales

`all` follows the same active-locale rule as sync_texture_schema.py: it
covers Template plus every locale with `enabled: true` in src/locale.json
(English is excluded). Disabled locales like Russian are intentionally
skipped — pass the locale name explicitly to check it.
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import NamedTuple

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent.parent
TRANSLATIONS = REPO / "Translations"
LOCALE_JSON = REPO / "src" / "locale.json"
TEMPLATE_LOCALE = "Template"

sys.path.insert(0, str(REPO / "tools"))
from helper.helper_log import setup_logpath  # noqa: E402

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "Translation": [
        "identifier",
        "method", "filename", "filetype", "location",
        "parent", "name", "type", "unique_id",
        "text", "translation", "untranslatable",
    ],
    "Texture": [
        "identifier",
        "method", "Text", "Translation",
        "File Directory", "File Name",
        "size", "sha256",
    ],
}


class Issue(NamedTuple):
    severity: str  # "ERROR" / "WARN"
    kind: str      # e.g. "MISSING_COLUMN"
    locale: str
    category: str  # "Translation" / "Texture"
    sheet: str     # TSV stem (filename without extension)
    detail: str    # human-readable detail (e.g. comma-joined missing columns)


def check_tsv(path: Path, locale: str, category: str) -> list[Issue]:
    """Verify a single canonical TSV has every required column for its category."""
    required = REQUIRED_COLUMNS[category]
    try:
        with open(path, encoding="utf-8", newline="") as f:
            header = next(csv.reader(f, delimiter="\t"), None)
    except OSError as e:
        return [Issue("ERROR", "READ_FAILED", locale, category, path.stem, str(e))]

    if not header:
        return [Issue("ERROR", "MISSING_COLUMN", locale, category, path.stem,
                      "empty file or missing header")]

    header_set = {h.strip() for h in header}
    missing = [c for c in required if c not in header_set]
    if not missing:
        return []
    return [Issue("ERROR", "MISSING_COLUMN", locale, category, path.stem,
                  ", ".join(missing))]


def check_locale(locale: str) -> list[Issue]:
    """Run the required-column check across every TSV in a locale."""
    issues: list[Issue] = []
    for category in REQUIRED_COLUMNS:
        cat_dir = TRANSLATIONS / locale / "tsv" / category
        if not cat_dir.exists():
            continue
        for tsv in sorted(cat_dir.glob("*.tsv")):
            if tsv.name.startswith("_"):
                continue
            issues.extend(check_tsv(tsv, locale, category))
    return issues


def _discover_locales() -> list[str]:
    """Locales to iterate for `all`: Template + enabled non-English locales
    (per src/locale.json). Mirrors the active set sync_texture_schema uses."""
    locales: list[str] = [TEMPLATE_LOCALE]
    if not LOCALE_JSON.exists():
        return locales
    try:
        data = json.loads(LOCALE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return locales
    for loc in data.get("locales", []):
        name = loc.get("dir")
        if loc.get("enabled") and name and name not in ("English", TEMPLATE_LOCALE):
            locales.append(name)
    return locales


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale",
        help="Locale name (e.g. Korean, French), 'Template', or 'all'",
    )
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file (used by orchestrator)")
    args = parser.parse_args(argv[1:])
    setup_logpath(args.logpath)

    if args.locale == "all":
        locales = _discover_locales()
    else:
        if not (TRANSLATIONS / args.locale).exists():
            print(f"[ERROR] locale directory not found: {args.locale}")
            return 1
        locales = [args.locale]

    all_issues: list[Issue] = []
    sheets_checked = 0
    for locale in locales:
        for category in REQUIRED_COLUMNS:
            cat_dir = TRANSLATIONS / locale / "tsv" / category
            if cat_dir.exists():
                sheets_checked += sum(
                    1 for t in cat_dir.glob("*.tsv") if not t.name.startswith("_")
                )
        all_issues.extend(check_locale(locale))

    target = "all locales" if args.locale == "all" else args.locale
    if not all_issues:
        print(f"OK ({target}): all required columns present in {sheets_checked} sheet(s)")
        return 0

    print(f"[ERROR] {target}: {len(all_issues)} sheet(s) missing required columns")
    print()
    for issue in all_issues:
        print(f"  {issue.locale}/{issue.category}/{issue.sheet}.tsv")
        print(f"    missing: {issue.detail}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
