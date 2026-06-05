"""Find rows where the same source text has been translated differently.

Per-locale consistency check on Translation TSVs: group rows by their
whitespace-normalized `text`, then within each group flag the cases
where two or more distinct (whitespace-normalized) translations exist.
The output is a hint for a human reviewer — homonyms legitimately
diverge in translation depending on context, so this is an Info-level
signal, not an error.

Filter:
  - method=ignore     (not translation work)
  - untranslatable=1  (not translation work)
  - empty text        (nothing to translate)
  - empty translation (consistency can't be judged yet)
  - groups of size 1  (no peers to disagree with)

Normalization:
  text         — `" ".join(s.split())` (collapse whitespace, strip ends).
                  Two rows whose text differs only in whitespace land in
                  the same group.
  translation  — same normalization applied for distinctness comparison,
                  so a whitespace-only translation variation does NOT
                  count as a conflict.

Texture rows are NOT checked: a given depicted text rarely repeats across
distinct PNGs in this project, and the catalog enforces uniqueness via
(File Directory, File Name).

Usage:
  python tools/validation/check_conflict.py Korean
  python tools/validation/check_conflict.py all      # every enabled locale
  python tools/validation/check_conflict.py Template # no-op (no translations)
"""
import argparse
import csv

import sys as _sys_helper_log  # noqa: E402
_sys_helper_log.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helper.helper_log import setup_logpath  # noqa: E402
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

BOOL_TRUE = {"1", "true"}
SAMPLE_LIMIT = 5


class Entry(NamedTuple):
    sheet: str
    row: int
    text: str           # raw text
    translation: str    # raw translation
    method: str
    location: str
    filename: str
    parent: str
    name: str
    property: str


class Conflict(NamedTuple):
    locale: str
    text_key: str             # normalized source text
    distinct_translations: int
    entries: list[Entry]


def _normalize_ws(s: str) -> str:
    return " ".join((s or "").split())


def _preview(s: str, n: int = 40) -> str:
    p = (s or "").replace("\n", "\\n")
    return p[:n] + ("..." if len(p) > n else "")


def _row_excluded(row: dict) -> bool:
    method = (row.get("method") or "").strip().lower()
    if method == "ignore":
        return True
    if (row.get("untranslatable") or "").strip().lower() in BOOL_TRUE:
        return True
    return False


def collect_conflicts(locale: str) -> list[Conflict]:
    tr_dir = TRANSLATIONS / locale / "tsv" / "Translation"
    if not tr_dir.exists():
        return []

    groups: dict[str, list[Entry]] = defaultdict(list)

    for tsv in sorted(tr_dir.glob("*.tsv")):
        if tsv.name.startswith("_"):
            continue
        with open(tsv, encoding="utf-8", newline="") as f:
            for row_num, row in enumerate(csv.DictReader(f, delimiter="\t"), start=2):
                if _row_excluded(row):
                    continue
                text = row.get("text", "") or ""
                tx = row.get("translation", "") or ""
                if not text or not tx:
                    continue
                key = _normalize_ws(text)
                if not key:
                    continue
                groups[key].append(Entry(
                    sheet=tsv.stem,
                    row=row_num,
                    text=text,
                    translation=tx,
                    method=(row.get("method") or "").strip(),
                    location=(row.get("location") or "").strip(),
                    filename=(row.get("filename") or "").strip(),
                    parent=(row.get("parent") or "").strip(),
                    name=(row.get("name") or "").strip(),
                    property=(row.get("property") or "").strip(),
                ))

    conflicts: list[Conflict] = []
    for key, entries in groups.items():
        if len(entries) < 2:
            continue
        distinct = {_normalize_ws(e.translation) for e in entries}
        if len(distinct) < 2:
            continue
        conflicts.append(Conflict(locale, key, len(distinct), entries))
    # largest groups first
    conflicts.sort(key=lambda c: (-len(c.entries), c.text_key))
    return conflicts


def _format_entry(e: Entry) -> str:
    ctx_bits: list[str] = []
    if e.filename:
        ctx_bits.append(f"file={e.filename}")
    if e.location:
        ctx_bits.append(f"loc={e.location}")
    if e.parent:
        ctx_bits.append(f"parent={e.parent}")
    if e.name:
        ctx_bits.append(f"name={e.name}")
    if e.property:
        ctx_bits.append(f"prop={e.property}")
    ctx = " ".join(ctx_bits) or "(no context)"
    return f"[{e.sheet}:r{e.row}] method={e.method}  {ctx}"


def _print_conflicts(conflicts: list[Conflict]) -> None:
    for idx, c in enumerate(conflicts, 1):
        print()
        print(f"#{idx}  text(normalized): {_preview(c.text_key, 60)}  "
              f"— {len(c.entries)} entries, {c.distinct_translations} distinct translations")
        by_tx: dict[str, list[Entry]] = defaultdict(list)
        for e in c.entries:
            by_tx[e.translation].append(e)
        for tx, ents in by_tx.items():
            print(f"  -> {_preview(tx, 60)}")
            for e in ents:
                print(f"      {_format_entry(e)}")


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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale",
        help="Locale name (e.g. Korean) or 'all'",
    )
    parser.add_argument(
        "--samples", type=int, default=SAMPLE_LIMIT,
        help=f"Max conflict groups to print per locale (default {SAMPLE_LIMIT})",
    )
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file "
                             "(used by orchestrator)")
    args = parser.parse_args(argv[1:])
    setup_logpath(args.logpath)

    if args.locale == TEMPLATE_LOCALE:
        print("Template has no translations — nothing to check.")
        return 0

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

    total_conflicts = 0
    for locale in locales:
        conflicts = collect_conflicts(locale)
        if not conflicts:
            print(f"\n=== {locale} ===")
            print("  OK (no conflicts)")
            continue

        total_conflicts += len(conflicts)
        print(f"\n=== {locale} ===")
        print(f"  [Info] CONFLICT groups: {len(conflicts)}")
        head = conflicts[: args.samples]
        _print_conflicts(head)
        if len(conflicts) > len(head):
            print(f"\n  ... and {len(conflicts) - len(head)} more group(s) "
                  f"(pass --samples N to show more)")

    print()
    print(f"=== Grand Total ===")
    print(f"  Info: {total_conflicts} conflict group(s)")
    # Info-only: never block builds
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
