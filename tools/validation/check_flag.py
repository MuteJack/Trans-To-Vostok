"""Validate boolean-style flag column values in Translation TSVs.

Today the only flag column is `untranslatable`. Any value outside the
accepted vocabulary indicates a data-entry mistake — typos like "yes" or
"True" without the right normalization can silently change runtime
behavior, so this is treated as Critical.

Allowed values per column (compared after `strip().lower()`):
  untranslatable  ->  {"", "0", "1", "true", "false"}

Texture TSVs have no flag column today; this check is Translation-only.

Severity: Critical.

Usage:
  python tools/validation/check_flag.py Template
  python tools/validation/check_flag.py Korean
  python tools/validation/check_flag.py all   # Template + enabled locales
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helper.helper_log import setup_logpath  # noqa: E402

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

# column -> accepted values (case-insensitive, after strip)
ALLOWED_VALUES: dict[str, set[str]] = {
    "untranslatable": {"", "0", "1", "true", "false"},
}

SAMPLE_LIMIT = 10


class Issue(NamedTuple):
    locale: str
    sheet: str
    row: int
    column: str
    bad_value: str   # raw value as it appears in the TSV cell


def check_locale(locale: str) -> list[Issue]:
    issues: list[Issue] = []
    tr_dir = TRANSLATIONS / locale / "tsv" / "Translation"
    if not tr_dir.exists():
        return issues

    for tsv in sorted(tr_dir.glob("*.tsv")):
        if tsv.name.startswith("_"):
            continue
        with open(tsv, encoding="utf-8", newline="") as f:
            for row_num, row in enumerate(csv.DictReader(f, delimiter="\t"), start=2):
                for col, allowed in ALLOWED_VALUES.items():
                    if col not in row:
                        continue
                    val = (row[col] or "").strip().lower()
                    if val in allowed:
                        continue
                    issues.append(Issue(locale, tsv.stem, row_num, col, row[col] or ""))
    return issues


def _discover_locales() -> list[str]:
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


def _summarize(issues: list[Issue], locale: str) -> None:
    subset = [i for i in issues if i.locale == locale]
    if not subset:
        return
    counts: dict[str, int] = defaultdict(int)
    for i in subset:
        counts[i.column] += 1
    print(f"  INVALID_FLAG: {len(subset)}")
    for col, n in sorted(counts.items()):
        allowed = sorted(ALLOWED_VALUES[col], key=lambda v: (v != "", v))
        print(f"    {col:18s} {n:5d}   allowed: {allowed}")
    for i in subset[:SAMPLE_LIMIT]:
        print(f"      {i.sheet}:r{i.row}  {i.column}={i.bad_value!r}")
    if len(subset) > SAMPLE_LIMIT:
        print(f"      ... and {len(subset) - SAMPLE_LIMIT} more")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale",
        help="Locale name (e.g. Korean), 'Template', or 'all'",
    )
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file "
                             "(used by orchestrator)")
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
    for locale in locales:
        local = check_locale(locale)
        print()
        print(f"=== {locale} ===")
        if not local:
            print("  OK")
            continue
        all_issues.extend(local)
        _summarize(all_issues, locale)

    print()
    print(f"=== Grand Total ===")
    print(f"  INVALID_FLAG: {len(all_issues)}")
    return 1 if all_issues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
