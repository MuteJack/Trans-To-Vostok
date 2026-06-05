"""Detect runtime-matching key collisions inside built runtime TSVs.

Reads the runtime TSV bundle produced by build_runtime_tsv.py and checks
each bucket for rows whose matching key is duplicated — same key with
different (or even same) translations causes runtime ambiguity, since
the in-game translator picks one occurrence non-deterministically.

Key shape per file (matches validate_translation.py #7 semantics):

  translation_static.tsv             (location, parent, name, type, text)
  translation_literal_scoped.tsv     (location, parent, name, type, text)
  translation_pattern_scoped.tsv     (location, parent, name, type, text)
  translation_literal.tsv            (text,)            -- global
  translation_pattern.tsv            (text,)            -- global
  translation_substr.tsv             (text,)            -- global

Severity: Critical for any duplicated key. Translations matching exactly
are still reported (the duplicate row itself is data-hygiene noise that
shouldn't reach the deployed bundle).

Input source:
  default     Trans To Vostok/<locale>/runtime_tsv/
  --dry-run   .tmp/temp_build/Trans To Vostok/<locale>/runtime_tsv/

Template handling:
  Same auto-routing as build_runtime_tsv.py — locale=Template auto-enables
  --dry-run with a Warn.

Usage:
  python tools/build/check_runtime_tsv_conflict.py Korean
  python tools/build/check_runtime_tsv_conflict.py Korean --dry-run
  python tools/build/check_runtime_tsv_conflict.py Template
  python tools/build/check_runtime_tsv_conflict.py all   # every enabled locale
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
TOOLS_DIR = SCRIPT_DIR.parent
REPO = TOOLS_DIR.parent
PKG_ROOT = REPO / "Trans To Vostok"
DRY_RUN_ROOT = REPO / ".tmp" / "temp_build" / "Trans To Vostok"
LOCALE_JSON = REPO / "src" / "locale.json"
TEMPLATE_LOCALE = "Template"

# (filename, key_columns) for every runtime TSV that participates in collision checking
RUNTIME_FILES: list[tuple[str, tuple[str, ...]]] = [
    ("translation_static.tsv",         ("location", "parent", "name", "type", "text")),
    ("translation_literal_scoped.tsv", ("location", "parent", "name", "type", "text")),
    ("translation_pattern_scoped.tsv", ("location", "parent", "name", "type", "text")),
    ("translation_literal.tsv",        ("text",)),
    ("translation_pattern.tsv",        ("text",)),
    ("translation_substr.tsv",         ("text",)),
]

SAMPLE_LIMIT = 5


class Issue(NamedTuple):
    locale: str
    runtime_file: str
    key: tuple
    occurrences: list[tuple[int, str]]   # [(row_num, translation), ...]


def _runtime_dir(locale: str, dry_run: bool) -> Path:
    root = DRY_RUN_ROOT if dry_run else PKG_ROOT
    return root / locale / "runtime_tsv"


def _preview(s: str, n: int = 30) -> str:
    p = (s or "").replace("\n", "\\n")
    return p[:n] + ("..." if len(p) > n else "")


def _format_key(key: tuple, columns: tuple[str, ...]) -> str:
    parts = []
    for col, val in zip(columns, key):
        parts.append(f"{col}={_preview(val, 25)!r}")
    return ", ".join(parts)


def check_runtime_file(path: Path, key_cols: tuple[str, ...]) -> list[tuple[tuple, list[tuple[int, str]]]]:
    """Return [(key, [(row_num, translation), ...]), ...] for every duplicate key."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    groups: dict[tuple, list[tuple[int, str]]] = defaultdict(list)
    for row_num, row in enumerate(rows, start=2):
        key = tuple((row.get(c) or "") for c in key_cols)
        translation = row.get("translation", "") or ""
        groups[key].append((row_num, translation))

    return [(k, occ) for k, occ in groups.items() if len(occ) >= 2]


def check_locale(locale: str, dry_run: bool) -> list[Issue]:
    issues: list[Issue] = []
    runtime_dir = _runtime_dir(locale, dry_run)
    if not runtime_dir.exists():
        print(f"  [SKIP] {runtime_dir.relative_to(REPO)} not found")
        return issues

    for filename, key_cols in RUNTIME_FILES:
        path = runtime_dir / filename
        if not path.exists():
            continue
        dups = check_runtime_file(path, key_cols)
        for key, occ in dups:
            issues.append(Issue(locale, filename, key, occ))
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
    by_file: dict[str, int] = defaultdict(int)
    for i in subset:
        by_file[i.runtime_file] += 1
    print(f"  CONFLICT: {len(subset)} duplicate-key group(s)")
    for fname, n in sorted(by_file.items()):
        print(f"    {fname:35s} {n}")
    # samples
    key_cols_by_file = {f: cols for f, cols in RUNTIME_FILES}
    for i in subset[:SAMPLE_LIMIT]:
        cols = key_cols_by_file.get(i.runtime_file, ())
        print(f"      [{i.runtime_file}]")
        print(f"        key: {_format_key(i.key, cols)}")
        for row_num, tx in i.occurrences:
            print(f"        r{row_num}: translation={_preview(tx, 40)!r}")
    if len(subset) > SAMPLE_LIMIT:
        print(f"      ... and {len(subset) - SAMPLE_LIMIT} more")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("locale", help="Locale name, 'Template', or 'all'")
    parser.add_argument("--dry-run", action="store_true",
                        help="Read from .tmp/temp_build/Trans To Vostok/ instead of the deploy path")
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file "
                             "(used by orchestrator)")
    args = parser.parse_args(argv[1:])
    setup_logpath(args.logpath, label=Path(__file__).stem)

    if args.locale == "all":
        locales = _discover_locales()
    else:
        locales = [args.locale]

    # Per-locale dry-run resolution: Template forces --dry-run on.
    all_issues: list[Issue] = []
    for locale in locales:
        dry_run = args.dry_run
        if locale == TEMPLATE_LOCALE and not dry_run:
            print(f"[WARN] {locale} auto-routes to --dry-run "
                  f"(Template is never deployed).")
            dry_run = True

        print()
        print(f"=== {locale} {'(dry-run)' if dry_run else ''} ===")
        local = check_locale(locale, dry_run)
        if not local:
            print("  OK")
            continue
        all_issues.extend(local)
        _summarize(all_issues, locale)

    print()
    print(f"=== Grand Total ===")
    print(f"  CONFLICT: {len(all_issues)}")
    return 1 if all_issues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
