"""
Translation.xlsx → 런타임 TSV 빌드 스크립트.

사용법:
    python build_runtime_tsv.py <locale>

예시:
    python build_runtime_tsv.py Korean

동작:
1. <locale>/Translation.xlsx 를 대상으로 validate_translation.validate_xlsx() 호출
2. 에러가 하나라도 있으면 빌드 실패 (SystemExit)
3. MetaData 시트 제외한 모든 시트의 행을 수집
4. ignore 컬럼이 '1' 또는 'true'인 행은 제외
5. translated 값이 비어있는 행은 제외
6. location 값에 따라 3개의 TSV로 분류 저장:
       - #literal     → <locale>/translation_literal.tsv    (컬럼: text, translated)
       - #expression  → <locale>/translation_expression.tsv (컬럼: text, translated)
       - 그 외        → <locale>/translation.tsv            (컬럼: location, parent, name, type, text, translated)
7. 원자적 쓰기 (.tmp → rename)

출력: <locale>/ 폴더에 TSV 파일 생성
"""
import csv
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl이 필요합니다. pip install openpyxl", file=sys.stderr)
    sys.exit(1)

# Windows 콘솔 한글 출력 지원
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass

# 같은 폴더의 validate_translation 모듈 import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_translation import validate_xlsx, _normalize_cell


# filetype 분류 기준
FILETYPE_LITERAL = "#literal"
FILETYPE_EXPRESSION = "#expression"
FILETYPE_TRES = "tres"
FILETYPE_SCN = "scn"  # 빈 값도 scn으로 취급

# 씬 파일 확장자 (런타임 TSV 출력 시 location에서 제거)
SCENE_EXTENSIONS = (".tscn", ".scn")

# 출력 TSV 컬럼
COLUMNS_MAIN = ["location", "parent", "name", "type", "text", "translated"]
COLUMNS_LITERAL = ["text", "translated"]
COLUMNS_EXPRESSION = ["text", "translated"]

# ignore 값으로 간주할 문자열
IGNORE_VALUES = {"1", "true"}


def _strip_scene_extension(location: str) -> str:
    """씬 파일 확장자(.tscn/.scn)를 제거. 다른 경우는 원본 유지."""
    for ext in SCENE_EXTENSIONS:
        if location.endswith(ext):
            return location[: -len(ext)]
    return location


def load_all_sheets(xlsx_path: Path) -> list[dict]:
    """
    MetaData 시트를 제외한 모든 시트를 읽어 행 리스트로 반환.
    각 행은 {컬럼: 값} 딕셔너리. 빈 행은 제외.
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    all_rows = []

    for sheet_name in wb.sheetnames:
        if sheet_name == "MetaData":
            continue
        ws = wb[sheet_name]
        rows_iter = ws.iter_rows(values_only=True)

        # 헤더 파싱
        try:
            header_row = next(rows_iter)
        except StopIteration:
            continue
        header = []
        for c in header_row:
            h = _normalize_cell(c)
            h = h.replace("\r", " ").replace("\n", " ")
            h = " ".join(h.split())
            header.append(h)

        for row_values in rows_iter:
            if row_values is None or all(v is None for v in row_values):
                continue
            row_dict = {"_sheet": sheet_name}
            for i, key in enumerate(header):
                val = row_values[i] if i < len(row_values) else None
                row_dict[key] = _normalize_cell(val)
            all_rows.append(row_dict)

    wb.close()
    return all_rows


def classify_rows(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict], dict]:
    """
    행을 filetype 기준으로 분류한다:
      - main:        filetype='' or 'scn' → translation.tsv (location 확장자 제거)
      - literal:     filetype='#literal' or 'tres' → translation_literal.tsv (text-only)
      - expression:  filetype='#expression' → translation_expression.tsv (정규식)
      - stats:       제외/미번역 통계

    반환: (main, literal, expression, stats)
    """
    main_rows = []
    literal_rows = []
    expression_rows = []
    stats = {
        "total": len(rows),
        "excluded_ignore": 0,
        "excluded_untranslated": 0,
        "main": 0,
        "literal": 0,
        "expression": 0,
        "tres": 0,
    }

    for row in rows:
        # ignore 체크
        ignore_val = row.get("ignore", "").strip().lower()
        if ignore_val in IGNORE_VALUES:
            stats["excluded_ignore"] += 1
            continue

        # 미번역 체크
        translated = row.get("translated", "")
        if translated == "":
            stats["excluded_untranslated"] += 1
            continue

        filetype = row.get("filetype", "").strip()

        if filetype == FILETYPE_LITERAL:
            literal_rows.append(row)
            stats["literal"] += 1
        elif filetype == FILETYPE_EXPRESSION:
            expression_rows.append(row)
            stats["expression"] += 1
        elif filetype == FILETYPE_TRES:
            # tres도 런타임엔 text-only 매칭이라 literal과 동일 파일에 합침
            literal_rows.append(row)
            stats["tres"] += 1
        else:
            # 빈 값 또는 'scn' → 일반 행
            # location 확장자 제거 후 복사본 저장 (원본 보존)
            new_row = dict(row)
            new_row["location"] = _strip_scene_extension(
                row.get("location", "").strip()
            )
            main_rows.append(new_row)
            stats["main"] += 1

    return main_rows, literal_rows, expression_rows, stats


def write_tsv(out_path: Path, columns: list[str], rows: list[dict]) -> None:
    """
    TSV 파일을 원자적으로 쓴다. 임시 파일에 먼저 기록한 후 rename.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([row.get(c, "") for c in columns])

        # 원자적 덮어쓰기
        tmp_path.replace(out_path)
    except Exception:
        # 임시 파일 정리
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: python build_runtime_tsv.py <locale>")
        print("예: python build_runtime_tsv.py Korean")
        return 1

    locale = sys.argv[1]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent              # mods/Trans To Vostok
    locale_dir = mod_root / locale            # mods/Trans To Vostok/Korean
    xlsx_path = locale_dir / "Translation.xlsx"
    tsv_dir = mod_root / ".tmp" / "extracted_text"

    if not locale_dir.exists():
        print(f"[ERROR] 로케일 폴더가 없습니다: {locale_dir}")
        return 1
    if not xlsx_path.exists():
        print(f"[ERROR] xlsx 파일이 없습니다: {xlsx_path}")
        return 1

    # 1. 검증 실행
    print(f"[1/4] 검증 중... ({locale})")
    try:
        result = validate_xlsx(xlsx_path, tsv_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] 검증 실패: {e}")
        return 1

    print(f"  → 로그: {result.log_path}")
    if not result.ok:
        print(
            f"[ERROR] 검증 실패: {result.error_count}개 에러 "
            f"(TSV 매칭 {result.error_tsv}, 플래그 {result.error_flags}, 중복 {result.error_dup})"
        )
        print("빌드를 중단합니다. 위 로그를 확인하세요.")
        raise SystemExit(1)

    if result.warning_count > 0:
        print(f"  경고 {result.warning_count}개 (진행 계속)")
    print()

    # 2. xlsx 로드
    print("[2/4] xlsx 로드 중...")
    all_rows = load_all_sheets(xlsx_path)
    print(f"  → MetaData 제외 {len(all_rows)}행 로드")
    print()

    # 3. 행 분류
    print("[3/4] 행 분류 중...")
    main_rows, literal_rows, expression_rows, stats = classify_rows(all_rows)
    print(f"  → scn (일반):     {stats['main']}행")
    print(f"  → #literal:       {stats['literal']}행")
    print(f"  → tres:           {stats['tres']}행 (→ literal과 합침)")
    print(f"  → #expression:    {stats['expression']}행")
    print(f"  → 제외 (ignore):  {stats['excluded_ignore']}행")
    print(f"  → 제외 (미번역):  {stats['excluded_untranslated']}행")
    print()

    # 4. TSV 작성
    print("[4/4] TSV 작성 중...")
    out_main = locale_dir / "translation.tsv"
    out_literal = locale_dir / "translation_literal.tsv"
    out_expression = locale_dir / "translation_expression.tsv"

    write_tsv(out_main, COLUMNS_MAIN, main_rows)
    print(f"  → {out_main.relative_to(mod_root)} ({len(main_rows)}행)")

    write_tsv(out_literal, COLUMNS_LITERAL, literal_rows)
    print(f"  → {out_literal.relative_to(mod_root)} ({len(literal_rows)}행)")

    write_tsv(out_expression, COLUMNS_EXPRESSION, expression_rows)
    print(f"  → {out_expression.relative_to(mod_root)} ({len(expression_rows)}행)")

    print()
    print("=" * 60)
    print(f"빌드 완료: {locale}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
