"""
Pre-check for runtime key duplicates within xlsx.

Runs the same duplicate-check logic as validate_translation.py to report
both intra-sheet and cross-sheet duplicates. Use to quickly verify duplicates
without TSV extraction or other validation.

Targets:
    - exclude rows with ignore / untranslatable=1
    - static + scoped literal  → share 5-tuple key space
    - global literal           → text key
    - scoped pattern           → 5-tuple key
    - global pattern           → text key
    - global substr            → text key

Usage:
    python check_duplicate.py <locale>

Example:
    python check_duplicate.py Korean

Exit codes:
    0 — no duplicates
    1 — duplicates found or xlsx missing

Log:
    <locale>/.log/check_duplicate_YYYYMMDD_HHMMSS.log
"""
import sys
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
    check_duplicates,
    check_duplicates_cross_sheet,
    load_all_translation_sheets,
    Tee,
)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python check_duplicate.py <locale>")
        print("Example: python check_duplicate.py Korean")
        return 1

    locale = sys.argv[1]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    translations_root = mod_root / "Translations"
    locale_dir = translations_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"

    if not xlsx_path.exists():
        print(f"[ERROR] xlsx file not found: {xlsx_path}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = locale_dir / ".log" / f"check_duplicate_{timestamp}.log"
    tee = Tee(log_path)

    try:
        tee.print(f"xlsx: {xlsx_path}")
        tee.print(f"Log:  {log_path}")
        tee.print(f"Run:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        tee.print()

        tee.print("Loading xlsx...")
        sheets = load_all_translation_sheets(xlsx_path)
        total_rows = sum(len(rows) for _, _, rows in sheets)
        tee.print(f"  {len(sheets)} sheets, {total_rows} rows")
        for sheet_name, _, rows in sheets:
            tee.print(f"    {sheet_name}: {len(rows)} rows")
        tee.print()

        intra_count = 0
        cross_count = 0

        # intra-sheet duplicates
        tee.print("[Intra-sheet duplicates]")
        any_intra = False
        for sheet_name, _header, rows in sheets:
            intra: dict = {}
            for row_num, msg in check_duplicates(rows):
                intra.setdefault(row_num, []).append(msg)
                intra_count += 1
            if not intra:
                continue
            any_intra = True
            tee.print(f"  [{sheet_name}]")
            for i in sorted(intra.keys()):
                row = rows[i - 2]
                text_preview = _preview(row.get("text", ""), 60)
                tee.print(f"    Row {i}: text={text_preview}")
                for msg in intra[i]:
                    tee.print(f"      {msg}")
        if not any_intra:
            tee.print("  none.")
        tee.print()

        # cross-sheet duplicates
        tee.print("[Cross-sheet duplicates]")
        cross: dict = {}
        for sn, row_num, msg in check_duplicates_cross_sheet(sheets):
            cross.setdefault(sn, {}).setdefault(row_num, []).append(msg)
            cross_count += 1
        if cross:
            sheet_rows_map = {sn: rows for sn, _, rows in sheets}
            for sn in sorted(cross.keys()):
                tee.print(f"  [{sn}]")
                for i in sorted(cross[sn].keys()):
                    row = sheet_rows_map[sn][i - 2]
                    text_preview = _preview(row.get("text", ""), 60)
                    tee.print(f"    Row {i}: text={text_preview}")
                    for msg in cross[sn][i]:
                        tee.print(f"      {msg}")
        else:
            tee.print("  none.")
        tee.print()

        tee.print("=" * 60)
        total = intra_count + cross_count
        tee.print(f"Summary: intra-sheet {intra_count} + cross-sheet {cross_count} = {total} total")
        return 0 if total == 0 else 1
    finally:
        tee.close()


if __name__ == "__main__":
    sys.exit(main())
