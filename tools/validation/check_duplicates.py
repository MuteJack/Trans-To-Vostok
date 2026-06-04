"""Duplicate-row check for canonical Translation / Texture TSVs.

Each category has a key field set that identifies a "logical row". When two
or more rows share the same key, this is reported as a data-hygiene issue —
the usual cause is copy-paste mistakes during xlsx editing or stale rows
left behind after a refactor.

This is NOT runtime-collision detection. Different `method` values use
different runtime matching rules (static vs scoped-literal vs global
literal/pattern/substr), so two rows with the same `text` but different
methods can coexist safely at runtime. A dedicated check_runtime_collisions
tool will cover that semantic separately.

Key fields per category:
  Translation: text, filename, filetype, location, parent, name, type,
               property, unique_id
  Texture:     File Directory, File Name

Filter (skip rows that cannot collide):
  - method=ignore
  - untranslatable=1 (Translation only)

`ignore` rows are placeholders today (often paired with a substr/literal
fallback that carries the actual runtime behavior), so flagging them as
"duplicates of substr" produces noise. A future `placeholder` method may
disambiguate this — see todo_placeholder_method.md.

Reports:
  ERROR  DUPLICATE_KEY  — two or more rows share the same key tuple

Exit codes:
  0  no duplicates
  1  one or more duplicate groups found

Usage:
  python tools/validation/check_dups.py Template
  python tools/validation/check_dups.py Korean
  python tools/validation/check_dups.py all      # Template + enabled locales
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
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

KEY_FIELDS: dict[str, list[str]] = {
    "Translation": [
        "text", "filename", "filetype", "location",
        "parent", "name", "type", "property", "unique_id",
    ],
    "Texture": [
        "File Directory", "File Name",
    ],
}

BOOL_TRUE = {"1", "true"}


class Issue(NamedTuple):
    severity: str    # "ERROR" / "WARN"
    kind: str        # e.g. "DUPLICATE_KEY"
    locale: str
    category: str
    key: tuple       # the shared key values
    occurrences: list[tuple[str, int]]  # [(sheet, row_num), ...]


def _row_skipped(row: dict, category: str) -> bool:
    """Rows excluded from dup detection — see module docstring."""
    method = (row.get("method") or "").strip().lower()
    if method == "ignore":
        return True
    if category == "Translation":
        if (row.get("untranslatable") or "").strip().lower() in BOOL_TRUE:
            return True
    return False


def _row_key(row: dict, category: str) -> tuple:
    return tuple((row.get(f) or "").strip() for f in KEY_FIELDS[category])


def check_locale(locale: str) -> list[Issue]:
    """Group rows by key per category, report groups with >= 2 entries."""
    issues: list[Issue] = []
    for category, fields in KEY_FIELDS.items():
        cat_dir = TRANSLATIONS / locale / "tsv" / category
        if not cat_dir.exists():
            continue
        # key -> [(sheet, row_num), ...]
        groups: dict[tuple, list[tuple[str, int]]] = defaultdict(list)
        for tsv in sorted(cat_dir.glob("*.tsv")):
            if tsv.name.startswith("_"):
                continue
            with open(tsv, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row_num, row in enumerate(reader, start=2):
                    if _row_skipped(row, category):
                        continue
                    key = _row_key(row, category)
                    # empty key (all fields blank) is meaningless — skip
                    if not any(key):
                        continue
                    groups[key].append((tsv.stem, row_num))
        for key, occ in groups.items():
            if len(occ) >= 2:
                issues.append(Issue(
                    "ERROR", "DUPLICATE_KEY", locale, category, key, occ,
                ))
    return issues


def _discover_locales() -> list[str]:
    """Template + enabled non-English locales (same set as sync_texture_schema)."""
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


def _format_key(category: str, key: tuple) -> str:
    fields = KEY_FIELDS[category]
    parts = []
    for f, v in zip(fields, key):
        if v:
            preview = v.replace("\n", " ⏎ ")
            if len(preview) > 40:
                preview = preview[:37] + "..."
            parts.append(f"{f}={preview!r}")
    return ", ".join(parts) if parts else "(empty key)"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale",
        help="Locale name (e.g. Korean), 'Template', or 'all'",
    )
    args = parser.parse_args(argv[1:])

    if args.locale == "all":
        locales = _discover_locales()
    else:
        if not (TRANSLATIONS / args.locale).exists():
            print(f"[ERROR] locale directory not found: {args.locale}")
            return 1
        locales = [args.locale]

    all_issues: list[Issue] = []
    for locale in locales:
        all_issues.extend(check_locale(locale))

    target = "all locales" if args.locale == "all" else args.locale
    if not all_issues:
        print(f"OK ({target}): no duplicate keys")
        return 0

    print(f"[ERROR] {target}: {len(all_issues)} duplicate group(s)")
    print()
    by_locale: dict[str, list[Issue]] = defaultdict(list)
    for iss in all_issues:
        by_locale[iss.locale].append(iss)

    for locale in sorted(by_locale):
        print(f"=== {locale} ({len(by_locale[locale])} group(s)) ===")
        for iss in by_locale[locale]:
            print(f"  [{iss.category}]  {_format_key(iss.category, iss.key)}")
            for sheet, row_num in iss.occurrences:
                print(f"    {sheet}:r{row_num}")
            print()

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
