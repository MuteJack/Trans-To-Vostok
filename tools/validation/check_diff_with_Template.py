"""Compare a locale's canonical TSVs against Template and report drift.

This is the catalog-sync check: every locale should mirror Template's row
set and structural columns exactly, except for the per-locale columns
that legitimately differ (translation text, credits).

Reported categories:
  MISSING_IN_LOCALE   (Warn)      row in Template, absent from locale
  ORPHAN_IN_LOCALE    (Info)      row in locale, absent from Template
  STRUCTURAL_DRIFT    (Critical)  matched row pair with differing
                                  structural column value(s)
  MISSING_SHEET       (Warn)      TSV in Template missing from locale
  ORPHAN_SHEET        (Info)      TSV in locale missing from Template

Row matching across Template ↔ locale uses the most stable identity
available, in order:
  1. `identifier` column (numeric_id from the Crowdin migration)
  2. Translation: (filename, parent, name, type, property, unique_id)
  3. Translation global rows: (method, text)
  4. Texture: (File Directory, File Name)

Locale-specific columns are excluded from the structural comparison:
  Translation: translation
  Texture:     Translation, Reworked by, Contributors, Attribution

Whitespace drift on the `text` column is intentionally NOT special-cased
here — values are compared with `str.strip()` + exact match. Use
check_whitespace_text.py for whitespace-specific analysis.

Usage:
  python tools/validation/check_diff_with_Template.py Korean
  python tools/validation/check_diff_with_Template.py all   # every enabled locale

Template cannot be passed as the `locale` argument — this tool compares
Template against a locale, so Template-vs-Template makes no sense.
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

LOCALE_SPECIFIC: dict[str, set[str]] = {
    # `Comments` is treated as locale-specific for now — translators routinely
    # leave per-row notes that legitimately differ from Template. Tracking
    # genuine Template-side Comments drift requires a smarter check (see
    # memory/todo_comments_drift.md).
    "Translation": {"translation", "Comments"},
    "Texture":     {"Translation", "Reworked by", "Contributors", "Attribution", "Comments"},
}

CRITICAL = "Critical"
WARN = "Warn"
INFO = "Info"
SEVERITY_RANK = {CRITICAL: 0, WARN: 1, INFO: 2}
SAMPLE_LIMIT = 8


class Issue(NamedTuple):
    severity: str
    kind: str       # MISSING_IN_LOCALE / ORPHAN_IN_LOCALE / STRUCTURAL_DRIFT / MISSING_SHEET / ORPHAN_SHEET
    locale: str
    category: str
    sheet: str
    detail: str


def _match_key_translation(row: dict) -> tuple | None:
    cid = (row.get("identifier") or "").strip()
    if cid:
        return ("id", cid)
    parts = tuple((row.get(f) or "").strip()
                  for f in ("filename", "parent", "name", "type", "property", "unique_id"))
    if any(parts):
        return ("loc", parts)
    method = (row.get("method") or "").strip()
    text = (row.get("text") or "").strip()
    if text:
        return ("global", method, text)
    return None


def _match_key_texture(row: dict) -> tuple | None:
    cid = (row.get("identifier") or "").strip()
    if cid:
        return ("id", cid)
    fd = (row.get("File Directory") or "").strip()
    fn = (row.get("File Name") or "").strip()
    if fd or fn:
        return ("path", fd, fn)
    return None


MATCH_KEY_FN = {
    "Translation": _match_key_translation,
    "Texture":     _match_key_texture,
}


def _format_key(key: tuple) -> str:
    if key[0] == "id":
        return f"id={key[1]}"
    if key[0] == "loc":
        return f"loc=({':'.join(key[1])})"
    if key[0] == "global":
        text_preview = (key[2] or "").replace("\n", "\\n")[:30]
        return f"global method={key[1]} text={text_preview!r}"
    if key[0] == "path":
        fd, fn = key[1], key[2]
        return f"path={fd}\\{fn}" if fn else f"path={fd}"
    return repr(key)


def _load_sheet_rows(path: Path) -> list[tuple[int, dict]]:
    out: list[tuple[int, dict]] = []
    with open(path, encoding="utf-8", newline="") as f:
        for row_num, row in enumerate(csv.DictReader(f, delimiter="\t"), start=2):
            out.append((row_num, row))
    return out


def _build_index(rows: list[tuple[int, dict]], match_key_fn) -> dict[tuple, tuple[int, dict]]:
    out: dict[tuple, tuple[int, dict]] = {}
    for row_num, row in rows:
        key = match_key_fn(row)
        if key is None:
            continue
        out.setdefault(key, (row_num, row))  # leave duplicate detection to check_duplicates
    return out


def _structural_diff(tpl_row: dict, loc_row: dict, excluded: set[str]) -> dict[str, tuple[str, str]]:
    diffs: dict[str, tuple[str, str]] = {}
    cols = set(tpl_row.keys()) | set(loc_row.keys())
    for col in cols:
        if col in excluded:
            continue
        tpl_val = (tpl_row.get(col) or "").strip()
        loc_val = (loc_row.get(col) or "").strip()
        if tpl_val != loc_val:
            diffs[col] = (tpl_val, loc_val)
    return diffs


def check_locale(locale: str) -> list[Issue]:
    issues: list[Issue] = []
    for category in ("Translation", "Texture"):
        tpl_dir = TRANSLATIONS / TEMPLATE_LOCALE / "tsv" / category
        loc_dir = TRANSLATIONS / locale / "tsv" / category
        if not tpl_dir.exists() or not loc_dir.exists():
            continue

        tpl_sheets = {p.stem for p in tpl_dir.glob("*.tsv") if not p.name.startswith("_")}
        loc_sheets = {p.stem for p in loc_dir.glob("*.tsv") if not p.name.startswith("_")}

        for sheet in sorted(tpl_sheets - loc_sheets):
            issues.append(Issue(WARN, "MISSING_SHEET", locale, category, sheet, ""))
        for sheet in sorted(loc_sheets - tpl_sheets):
            issues.append(Issue(INFO, "ORPHAN_SHEET", locale, category, sheet, ""))

        excluded = LOCALE_SPECIFIC[category]
        match_fn = MATCH_KEY_FN[category]

        for sheet in sorted(tpl_sheets & loc_sheets):
            tpl_rows = _load_sheet_rows(tpl_dir / f"{sheet}.tsv")
            loc_rows = _load_sheet_rows(loc_dir / f"{sheet}.tsv")
            tpl_index = _build_index(tpl_rows, match_fn)
            loc_index = _build_index(loc_rows, match_fn)

            for key in tpl_index.keys() - loc_index.keys():
                tpl_row_num, _ = tpl_index[key]
                issues.append(Issue(
                    WARN, "MISSING_IN_LOCALE", locale, category,
                    f"{sheet} (tpl r{tpl_row_num})", _format_key(key),
                ))
            for key in loc_index.keys() - tpl_index.keys():
                loc_row_num, _ = loc_index[key]
                issues.append(Issue(
                    INFO, "ORPHAN_IN_LOCALE", locale, category,
                    f"{sheet}:r{loc_row_num}", _format_key(key),
                ))
            for key in tpl_index.keys() & loc_index.keys():
                tpl_row_num, tpl_row = tpl_index[key]
                loc_row_num, loc_row = loc_index[key]
                diffs = _structural_diff(tpl_row, loc_row, excluded)
                if diffs:
                    cols = ", ".join(sorted(diffs.keys()))
                    issues.append(Issue(
                        CRITICAL, "STRUCTURAL_DRIFT", locale, category,
                        f"{sheet} (tpl r{tpl_row_num} ↔ loc r{loc_row_num})",
                        f"{_format_key(key)} cols=[{cols}]",
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
        print("  OK")
        return
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for i in subset:
        counts[(i.kind, i.severity)] += 1
    for (kind, sev), n in sorted(counts.items(),
                                  key=lambda kv: (SEVERITY_RANK[kv[0][1]], kv[0][0])):
        print(f"  [{sev:8s}] {kind:20s} {n}")
    # Samples grouped by kind, prioritising Critical first
    by_kind: dict[str, list[Issue]] = defaultdict(list)
    for i in subset:
        by_kind[i.kind].append(i)
    shown_total = 0
    for kind in sorted(by_kind, key=lambda k: SEVERITY_RANK[by_kind[k][0].severity]):
        head = by_kind[kind][:SAMPLE_LIMIT]
        for i in head:
            print(f"      [{i.severity[:1]}] {i.kind:20s} {i.category:11s} {i.sheet:30s} {i.detail}")
            shown_total += 1
        extra = len(by_kind[kind]) - len(head)
        if extra > 0:
            print(f"          ... and {extra} more {kind}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale",
        help="Locale name (e.g. Korean) or 'all'",
    )
    args = parser.parse_args(argv[1:])

    if args.locale == TEMPLATE_LOCALE:
        print("[ERROR] Template is not a valid `locale` argument for this tool.")
        print("        check_diff_with_Template.py compares Template against a")
        print("        locale; pass a locale name (e.g. Korean) or 'all'.")
        return 1

    if args.locale == "all":
        locales = _discover_locales()
        if not locales:
            print("[ERROR] no enabled locales found in src/locale.json")
            return 1
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
        _summarize(local, locale)
        all_issues.extend(local)

    print()
    print(f"=== Grand Total ===")
    sev_counts: dict[str, int] = defaultdict(int)
    for i in all_issues:
        sev_counts[i.severity] += 1
    print(f"  Critical: {sev_counts[CRITICAL]}")
    print(f"  Warn    : {sev_counts[WARN]}")
    print(f"  Info    : {sev_counts[INFO]}")

    if sev_counts[CRITICAL]:
        return 1
    if sev_counts[WARN]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
