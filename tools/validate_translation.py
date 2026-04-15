"""
Translation.xlsx 검증 도구.

체크 항목:
1. [ERROR] TSV 매칭: location/name/type/parent/unique_id/text가 .tmp/extracted_text/의 TSV와 일치
   - text는 앞뒤 공백/개행까지 완전 일치 (엄격)
   - filetype이 '' 또는 'scn'이면 TSV 검증 대상 (location은 확장자 포함)
   - filetype이 '#literal', '#expression', 'tres'이면 TSV 검증 스킵
2. [WARNING] text ↔ translated 앞뒤 공백/개행이 일치하지 않으면 경고만 (에러 아님)
3. [ERROR] Transliteration, Machine translated 플래그가 0/1/true/false인가 (빈 셀 금지)
4. [ERROR] 중복 매칭 키:
   - 일반 행: (text, location, parent, name, type) 조합이 동일한 행 여러 개 → 에러
   - #literal: text가 중복된 #literal 행 여러 개 → 에러 (fallback 모호)
   - #expression: text가 중복된 #expression 행 여러 개 → 에러 (패턴 모호)
   - tres: text가 중복된 tres 행 여러 개 → 에러 (런타임 동작 동일)
5. [ERROR] filetype / location 조합 검증:
   - '' 또는 'scn': location 필수, .tscn 또는 .scn 확장자여야 함
   - '#literal', '#expression': location은 비어있어야 함
   - 'tres': location 등의 필드는 제약 없음 (검증 완화)
   - 그 외 값: 알 수 없는 filetype

사용법:
    python validate_translation.py                # 기본: Korean/Translation.xlsx 검증
    python validate_translation.py <xlsx_path>    # 다른 파일 지정

로그:
    검증 결과는 화면 출력과 동시에
    <xlsx_부모_폴더>/.log/validate_translation_YYYYMMDD_HHMMSS.log
    로 저장된다.

종료 코드:
    0 = 에러 없음 (경고는 무시)
    1 = 에러 있음
"""
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print(  "ERROR: openpyxl이 필요합니다. 아래 명령어를 입력해주세요.\n"
            " >> pip install openpyxl", file=sys.stderr)
    sys.exit(1)

# Windows 콘솔 한글 출력 지원
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


# 플래그 허용 값
VALID_FLAGS = {"0", "1", "true", "false"}

# TSV 매칭 시 비교할 필드 (text는 엄격 비교, 나머지는 strip 후 비교)
COMPARE_FIELDS = ["location", "name", "type", "parent", "text"]

# 엑셀(.xlsx) 포맷에서 캐리지 리턴(줄바꿈) \r이 _x000D_ 또는 _x000d_로 저장된 것을 치환하기 위한 패턴
_X000D_RE = re.compile(r"_x000[dD]_")


def _normalize_cell(value) -> str:
    """엑셀 셀 값을 문자열로 정규화. _x000d_ / _x000D_ 아티팩트 제거."""
    if value is None:
        return ""
    s = str(value)
    # 엑셀이 캐리지 리턴을 _x000D_로 저장하는 아티팩트 제거 (대소문자 모두)
    s = _X000D_RE.sub("", s)
    return s

# leading whitespace: text의 앞부분에서 공백과 개행 문자만 추출
def _leading_ws(s: str) -> str:
    """앞부분 공백/개행만 추출."""
    return s[: len(s) - len(s.lstrip())]

# trailing whitespace: text의 뒷부분에서 공백과 개행 문자만 추출
def _trailing_ws(s: str) -> str:
    """뒷부분 공백/개행만 추출."""
    return s[len(s.rstrip()):]


def _preview(text: str, limit: int = 60) -> str:
    """긴 문자열을 repr로 줄여서 표시."""
    r = repr(text)
    if len(r) > limit:
        return r[: limit - 3] + "...'"
    return r


def load_tsv_index(tsv_dir: Path) -> dict:
    """
    모든 TSV 파일에서 unique_id → [레코드 목록] 인덱스를 만든다.
    (unique_id는 씬 내 고유지만 씬 간에는 중복 가능하므로 리스트)
    """
    index = {}
    for tsv_file in sorted(tsv_dir.rglob("*.tsv")):
        try:
            with open(tsv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    uid = (row.get("unique_id") or "").strip()
                    if not uid:
                        continue
                    record = {
                        "location": (row.get("location") or "").strip(),
                        "name": (row.get("name") or "").strip(),
                        "type": (row.get("type") or "").strip(),
                        "parent": (row.get("parent") or "").strip(),
                        "text": row.get("text") or "",
                        "_tsv_file": tsv_file.name,
                    }
                    index.setdefault(uid, []).append(record)
        except Exception as e:
            print(f"[WARN] TSV 읽기 실패: {tsv_file} ({e})")
    return index


def load_xlsx_main(xlsx_path: Path, sheet_name: str = "Main") -> tuple[list[str], list[dict], str]:
    """
    Translation.xlsx의 지정 시트를 읽어 (헤더, 행 리스트, 시트 이름) 반환.
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"'{sheet_name}' 시트가 없습니다: {wb.sheetnames}")
    ws = wb[sheet_name]

    rows_iter = ws.iter_rows(values_only=True)
    # 헤더 정규화: _x000d_ 제거 + 내부 줄바꿈을 공백으로 + 중복 공백 축약
    header = []
    for c in next(rows_iter):
        h = _normalize_cell(c)
        h = h.replace("\r", " ").replace("\n", " ")
        h = " ".join(h.split())  # 중복 공백 제거
        header.append(h)

    rows = []
    for row_values in rows_iter:
        if row_values is None or all(v is None for v in row_values):
            continue
        row_dict = {}
        for i, key in enumerate(header):
            val = row_values[i] if i < len(row_values) else None
            row_dict[key] = _normalize_cell(val)
        rows.append(row_dict)

    wb.close()
    return header, rows, sheet_name


def check_tsv_match(row: dict, tsv_index: dict) -> list[str]:
    """체크 1 (ERROR): TSV 매칭. text는 앞뒤 공백/개행까지 엄격 비교."""
    errors = []

    filetype = row.get("filetype", "").strip()
    # #literal / #expression / tres 는 TSV 원본이 없거나 다른 방식이라 검증 스킵
    if filetype.startswith("#") or filetype == "tres":
        return errors
    # 빈 값이나 'scn' 만 TSV 검증 대상

    location = row.get("location", "").strip()
    uid = row.get("unique_id", "").strip()
    if not uid:
        errors.append(f"unique_id 비어있음 (location='{location}')")
        return errors

    candidates = tsv_index.get(uid)
    if not candidates:
        errors.append(f"unique_id={uid} 가 TSV에 없음")
        return errors

    # 후보가 여러 개면 text가 일치하는 것을 우선 선택 (씬 간 unique_id 중복 대비)
    xlsx_text = row.get("text", "")
    best = None
    for cand in candidates:
        if cand["text"] == xlsx_text:
            best = cand
            break
    if best is None:
        # 완전 일치 후보가 없으면 첫 후보로 비교 (에러로 남음)
        best = candidates[0]

    mismatches = []
    for field in COMPARE_FIELDS:
        xlsx_val = row.get(field, "")
        tsv_val = best[field]
        if field == "text":
            # text는 앞뒤 공백/개행까지 완전 일치해야 함
            if xlsx_val != tsv_val:
                mismatches.append(
                    f"{field}: xlsx={_preview(xlsx_val)} / tsv={_preview(tsv_val)}"
                )
        else:
            # name, type, parent는 strip 후 비교
            if xlsx_val.strip() != tsv_val.strip():
                mismatches.append(
                    f"{field}: xlsx={_preview(xlsx_val)} / tsv={_preview(tsv_val)}"
                )

    if mismatches:
        errors.append(
            f"unique_id={uid} ({best['_tsv_file']}) 필드 불일치: " + "; ".join(mismatches)
        )

    return errors


def check_whitespace(row: dict) -> list[str]:
    """
    체크 2 (WARNING): text ↔ translated 앞뒤 공백/개행 매칭.
    번역자 참고용 경고만 반환.
    """
    warnings = []
    text = row.get("text", "")
    translated = row.get("translated", "")

    # translated가 비어있으면 미번역으로 간주, 스킵
    if not translated:
        return warnings

    text_lead = _leading_ws(text)
    trans_lead = _leading_ws(translated)
    if text_lead != trans_lead:
        warnings.append(
            f"앞 공백 불일치: text={_preview(text_lead)} / translated={_preview(trans_lead)}"
        )

    text_trail = _trailing_ws(text)
    trans_trail = _trailing_ws(translated)
    if text_trail != trans_trail:
        warnings.append(
            f"뒤 공백 불일치: text={_preview(text_trail)} / translated={_preview(trans_trail)}"
        )

    return warnings


def check_flags(row: dict) -> list[str]:
    """체크 3 (ERROR): Transliteration, Machine translated 플래그 값."""
    errors = []
    for col in ["Transliteration", "Machine translated"]:
        val = row.get(col, "")
        if val == "":
            errors.append(f"{col} 컬럼이 비어있음")
            continue
        normalized = val.strip().lower()
        if normalized not in VALID_FLAGS:
            errors.append(f"{col} 값이 잘못됨: {val!r} (허용: 0/1/true/false)")
    return errors


def check_filetype_fields(row: dict) -> list[str]:
    """
    체크 5 (ERROR): filetype과 다른 필드의 조합 검증.
    - '' 또는 'scn': location 필수, .tscn/.scn 확장자
    - '#literal' / '#expression':
        * location 비어있음 → 전역 매칭
        * location 있음 → 스코프드 (씬 파일 경로여야 함, .tscn/.scn)
    - 'tres': 제약 없음 (런타임엔 #literal처럼 동작)
    """
    errors = []
    filetype = row.get("filetype", "").strip()
    location = row.get("location", "").strip()

    if filetype == "#literal" or filetype == "#expression":
        # 빈값 → 전역, 값 있음 → 스코프드 (.tscn/.scn 필요)
        if location != "" and not location.endswith((".tscn", ".scn")):
            errors.append(
                f"filetype={filetype!r} 의 scoped location은 "
                f".tscn 또는 .scn 으로 끝나야 함 (현재: {location!r})"
            )
    elif filetype == "tres":
        # tres는 검증 완화 — location 등 필드에 값이 있어도 OK
        pass
    elif filetype == "" or filetype == "scn":
        if location == "":
            errors.append(f"filetype={filetype!r} 는 location이 필수")
        elif not location.endswith((".tscn", ".scn")):
            errors.append(
                f"filetype={filetype!r} 의 location은 .tscn 또는 .scn 로 끝나야 함 "
                f"(현재: {location!r})"
            )
    else:
        errors.append(f"알 수 없는 filetype: {filetype!r}")

    return errors


def check_duplicates(rows: list[dict]) -> list[tuple[int, str]]:
    """
    체크 4 (ERROR): 런타임 매칭 키 중복.
    - 일반 행 (filetype='' or 'scn'): (text, location, parent, name, type) 조합이 동일하면 에러
    - #literal / tres (전역): text가 동일하면 에러 (런타임에 text-only 매칭이라 모호)
    - #literal scoped: (location, text) 동일하면 에러
    - #expression (전역): text가 동일하면 에러 (패턴 모호)
    - #expression scoped: (location, text) 동일하면 에러
    ignore=1 행은 제외.

    반환: [(행번호, 메시지), ...]
    """
    errors = []
    normal_keys = {}               # (text, loc, parent, name, type) → [(row_num, row), ...]
    literal_global = {}            # text → [...] (#literal 전역 + tres)
    literal_scoped = {}            # (location, text) → [...] (#literal scoped)
    expression_global = {}         # text → [...]
    expression_scoped = {}         # (location, text) → [...]

    for i, row in enumerate(rows, start=2):
        if row.get("ignore", "").strip() == "1":
            continue

        text = row.get("text", "")
        filetype = row.get("filetype", "").strip()
        location = row.get("location", "").strip()

        if filetype == "tres":
            literal_global.setdefault(text, []).append((i, row))
        elif filetype == "#literal":
            if location == "":
                literal_global.setdefault(text, []).append((i, row))
            else:
                literal_scoped.setdefault((location, text), []).append((i, row))
        elif filetype == "#expression":
            if location == "":
                expression_global.setdefault(text, []).append((i, row))
            else:
                expression_scoped.setdefault((location, text), []).append((i, row))
        else:
            # 일반 (scn 또는 빈값) — location은 확장자 포함 상태로 비교
            key = (
                text,
                row.get("location", "").strip(),
                row.get("parent", "").strip(),
                row.get("name", "").strip(),
                row.get("type", "").strip(),
            )
            normal_keys.setdefault(key, []).append((i, row))

    # 일반 행 중복 검사
    for key, occurrences in normal_keys.items():
        if len(occurrences) > 1:
            row_nums = ", ".join(str(n) for n, _ in occurrences)
            text_preview = _preview(key[0], 40)
            msg = (
                f"중복 매칭 키 ({len(occurrences)}개): "
                f"text={text_preview}, location={key[1]!r}, "
                f"parent={key[2]!r}, name={key[3]!r}, type={key[4]!r} "
                f"(행: {row_nums})"
            )
            for row_num, _ in occurrences:
                errors.append((row_num, msg))

    # #literal / tres 전역 중복 검사 (text만 기준)
    for text, occurrences in literal_global.items():
        if len(occurrences) > 1:
            row_nums = ", ".join(str(n) for n, _ in occurrences)
            text_preview = _preview(text, 40)
            msg = (
                f"전역 text-only 매칭 중복 ({len(occurrences)}개, #literal/tres): "
                f"text={text_preview} (행: {row_nums})"
            )
            for row_num, _ in occurrences:
                errors.append((row_num, msg))

    # #literal scoped 중복 검사 ((location, text) 기준)
    for (loc, text), occurrences in literal_scoped.items():
        if len(occurrences) > 1:
            row_nums = ", ".join(str(n) for n, _ in occurrences)
            text_preview = _preview(text, 40)
            msg = (
                f"scoped #literal 중복 ({len(occurrences)}개): "
                f"location={loc!r}, text={text_preview} (행: {row_nums})"
            )
            for row_num, _ in occurrences:
                errors.append((row_num, msg))

    # #expression 전역 중복 검사 (text만 기준)
    for text, occurrences in expression_global.items():
        if len(occurrences) > 1:
            row_nums = ", ".join(str(n) for n, _ in occurrences)
            text_preview = _preview(text, 40)
            msg = (
                f"전역 #expression text 중복 ({len(occurrences)}개): "
                f"text={text_preview} (행: {row_nums})"
            )
            for row_num, _ in occurrences:
                errors.append((row_num, msg))

    # #expression scoped 중복 검사 ((location, text) 기준)
    for (loc, text), occurrences in expression_scoped.items():
        if len(occurrences) > 1:
            row_nums = ", ".join(str(n) for n, _ in occurrences)
            text_preview = _preview(text, 40)
            msg = (
                f"scoped #expression 중복 ({len(occurrences)}개): "
                f"location={loc!r}, text={text_preview} (행: {row_nums})"
            )
            for row_num, _ in occurrences:
                errors.append((row_num, msg))

    return errors


class Tee:
    """print 출력을 화면과 파일에 동시 기록."""

    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = open(log_path, "w", encoding="utf-8")

    def print(self, *args, **kwargs):
        end = kwargs.get("end", "\n")
        sep = kwargs.get("sep", " ")
        text = sep.join(str(a) for a in args) + end
        print(*args, **kwargs)
        self._fp.write(text)

    def close(self):
        self._fp.close()


class ValidationResult:
    """검증 결과. error_count가 0이면 통과."""

    def __init__(self):
        self.error_tsv = 0
        self.error_flags = 0
        self.error_dup = 0
        self.error_filetype = 0
        self.warn_ws = 0
        self.log_path: Path | None = None

    @property
    def error_count(self) -> int:
        return (
            self.error_tsv
            + self.error_flags
            + self.error_dup
            + self.error_filetype
        )

    @property
    def warning_count(self) -> int:
        return self.warn_ws

    @property
    def ok(self) -> bool:
        return self.error_count == 0


def validate_xlsx(xlsx_path: Path, tsv_dir: Path) -> ValidationResult:
    """
    Translation.xlsx를 검증하고 결과를 반환.
    로그 파일은 <xlsx 부모>/.log/ 에 자동 생성.

    예외:
        FileNotFoundError: xlsx 또는 tsv_dir이 없음
        ValueError: 필수 컬럼 누락
    """
    result = ValidationResult()

    if not xlsx_path.exists():
        raise FileNotFoundError(f"xlsx 파일이 없습니다: {xlsx_path}")
    if not tsv_dir.exists():
        raise FileNotFoundError(
            f"TSV 디렉토리가 없습니다: {tsv_dir}\n먼저 extract_tscn_text.py를 실행하세요."
        )

    # 로그 파일
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = xlsx_path.parent / ".log" / f"validate_translation_{timestamp}.log"
    result.log_path = log_path
    tee = Tee(log_path)

    try:
        tee.print(f"검증 대상: {xlsx_path}")
        tee.print(f"TSV 소스:  {tsv_dir}")
        tee.print(f"로그 파일: {log_path}")
        tee.print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        tee.print()

        # TSV 인덱스 빌드
        tee.print("TSV 인덱스 빌드 중...")
        tsv_index = load_tsv_index(tsv_dir)
        total_tsv_entries = sum(len(v) for v in tsv_index.values())
        tee.print(f"  unique_id 수: {len(tsv_index)}, 총 레코드: {total_tsv_entries}")

        # xlsx 로드
        tee.print("Translation.xlsx 로드 중...")
        header, rows, sheet_name = load_xlsx_main(xlsx_path)
        tee.print(f"  시트: {sheet_name}, 데이터 행: {len(rows)}개")
        tee.print()

        # 컬럼 존재 체크
        required = ["filetype", "location", "name", "type", "parent", "unique_id",
                    "text", "translated",
                    "Transliteration", "Machine translated"]
        missing = [c for c in required if c not in header]
        if missing:
            tee.print(f"[ERROR] 필수 컬럼 누락: {missing}")
            tee.print(f"실제 헤더: {header}")
            raise ValueError(f"필수 컬럼 누락: {missing}")

        # 행별 이슈를 {row_num: [(level, label, msg), ...]} 로 수집
        issues_by_row = {}

        for i, row in enumerate(rows, start=2):
            local_issues = []

            for msg in check_tsv_match(row, tsv_index):
                local_issues.append(("ERROR", "TSV 매칭", msg))
                result.error_tsv += 1

            for msg in check_whitespace(row):
                local_issues.append(("WARN", "공백", msg))
                result.warn_ws += 1

            for msg in check_flags(row):
                local_issues.append(("ERROR", "플래그", msg))
                result.error_flags += 1

            for msg in check_filetype_fields(row):
                local_issues.append(("ERROR", "filetype", msg))
                result.error_filetype += 1

            if local_issues:
                issues_by_row.setdefault(i, []).extend(local_issues)

        # 체크 4: 중복 매칭 키 (전체 스캔)
        for row_num, msg in check_duplicates(rows):
            issues_by_row.setdefault(row_num, []).append(("ERROR", "중복 키", msg))
            result.error_dup += 1

        # 행 번호 순으로 출력
        for i in sorted(issues_by_row.keys()):
            row = rows[i - 2]
            text_preview = _preview(row.get("text", ""), 60)
            tee.print(f"[{sheet_name}: Row {i}] text={text_preview}")
            for level, label, msg in issues_by_row[i]:
                tee.print(f"  [{level}] {label}: {msg}")

        tee.print()
        tee.print("=" * 60)
        tee.print(f"검증 완료: {len(rows)}행 검사")
        tee.print(
            f"  ERROR {result.error_count}개  "
            f"(TSV 매칭 {result.error_tsv}, 플래그 {result.error_flags}, "
            f"중복 키 {result.error_dup}, filetype {result.error_filetype})"
        )
        tee.print(f"  WARN  {result.warning_count}개  (공백 {result.warn_ws})")

        return result
    finally:
        tee.close()


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    default_xlsx = (script_dir / "../Korean/Translation.xlsx").resolve()
    default_tsv = (script_dir / "../.tmp/extracted_text").resolve()

    xlsx_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_xlsx
    tsv_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_tsv

    try:
        result = validate_xlsx(xlsx_path, tsv_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        return 1

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
