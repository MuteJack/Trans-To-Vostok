"""Validate `method` column values and method-dependent field combinations.

Each row's `method` chooses a runtime matching strategy; some strategies
require auxiliary fields (filetype, parent, name, unique_id, ...) and
others don't. This check verifies the value vocabulary and the field
combinations.

Translation `method` value vocabulary:
  "", static, literal, pattern, substr, ignore
  (empty defaults to literal for combination purposes; runtime falls
  back to literal too.)

Translation field requirements per method:
  static                        location, filetype∈{tscn,scn}, name, unique_id
  scoped literal (literal + location)   name
  scoped pattern (pattern + location)   name
  global literal / pattern / substr     no extra requirements
  ignore                                 no field requirements

Translation hints (Warn):
  empty method + unique_id filled → most likely intended as static.

Texture `method` value vocabulary:
  "", replace, blend, ignore, pending
  No field-combination rules — method shape is enforced elsewhere
  (validate_texture.py REPLACE_OR_BLEND_NO_TEXT etc.).

Severity:
  INVALID_METHOD                          Critical
  STATIC_NO_LOCATION / WRONG_FILETYPE /
  STATIC_NO_NAME / STATIC_NO_UNIQUE_ID    Critical
  SCOPED_LITERAL_NO_NAME                  Critical
  SCOPED_PATTERN_NO_NAME                  Critical
  EMPTY_METHOD_WITH_UNIQUE_ID             Warn

Usage:
  python tools/validation/check_method.py Template
  python tools/validation/check_method.py Korean
  python tools/validation/check_method.py all
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

TRANSLATION_METHODS = {"", "static", "literal", "pattern", "substr", "ignore"}
TEXTURE_METHODS = {"", "replace", "blend", "ignore", "pending"}
SCENE_FILETYPES = {"tscn", "scn"}

CRITICAL = "Critical"
WARN = "Warn"
SEVERITY_RANK = {CRITICAL: 0, WARN: 1}
SAMPLE_LIMIT = 8


class Issue(NamedTuple):
    severity: str
    kind: str
    locale: str
    category: str
    sheet: str
    row: int
    detail: str


def _check_translation_row(row: dict) -> list[tuple[str, str, str]]:
    """Return list of (severity, kind, detail) tuples for one row."""
    out: list[tuple[str, str, str]] = []
    method = (row.get("method") or "").strip()
    if method not in TRANSLATION_METHODS:
        out.append((CRITICAL, "INVALID_METHOD",
                    f"method={method!r} (allowed: {sorted(TRANSLATION_METHODS)})"))
        return out  # downstream rules don't apply to unknown methods

    effective = method if method else "literal"

    if effective == "ignore":
        return out

    location = (row.get("location") or "").strip()
    name = (row.get("name") or "").strip()
    unique_id = (row.get("unique_id") or "").strip()
    filetype = (row.get("filetype") or "").strip()

    if effective == "static":
        if not location:
            out.append((CRITICAL, "STATIC_NO_LOCATION", ""))
        if filetype not in SCENE_FILETYPES:
            out.append((CRITICAL, "STATIC_WRONG_FILETYPE",
                        f"filetype={filetype!r} (must be tscn or scn)"))
        if not name:
            out.append((CRITICAL, "STATIC_NO_NAME", ""))
        if not unique_id:
            out.append((CRITICAL, "STATIC_NO_UNIQUE_ID", ""))
    elif effective == "literal" and location:
        if not name:
            out.append((CRITICAL, "SCOPED_LITERAL_NO_NAME",
                        "literal + location requires name"))
    elif effective == "pattern" and location:
        if not name:
            out.append((CRITICAL, "SCOPED_PATTERN_NO_NAME",
                        "pattern + location requires name"))
    # global literal/pattern/substr: no extra requirements

    # Warn: empty method but unique_id filled
    if not method and unique_id:
        out.append((WARN, "EMPTY_METHOD_WITH_UNIQUE_ID",
                    f"unique_id={unique_id} — probably meant method=static"))

    return out


def _check_texture_row(row: dict) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    method = (row.get("method") or "").strip().lower()
    if method not in TEXTURE_METHODS:
        out.append((CRITICAL, "INVALID_METHOD",
                    f"method={method!r} (allowed: {sorted(TEXTURE_METHODS)})"))
    return out


CHECKERS = {
    "Translation": _check_translation_row,
    "Texture":     _check_texture_row,
}


def check_locale(locale: str) -> list[Issue]:
    issues: list[Issue] = []
    for category, checker in CHECKERS.items():
        cat_dir = TRANSLATIONS / locale / "tsv" / category
        if not cat_dir.exists():
            continue
        for tsv in sorted(cat_dir.glob("*.tsv")):
            if tsv.name.startswith("_"):
                continue
            with open(tsv, encoding="utf-8", newline="") as f:
                for row_num, row in enumerate(csv.DictReader(f, delimiter="\t"), start=2):
                    for severity, kind, detail in checker(row):
                        issues.append(Issue(severity, kind, locale, category,
                                            tsv.stem, row_num, detail))
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
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for i in subset:
        counts[(i.severity, i.kind, i.category)] += 1
    for (sev, kind, cat), n in sorted(counts.items(),
                                       key=lambda kv: (SEVERITY_RANK[kv[0][0]], kv[0][1])):
        print(f"  [{sev:8s}] {kind:30s} {cat:11s} {n}")
    # samples (Critical first)
    sorted_issues = sorted(subset, key=lambda i: (SEVERITY_RANK[i.severity],
                                                   i.kind, i.sheet, i.row))
    for i in sorted_issues[:SAMPLE_LIMIT]:
        sev_letter = i.severity[:1]
        loc = f"{i.sheet}:r{i.row}"
        det = f" — {i.detail}" if i.detail else ""
        print(f"      [{sev_letter}] {i.kind:30s} {i.category:11s} {loc:20s}{det}")
    if len(sorted_issues) > SAMPLE_LIMIT:
        print(f"      ... and {len(sorted_issues) - SAMPLE_LIMIT} more")


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
    sev_counts: dict[str, int] = defaultdict(int)
    for i in all_issues:
        sev_counts[i.severity] += 1
    print(f"  Critical: {sev_counts[CRITICAL]}")
    print(f"  Warn    : {sev_counts[WARN]}")

    if sev_counts[CRITICAL]:
        return 1
    if sev_counts[WARN]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
