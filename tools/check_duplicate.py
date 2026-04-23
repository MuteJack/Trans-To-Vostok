"""
xlsx 내 런타임 키 중복 사전 체크.

validate_translation.py 가 수행하는 중복 검사와 동일한 로직을 실행해
시트 내 / 시트 간 중복을 모두 보고한다. TSV 추출이나 다른 검증 없이
빠르게 중복만 확인할 때 사용.

검사 대상:
    - ignore / untranslatable=1 행은 제외
    - static + scoped literal  → 5-tuple 키 공간 공유
    - 전역 literal             → text 키
    - scoped pattern           → 5-tuple 키
    - 전역 pattern             → text 키
    - 전역 substr              → text 키

사용법:
    python check_duplicate.py <locale>

예:
    python check_duplicate.py Korean

종료 코드:
    0 — 중복 없음
    1 — 중복 있음 또는 xlsx 누락

로그:
    <locale>/.log/check_duplicate_YYYYMMDD_HHMMSS.log
"""
import sys
from datetime import datetime
from pathlib import Path

try:
    import openpyxl  # noqa: F401
except ImportError:
    print("ERROR: openpyxl이 필요합니다. pip install openpyxl", file=sys.stderr)
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
        print("사용법: python check_duplicate.py <locale>")
        print("예: python check_duplicate.py Korean")
        return 1

    locale = sys.argv[1]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    pkg_root = mod_root / "Trans To Vostok"
    locale_dir = pkg_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"

    if not xlsx_path.exists():
        print(f"[ERROR] xlsx 파일이 없습니다: {xlsx_path}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = locale_dir / ".log" / f"check_duplicate_{timestamp}.log"
    tee = Tee(log_path)

    try:
        tee.print(f"xlsx: {xlsx_path}")
        tee.print(f"로그: {log_path}")
        tee.print(f"실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        tee.print()

        tee.print("xlsx 로드 중...")
        sheets = load_all_translation_sheets(xlsx_path)
        total_rows = sum(len(rows) for _, _, rows in sheets)
        tee.print(f"  시트 {len(sheets)}개, 총 {total_rows}행")
        for sheet_name, _, rows in sheets:
            tee.print(f"    {sheet_name}: {len(rows)}행")
        tee.print()

        intra_count = 0
        cross_count = 0

        # 시트 내 중복
        tee.print("[시트 내 중복]")
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
            tee.print("  없음.")
        tee.print()

        # 시트 간 중복
        tee.print("[시트 간 중복]")
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
            tee.print("  없음.")
        tee.print()

        tee.print("=" * 60)
        total = intra_count + cross_count
        tee.print(f"요약: 시트 내 {intra_count}건 + 시트 간 {cross_count}건 = 총 {total}건")
        return 0 if total == 0 else 1
    finally:
        tee.close()


if __name__ == "__main__":
    sys.exit(main())
