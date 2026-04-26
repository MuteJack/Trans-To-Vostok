"""
Find rows that exist in xlsx but are absent in extracted TSV (reverse check).

Detects xlsx rows for nodes or texts deleted/changed by game updates.
Reverse of check_untranslated.py: xlsx→TSV instead of TSV→xlsx.

Targets:
    filetype=tscn/scn  → match against TSV index by unique_id + text
    filetype=tres       → check if text is in tres_text_set

Exclusions:
    method=ignore/pattern/substr  → cannot match against TSV source
    empty filetype                → manually entered row
    untranslatable=1               → skip

Usage:
    python check_old_translation.py <locale>

Example:
    python check_old_translation.py Korean

Output:
    screen + <locale>/.log/check_old_translation_YYYYMMDD_HHMMSS.log
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
    _effective_method,
    load_all_translation_sheets,
    load_tsv_index,
    load_tres_text_set,
    load_gd_text_set,
    load_metadata,
    format_metadata_lines,
    Tee,
)


BOOL_TRUE = {"1", "true"}
SCENE_FILETYPES = {"tscn", "scn"}


def check_old_translations(
    rows: list[dict],
    tsv_index: dict,
    tres_texts: set,
    gd_texts: set,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Find xlsx rows that have no counterpart in the extracted TSV.

    Returns:
        old_tscn: [row, ...]  — filetype=tscn/scn rows missing from TSV
        old_tres: [row, ...]  — filetype=tres rows missing from TSV
        old_gd:   [row, ...]  — filetype=gd rows missing from TSV
    """
    old_tscn: list[dict] = []
    old_tres: list[dict] = []
    old_gd: list[dict] = []

    for row in rows:
        effective = _effective_method(row)
        # skip methods that cannot be matched
        if effective in ("ignore", "pattern", "substr"):
            continue
        # skip untranslatable
        if row.get("untranslatable", "").strip().lower() in BOOL_TRUE:
            continue

        filetype = row.get("filetype", "").strip()
        text = row.get("text", "")

        if filetype in SCENE_FILETYPES:
            uid = row.get("unique_id", "").strip()
            if not uid:
                continue
            # match (unique_id, text) in TSV index
            candidates = tsv_index.get(uid)
            if candidates is None:
                old_tscn.append(row)
                continue
            # uid exists but no candidate matches text → old
            if not any(c["text"] == text for c in candidates):
                old_tscn.append(row)

        elif filetype == "tres":
            if not text:
                continue
            if text not in tres_texts:
                old_tres.append(row)

        elif filetype == "gd":
            if not text:
                continue
            if text not in gd_texts:
                old_gd.append(row)

    return old_tscn, old_tres, old_gd


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: python check_old_translation.py <locale>")
        print("예: python check_old_translation.py Korean")
        return 1

    locale = sys.argv[1]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    pkg_root = mod_root / "Trans To Vostok"
    locale_dir = pkg_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"
    tsv_dir = mod_root / ".tmp" / "parsed_text"

    if not xlsx_path.exists():
        print(f"[ERROR] xlsx 파일이 없습니다: {xlsx_path}")
        return 1
    if not tsv_dir.exists():
        print(f"[ERROR] TSV 디렉토리가 없습니다: {tsv_dir}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = locale_dir / ".log" / f"check_old_translation_{timestamp}.log"
    tee = Tee(log_path)

    try:
        tee.print(f"xlsx:   {xlsx_path}")
        tee.print(f"TSV:    {tsv_dir}")
        tee.print(f"로그:   {log_path}")
        tee.print(f"실행:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        meta = load_metadata(xlsx_path)
        for line in format_metadata_lines(meta):
            tee.print(line)
        tee.print()

        # 1. load TSV index
        tee.print("TSV 인덱스 빌드 중...")
        tsv_index = load_tsv_index(tsv_dir)
        tres_texts = load_tres_text_set(tsv_dir)
        gd_texts = load_gd_text_set(tsv_dir)
        total_tsv = sum(len(v) for v in tsv_index.values())
        tee.print(f"  tscn unique_id: {len(tsv_index)}개, 레코드: {total_tsv}")
        tee.print(f"  tres text: {len(tres_texts)}개, gd text: {len(gd_texts)}개")
        tee.print()

        # 2. load xlsx
        tee.print("xlsx 로드 중...")
        sheets = load_all_translation_sheets(xlsx_path)
        all_rows: list[dict] = []
        for sheet_name, _header, rows in sheets:
            all_rows.extend(rows)
        tee.print(f"  시트 {len(sheets)}개, 총 {len(all_rows)}행")
        tee.print()

        # 3. check old translations
        old_tscn, old_tres, old_gd = check_old_translations(all_rows, tsv_index, tres_texts, gd_texts)

        # 4. report
        if old_tscn:
            tee.print("=" * 80)
            tee.print(f"tscn — TSV에 없는 xlsx 행 ({len(old_tscn)}개)")
            tee.print("=" * 80)
            for row in old_tscn:
                tee.print(
                    f"  uid={row.get('unique_id', ''):<12}  "
                    f"filename={row.get('filename', '')!r}  "
                    f"text={_preview(row.get('text', ''), 50)}"
                )
            tee.print()

        if old_tres:
            tee.print("=" * 80)
            tee.print(f"tres — TSV에 없는 xlsx 행 ({len(old_tres)}개)")
            tee.print("=" * 80)
            for row in old_tres:
                tee.print(
                    f"  filename={row.get('filename', '')!r}  "
                    f"name={row.get('name', '')!r}  "
                    f"text={_preview(row.get('text', ''), 50)}"
                )
            tee.print()

        if old_gd:
            tee.print("=" * 80)
            tee.print(f"gd — TSV에 없는 xlsx 행 ({len(old_gd)}개, 휴리스틱 추출 한계 가능)")
            tee.print("=" * 80)
            for row in old_gd:
                tee.print(
                    f"  filename={row.get('filename', '')!r}  "
                    f"name={row.get('name', '')!r}  "
                    f"text={_preview(row.get('text', ''), 50)}"
                )
            tee.print()

        # 5. summary
        tee.print("=" * 80)
        total_old = len(old_tscn) + len(old_tres) + len(old_gd)
        if total_old == 0:
            tee.print("완료: old translation 없음 — 모든 xlsx 행이 추출 TSV와 일치합니다.")
        else:
            tee.print(
                f"완료: old translation {total_old}개 발견 "
                f"(tscn {len(old_tscn)}, tres {len(old_tres)}, gd {len(old_gd)})"
            )
            tee.print("  이 행들은 게임 업데이트로 삭제/변경된 텍스트일 수 있습니다.")
            tee.print("  xlsx에서 제거하거나 method=ignore 로 변경하세요.")

        return 0
    finally:
        tee.close()


if __name__ == "__main__":
    sys.exit(main())
