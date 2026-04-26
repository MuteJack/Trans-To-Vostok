"""
Translation conflict check within xlsx.

Based on text with whitespace stripped, warns when the same source text has
**different translations** registered. If the same source text is translated
differently across multiple methods/contexts, consistency is broken — flagged for review.

Targets:
    - exclude rows with ignore / untranslatable=1
    - exclude rows with empty translation
    - if text matches after whitespace removal but translation differs → conflict

Currently only outputs WARNING (not ERROR, exit code 0).

Usage:
    python check_conflict.py <locale>

Example:
    python check_conflict.py Korean

Log:
    <locale>/.log/check_conflict_YYYYMMDD_HHMMSS.log
"""
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import openpyxl  # noqa: F401
except ImportError:
    print("ERROR: openpyxl is required. pip install openpyxl", file=sys.stderr)
    sys.exit(1)

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_translation import (
    _preview,
    _effective_method,
    load_all_translation_sheets,
    Tee,
)


BOOL_TRUE = {"1", "true"}


def _normalize_text(s: str) -> str:
    """Comparison key with all whitespace/tabs/newlines removed."""
    return "".join(s.split())


def collect_conflicts(sheets: list) -> list[dict]:
    """
    Iterate rows per sheet, grouping by (stripped_text → [entry, ...]).
    Conflict is detected if translations differ.

    entry: {sheet, row_idx, method, filename, filetype, location,
            parent, name, property, text, translation}
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    total_eligible = 0

    for sheet_name, _header, rows in sheets:
        for i, row in enumerate(rows, start=2):  # 2 = first row excluding header
            text = row.get("text", "") or ""
            translation = row.get("translation", "") or ""
            if not text or not translation:
                continue

            effective = _effective_method(row)
            if effective == "ignore":
                continue
            if str(row.get("untranslatable", "")).strip().lower() in BOOL_TRUE:
                continue

            key = _normalize_text(text)
            if not key:
                continue

            groups[key].append({
                "sheet": sheet_name,
                "row_idx": i,
                "method": effective,
                "filename": (row.get("filename") or "").strip(),
                "filetype": (row.get("filetype") or "").strip(),
                "location": (row.get("location") or "").strip(),
                "parent": (row.get("parent") or "").strip(),
                "name": (row.get("name") or "").strip(),
                "property": (row.get("property") or "").strip(),
                "text": text,
                "translation": translation,
            })
            total_eligible += 1

    # extract only groups with differing translations as conflicts
    conflicts: list[dict] = []
    for key, entries in groups.items():
        if len(entries) < 2:
            continue
        # also compare translations with whitespace stripped (whitespace differences are not conflicts)
        distinct_translations = set()
        for e in entries:
            distinct_translations.add(_normalize_text(e["translation"]))
        if len(distinct_translations) >= 2:
            conflicts.append({
                "key": key,
                "entries": entries,
                "distinct_count": len(distinct_translations),
            })

    return conflicts, total_eligible


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python check_conflict.py <locale>")
        print("Example: python check_conflict.py Korean")
        return 1

    locale = sys.argv[1]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    pkg_root = mod_root / "Trans To Vostok"
    locale_dir = pkg_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"

    if not xlsx_path.exists():
        print(f"[ERROR] xlsx file not found: {xlsx_path}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = locale_dir / ".log" / f"check_conflict_{timestamp}.log"
    tee = Tee(log_path)

    try:
        tee.print(f"xlsx: {xlsx_path}")
        tee.print(f"Log:  {log_path}")
        tee.print(f"Run:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        tee.print()

        tee.print("Loading xlsx...")
        sheets = load_all_translation_sheets(xlsx_path)
        tee.print(f"  {len(sheets)} sheets")
        tee.print()

        tee.print("Checking conflicts... (based on whitespace-stripped text)")
        conflicts, total_eligible = collect_conflicts(sheets)
        tee.print(f"  Rows checked: {total_eligible}")
        tee.print(f"  Conflict groups: {len(conflicts)}")
        tee.print()

        if not conflicts:
            tee.print("No conflicts.")
            return 0

        # sort conflict groups by entry count, descending
        conflicts.sort(key=lambda c: len(c["entries"]), reverse=True)

        tee.print("=" * 80)
        tee.print(f"[WARNING] {len(conflicts)} translation conflicts")
        tee.print("=" * 80)

        for idx, c in enumerate(conflicts, 1):
            tee.print()
            tee.print(
                f"#{idx}  text(stripped): {_preview(c['key'], 50)}  "
                f"- {len(c['entries'])} entries, {c['distinct_count']} distinct translations"
            )
            # display group per translation
            by_trans: dict[str, list[dict]] = defaultdict(list)
            for e in c["entries"]:
                by_trans[e["translation"]].append(e)
            for trans, ents in by_trans.items():
                tee.print(f"  → {_preview(trans, 50)}")
                for e in ents:
                    ctx_bits = []
                    if e["filename"]:
                        ctx_bits.append(f"file={e['filename']}.{e['filetype']}")
                    if e["location"]:
                        ctx_bits.append(f"loc={e['location']}")
                    if e["parent"]:
                        ctx_bits.append(f"parent={e['parent']}")
                    if e["name"]:
                        ctx_bits.append(f"name={e['name']}")
                    if e["property"]:
                        ctx_bits.append(f"prop={e['property']}")
                    ctx = " ".join(ctx_bits) if ctx_bits else "(no context)"
                    tee.print(
                        f"    [{e['sheet']}:{e['row_idx']}] method={e['method']}  {ctx}"
                    )

        tee.print()
        tee.print("=" * 80)
        tee.print(f"Summary: {len(conflicts)} conflict groups, {total_eligible} rows checked")
        return 0
    finally:
        tee.close()


if __name__ == "__main__":
    sys.exit(main())
