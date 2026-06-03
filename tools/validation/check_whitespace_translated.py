"""Find rows where translation's leading/trailing whitespace doesn't match the source.

This is the translator-side whitespace check: source text often carries
meaningful leading/trailing whitespace (e.g. a trailing newline that
controls label rendering or list spacing in-game), and the translation
must preserve it. A `text="Use\\n"` paired with `translation="사용"` (no
trailing newline) silently changes the layout.

Mirrors validate_translation.py's check #3, extracted as a standalone
tool consistent with the rest of `tools/validation/`. Internal whitespace
differences are NOT flagged — translators legitimately respace text.

Scope:
  Translation: every row with non-empty `text` and `translation`. Skip
               method=ignore and untranslatable=1 (not translation work).
  Texture:     every row with non-empty `Text` and `Translation`. Same
               filter logic (method=ignore/pending skipped).

Categories:
  LEADING_WS_MISMATCH   leading whitespace differs between source and translation
  TRAILING_WS_MISMATCH  trailing whitespace differs between source and translation

Usage:
  python tools/validation/check_whitespace_translated.py Korean
  python tools/validation/check_whitespace_translated.py all
  (passing 'Template' is a no-op — Template's translation column is empty)
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

SAMPLE_LIMIT = 10
BOOL_TRUE = {"1", "true"}

# Per-category column names for source vs translation
CATEGORY_FIELDS = {
    "Translation": {"source": "text", "translation": "translation"},
    "Texture":     {"source": "Text", "translation": "Translation"},
}


class Issue(NamedTuple):
    locale: str
    category: str
    kind: str        # LEADING_WS_MISMATCH / TRAILING_WS_MISMATCH
    sheet: str
    row: int
    detail: str


def _leading_ws(s: str) -> str:
    return s[: len(s) - len(s.lstrip())]


def _trailing_ws(s: str) -> str:
    return s[len(s.rstrip()):]


def _escape(s: str) -> str:
    return (s or "").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def _preview(s: str, n: int = 40) -> str:
    p = _escape(s)
    return p[:n] + ("..." if len(p) > n else "")


def _row_excluded(row: dict) -> bool:
    """Skip rows that aren't translation work."""
    method = (row.get("method") or "").strip().lower()
    if method in ("ignore", "pending"):
        return True
    if (row.get("untranslatable") or "").strip().lower() in BOOL_TRUE:
        return True
    return False


def check_locale(locale: str) -> list[Issue]:
    issues: list[Issue] = []
    for category, fields in CATEGORY_FIELDS.items():
        cat_dir = TRANSLATIONS / locale / "tsv" / category
        if not cat_dir.exists():
            continue
        src_col = fields["source"]
        tx_col = fields["translation"]
        for tsv in sorted(cat_dir.glob("*.tsv")):
            if tsv.name.startswith("_"):
                continue
            with open(tsv, encoding="utf-8", newline="") as f:
                for row_num, row in enumerate(csv.DictReader(f, delimiter="\t"), start=2):
                    if _row_excluded(row):
                        continue
                    src = row.get(src_col, "") or ""
                    tx = row.get(tx_col, "") or ""
                    if not src or not tx:
                        continue

                    src_lead = _leading_ws(src)
                    tx_lead = _leading_ws(tx)
                    if src_lead != tx_lead:
                        issues.append(Issue(
                            locale, category, "LEADING_WS_MISMATCH",
                            tsv.stem, row_num,
                            f"src={_escape(src_lead)!r}  tx={_escape(tx_lead)!r}  "
                            f"({_preview(src)} -> {_preview(tx)})",
                        ))

                    src_trail = _trailing_ws(src)
                    tx_trail = _trailing_ws(tx)
                    if src_trail != tx_trail:
                        issues.append(Issue(
                            locale, category, "TRAILING_WS_MISMATCH",
                            tsv.stem, row_num,
                            f"src={_escape(src_trail)!r}  tx={_escape(tx_trail)!r}  "
                            f"({_preview(src)} -> {_preview(tx)})",
                        ))
    return issues


def _discover_locales() -> list[str]:
    locales: list[str] = []
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
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for i in subset:
        counts[(i.category, i.kind)] += 1
    print(f"  total: {len(subset)}")
    for (cat, kind), n in sorted(counts.items()):
        print(f"    {cat:12s} {kind:22s} {n}")
    for i in subset[:SAMPLE_LIMIT]:
        print(f"      {i.category:11s} {i.kind:22s} {i.sheet}:r{i.row}  {i.detail}")
    if len(subset) > SAMPLE_LIMIT:
        print(f"      ... and {len(subset) - SAMPLE_LIMIT} more")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale",
        help="Locale name (e.g. Korean) or 'all' — Template is skipped (no translations)",
    )
    args = parser.parse_args(argv[1:])

    if args.locale == "all":
        locales = _discover_locales()
    elif args.locale == TEMPLATE_LOCALE:
        print("Template has no translations to check.")
        return 0
    else:
        if not (TRANSLATIONS / args.locale).exists():
            print(f"[ERROR] locale directory not found: {args.locale}")
            return 1
        locales = [args.locale]

    all_issues: list[Issue] = []
    for locale in locales:
        local = check_locale(locale)
        if not local:
            continue
        print()
        print(f"=== {locale} ===")
        all_issues.extend(local)
        _summarize(all_issues, locale)

    print()
    print(f"=== Grand Total ===")
    print(f"  whitespace mismatches: {len(all_issues)}")
    if all_issues:
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
