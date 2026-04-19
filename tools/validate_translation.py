"""
Translation.xlsx 검증 도구.

스키마 (18컬럼):
    A. 메타 (도구 미사용): WHERE, SUB, KIND
    B. 상태 플래그 (검증만): Transliteration, Machine translated, Confused, ignore
    C. 매칭: method, filename, filetype, location, parent, name, type, unique_id
    D. 내용: text, translation
    E. 메모 (도구 미사용): DESCRIPTION

method 값:
    static   — (location, parent, name, type, text) 완전 일치 1:1 매칭 (TSV 검증됨)
    literal  — text 완전 일치 (location 있으면 scoped, 없으면 전역)
    pattern  — 정규식 매칭 (location 있으면 scoped, 없으면 전역)
    ""       — 빈값은 literal 로 기본 처리 (수동 입력 편의)

체크 항목:
1. [ERROR] 필수 컬럼 누락
2. [ERROR] TSV 매칭 (method=static 전용):
   - filetype in {tscn, scn} 에서 unique_id 기반 TSV 대조
   - text 는 앞뒤 공백/개행까지 완전 일치 (엄격)
3. [WARNING] text ↔ translation 앞뒤 공백/개행 불일치
4. [ERROR] 플래그 값 검증: Transliteration, Machine translated, Confused, ignore
   - 허용: 0/1/true/false/""
5. [ERROR] method / 필드 조합 검증:
   - static: location/parent/name/type/unique_id 필수, filetype∈{tscn,scn}
   - literal + location: parent/name/type 필수 (scoped)
   - literal + no location: 컨텍스트 자유 (전역)
   - pattern + location: parent/name/type 필수 (scoped)
   - pattern + no location: 컨텍스트 자유 (전역)
   - "": literal 로 취급
6. [WARNING] 빈 method + unique_id 채워짐 → static 명시 권장
7. [ERROR] 중복 매칭 키:
   - static + scoped literal: (location, parent, name, type, text) 통합 공간
   - 전역 literal: text 공간
   - scoped pattern: (location, parent, name, type, text) 공간
   - 전역 pattern: text 공간

사용법:
    python validate_translation.py <locale>

예시:
    python validate_translation.py Korean

로그:
    <xlsx_부모_폴더>/.log/validate_translation_YYYYMMDD_HHMMSS.log

종료 코드:
    0 = 에러 없음 (경고 무시)
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
    print("ERROR: openpyxl이 필요합니다. 아래 명령어를 입력해주세요.\n"
          " >> pip install openpyxl", file=sys.stderr)
    sys.exit(1)

# Windows 콘솔 한글 출력 지원
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


# 플래그 허용 값 (빈 값도 허용됨 — 명시되지 않은 경우로 간주)
VALID_FLAGS = {"", "0", "1", "true", "false"}

# 플래그 컬럼 (ignore 는 method=ignore 로 대체됨)
FLAG_COLUMNS = ["Transliteration", "Machine translated", "Confused", "untranslatable"]

# 유효한 method 값 (빈 문자열은 literal 로 기본 처리됨, ignore 는 제외 처리)
VALID_METHODS = {"", "static", "literal", "pattern", "substr", "ignore"}

# 씬 파일 확장자 (소스 타입)
SCENE_FILETYPES = {"tscn", "scn"}

# MetaData 시트 제외 (번역 데이터 아님)
SKIP_SHEETS = {"MetaData"}

# 엑셀 아티팩트 _x000D_ 제거용
_X000D_RE = re.compile(r"_x000[dD]_")


# ==========================================
# 유틸
# ==========================================

def _normalize_cell(value) -> str:
    """엑셀 셀 값을 문자열로 정규화. _x000d_ / _x000D_ 아티팩트 제거."""
    if value is None:
        return ""
    s = str(value)
    s = _X000D_RE.sub("", s)
    return s


def _leading_ws(s: str) -> str:
    return s[: len(s) - len(s.lstrip())]


def _trailing_ws(s: str) -> str:
    return s[len(s.rstrip()):]


def _preview(text: str, limit: int = 60) -> str:
    r = repr(text)
    if len(r) > limit:
        return r[: limit - 3] + "...'"
    return r


def _effective_method(row: dict) -> str:
    """빈 method 를 literal 로 기본 처리. ignore 는 그대로 반환."""
    m = row.get("method", "").strip()
    if m == "ignore":
        return "ignore"
    return m if m else "literal"


# ==========================================
# TSV 인덱스 (추출된 .tscn.tsv / .tres.tsv 에서 unique_id 기반)
# ==========================================

def load_tsv_index(tsv_dir: Path) -> dict:
    """
    추출된 TSV 파일에서 unique_id → [레코드 목록] 인덱스를 만든다.

    대상 파일:
        *.tscn.tsv  (extract_tscn_text.py 출력, unique_id 있음)
        *.tres.tsv  (extract_tres_text.py 출력, unique_id 없음 → 자연 스킵)
    """
    index = {}
    tsv_files = sorted(tsv_dir.rglob("*.tscn.tsv")) + sorted(tsv_dir.rglob("*.tres.tsv"))
    for tsv_file in tsv_files:
        try:
            with open(tsv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    uid = (row.get("unique_id") or "").strip()
                    if not uid:
                        continue
                    record = {
                        "filename": (row.get("filename") or "").strip(),
                        "filetype": (row.get("filetype") or "").strip(),
                        "location": (row.get("location") or "").strip(),
                        "parent": (row.get("parent") or "").strip(),
                        "name": (row.get("name") or "").strip(),
                        "type": (row.get("type") or "").strip(),
                        "text": row.get("text") or "",
                        "_tsv_file": tsv_file.name,
                    }
                    index.setdefault(uid, []).append(record)
        except Exception as e:
            print(f"[WARN] TSV 읽기 실패: {tsv_file} ({e})")
    return index


def load_tres_text_set(tsv_dir: Path) -> set:
    """
    추출된 *.tres.tsv 에서 모든 text 값을 set 으로 수집.
    tres xlsx 행의 text 가 실제 .tres 소스에 존재하는지 검증하는 데 사용.
    """
    texts: set = set()
    for tsv_file in sorted(tsv_dir.rglob("*.tres.tsv")):
        try:
            with open(tsv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    text = row.get("text") or ""
                    if text:
                        texts.add(text)
        except Exception as e:
            print(f"[WARN] tres TSV 읽기 실패: {tsv_file} ({e})")
    return texts


def load_gd_text_set(tsv_dir: Path) -> set:
    """
    추출된 *.gd.tsv 에서 모든 text 값을 set 으로 수집.
    filetype=gd xlsx 행의 text 가 실제 .gd 소스에 존재하는지 검증하는 데 사용.
    """
    texts: set = set()
    for tsv_file in sorted(tsv_dir.rglob("*.gd.tsv")):
        try:
            with open(tsv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    text = row.get("text") or ""
                    if text:
                        texts.add(text)
        except Exception as e:
            print(f"[WARN] gd TSV 읽기 실패: {tsv_file} ({e})")
    return texts


# ==========================================
# MetaData 로딩
# ==========================================

def load_metadata(xlsx_path: Path) -> dict:
    """
    MetaData 시트에서 Field → Value 딕셔너리를 반환.
    MetaData 시트가 없으면 빈 dict.
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    try:
        if "MetaData" not in wb.sheetnames:
            return {}
        ws = wb["MetaData"]
        rows_iter = ws.iter_rows(values_only=True)
        header = next(rows_iter, None)
        if header is None:
            return {}
        meta: dict = {}
        for row in rows_iter:
            if row is None or len(row) < 3:
                continue
            field = _normalize_cell(row[1])
            value = _normalize_cell(row[2])
            if field:
                meta[field] = value
        return meta
    finally:
        wb.close()


def format_metadata_lines(meta: dict) -> list[str]:
    """메타데이터를 로그 출력용 문자열 리스트로 반환."""
    lines = []
    for key in ("Game Version", "Game Updated Date", "Translation Updated Date",
                "Translation Updated Time", "Translation UTC", "Translator"):
        val = meta.get(key, "")
        if val:
            lines.append(f"  {key}: {val}")
    return lines


# ==========================================
# xlsx 로딩
# ==========================================

def load_xlsx_main(xlsx_path: Path, sheet_name: str = "Main") -> tuple[list[str], list[dict], str]:
    """
    Translation.xlsx 의 지정 시트를 읽어 (헤더, 행 리스트, 시트 이름) 반환.
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"'{sheet_name}' 시트가 없습니다: {wb.sheetnames}")
    ws = wb[sheet_name]

    rows_iter = ws.iter_rows(values_only=True)
    header = []
    for c in next(rows_iter):
        h = _normalize_cell(c)
        h = h.replace("\r", " ").replace("\n", " ")
        h = " ".join(h.split())
        header.append(h)

    rows = []
    for row_values in rows_iter:
        if row_values is None or all(v is None for v in row_values):
            continue
        row_dict = {}
        for i, key in enumerate(header):
            val = row_values[i] if i < len(row_values) else None
            # 동일 컬럼명이 여러 번이면 첫 번째만 사용 (뒤는 버림)
            if key not in row_dict:
                row_dict[key] = _normalize_cell(val)
        rows.append(row_dict)

    wb.close()
    return header, rows, sheet_name


def load_all_translation_sheets(xlsx_path: Path) -> list[tuple[str, list[str], list[dict]]]:
    """
    MetaData 를 제외한 모든 시트를 로드해 (sheet_name, header, rows) 튜플 리스트로 반환.
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    try:
        result = []
        for sheet_name in wb.sheetnames:
            if sheet_name in SKIP_SHEETS:
                continue
            ws = wb[sheet_name]
            rows_iter = ws.iter_rows(values_only=True)
            header_raw = next(rows_iter, None)
            if header_raw is None:
                continue
            header = []
            for c in header_raw:
                h = _normalize_cell(c)
                h = h.replace("\r", " ").replace("\n", " ")
                h = " ".join(h.split())
                header.append(h)

            rows: list[dict] = []
            for row_values in rows_iter:
                if row_values is None or all(v is None for v in row_values):
                    continue
                row_dict = {"_sheet": sheet_name}
                for i, key in enumerate(header):
                    val = row_values[i] if i < len(row_values) else None
                    if key not in row_dict:
                        row_dict[key] = _normalize_cell(val)
                rows.append(row_dict)
            result.append((sheet_name, header, rows))
        return result
    finally:
        wb.close()


# ==========================================
# 개별 체크
# ==========================================

def check_tsv_match(row: dict, tsv_index: dict) -> list[str]:
    """
    체크 2 (ERROR): method=static 행에 한해 TSV 매칭.
    filetype in {tscn, scn} 이어야 하며 unique_id 로 추출 인덱스에서 대조.
    text 는 앞뒤 공백/개행까지 완전 일치 (엄격).
    """
    errors = []
    method = _effective_method(row)
    if method != "static":
        return errors  # static 만 TSV 검증 대상

    filetype = row.get("filetype", "").strip()
    if filetype not in SCENE_FILETYPES:
        return errors  # 검증 불가 (소스가 tscn/scn 이 아님)

    uid = row.get("unique_id", "").strip()
    if not uid:
        errors.append("static: unique_id 비어있음")
        return errors

    candidates = tsv_index.get(uid)
    if not candidates:
        errors.append(f"static: unique_id={uid} 가 추출 TSV 에 없음")
        return errors

    # 후보가 여러 개면 text 일치 우선 선택 (씬 간 uid 중복 대비)
    xlsx_text = row.get("text", "")
    best = None
    for cand in candidates:
        if cand["text"] == xlsx_text:
            best = cand
            break
    if best is None:
        best = candidates[0]

    mismatches = []
    # 비교 대상 필드 (xlsx → TSV 필드명)
    field_map = [
        ("filename", "filename"),
        ("filetype", "filetype"),
        ("location", "location"),
        ("parent", "parent"),
        ("name", "name"),
        ("type", "type"),
    ]
    for xlsx_key, tsv_key in field_map:
        xlsx_val = row.get(xlsx_key, "").strip()
        tsv_val = best.get(tsv_key, "").strip()
        if xlsx_val != tsv_val:
            mismatches.append(
                f"{xlsx_key}: xlsx={_preview(xlsx_val)} / tsv={_preview(tsv_val)}"
            )

    # text 는 엄격 비교 (공백/개행 포함)
    if xlsx_text != best["text"]:
        mismatches.append(
            f"text: xlsx={_preview(xlsx_text)} / tsv={_preview(best['text'])}"
        )

    if mismatches:
        errors.append(
            f"unique_id={uid} ({best['_tsv_file']}) 필드 불일치: " + "; ".join(mismatches)
        )

    return errors


def check_tres_text(row: dict, tres_texts: set) -> list[str]:
    """
    체크 2b (ERROR): filetype=tres 행의 text 가 추출된 .tres.tsv 에 존재하는지 검증.
    method=static 이 아닌 행 중 filetype=tres 인 것만 대상. 오타/유령 엔트리 방지.
    """
    errors = []
    filetype = row.get("filetype", "").strip()
    if filetype != "tres":
        return errors
    effective = _effective_method(row)
    if effective == "ignore":
        return errors

    text = row.get("text", "")
    if text and text not in tres_texts:
        filename = row.get("filename", "").strip()
        errors.append(
            f"filetype=tres 의 text 가 추출된 .tres.tsv 에 없음: "
            f"filename={filename!r}, text={_preview(text, 40)}"
        )
    return errors


def check_gd_text(row: dict, gd_texts: set) -> list[str]:
    """
    체크 2c (WARNING): filetype=gd 행의 text 가 추출된 .gd.tsv 에 존재하는지 검증.
    GD 추출은 휴리스틱 기반이라 ERROR 가 아닌 WARNING.
    """
    warnings = []
    filetype = row.get("filetype", "").strip()
    if filetype != "gd":
        return warnings
    effective = _effective_method(row)
    if effective == "ignore":
        return warnings

    text = row.get("text", "")
    if text and text not in gd_texts:
        filename = row.get("filename", "").strip()
        warnings.append(
            f"filetype=gd 의 text 가 추출된 .gd.tsv 에 없음 (변경/삭제?): "
            f"filename={filename!r}, text={_preview(text, 40)}"
        )
    return warnings


def check_whitespace(row: dict) -> list[str]:
    """체크 3 (WARNING): text ↔ translation 앞뒤 공백/개행 매칭."""
    warnings = []
    text = row.get("text", "")
    translation = row.get("translation", "")

    if not translation:
        return warnings

    text_lead = _leading_ws(text)
    trans_lead = _leading_ws(translation)
    if text_lead != trans_lead:
        warnings.append(
            f"앞 공백 불일치: text={_preview(text_lead)} / translation={_preview(trans_lead)}"
        )

    text_trail = _trailing_ws(text)
    trans_trail = _trailing_ws(translation)
    if text_trail != trans_trail:
        warnings.append(
            f"뒤 공백 불일치: text={_preview(text_trail)} / translation={_preview(trans_trail)}"
        )

    return warnings


def check_flags(row: dict) -> list[str]:
    """체크 4 (ERROR): 플래그 컬럼 값 검증. 빈 값 허용."""
    errors = []
    for col in FLAG_COLUMNS:
        val = row.get(col, "")
        normalized = val.strip().lower()
        if normalized not in VALID_FLAGS:
            errors.append(f"{col} 값이 잘못됨: {val!r} (허용: 0/1/true/false 또는 빈값)")
    return errors


def check_method_fields(row: dict) -> list[str]:
    """
    체크 5 (ERROR): method 값과 관련 필드 조합 검증.
    """
    errors = []
    method = row.get("method", "").strip()
    location = row.get("location", "").strip()
    filetype = row.get("filetype", "").strip()
    parent = row.get("parent", "").strip()
    name = row.get("name", "").strip()
    type_ = row.get("type", "").strip()
    unique_id = row.get("unique_id", "").strip()

    if method not in VALID_METHODS:
        errors.append(f"알 수 없는 method: {method!r} (허용: static/literal/pattern/substr/ignore 또는 빈값)")
        return errors

    effective = method if method else "literal"

    if effective == "ignore":
        return errors  # ignore 행은 필드 조합 검증 스킵

    if effective == "static":
        if not location:
            errors.append("static: location 필수")
        if filetype not in SCENE_FILETYPES:
            errors.append(
                f"static: filetype 은 'tscn' 또는 'scn' 이어야 함 (현재: {filetype!r})"
            )
        if not parent and not name:
            # parent 가 비어도 루트 노드면 OK. 다만 parent+name 둘 다 비면 이상.
            pass
        if not name:
            errors.append("static: name 필수")
        # type 은 instance 노드(.tscn 에 type= 미기록)에선 빈값이 정상. TSV 일치로 검증됨.
        if not unique_id:
            errors.append("static: unique_id 필수")

    elif effective == "literal":
        if location:
            # scoped literal: 컨텍스트 필드 필수 (type 제외, instance 노드 대응)
            if not name:
                errors.append("scoped literal: name 필수 (literal + location)")
        # 전역 literal 은 text 외 제약 없음

    elif effective == "pattern":
        if location:
            # scoped pattern: 컨텍스트 필드 필수 (type 제외)
            if not name:
                errors.append("scoped pattern: name 필수 (pattern + location)")
        # 전역 pattern 은 text(정규식) 외 제약 없음

    elif effective == "substr":
        # substr 은 text + translation 만 필수. 전역 부분 문자열 치환.
        pass

    return errors


def check_empty_method(row: dict) -> list[str]:
    """체크 6 (WARNING): 빈 method + unique_id 채워짐 → static 명시 권장."""
    warnings = []
    method = row.get("method", "").strip()
    if method:
        return warnings
    uid = row.get("unique_id", "").strip()
    if uid:
        warnings.append(
            "method 가 비어있는데 unique_id 가 채워져 있음 — static 을 명시하세요"
        )
    return warnings


def check_duplicates(rows: list[dict]) -> list[tuple[int, str]]:
    """
    체크 7 (ERROR): 런타임 매칭 키 중복.
    - static 과 scoped literal 은 동일한 5-tuple 키 공간에서 충돌 (런타임 동작 동일)
    - 전역 literal: text
    - scoped pattern: 5-tuple
    - 전역 pattern: text
    ignore=1 은 제외.
    """
    errors = []
    exact_keys: dict[tuple, list] = {}         # static + scoped literal
    literal_global: dict[str, list] = {}
    scoped_pattern_keys: dict[tuple, list] = {}
    pattern_global: dict[str, list] = {}
    substr_global: dict[str, list] = {}

    for i, row in enumerate(rows, start=2):
        effective = _effective_method(row)
        untranslatable = row.get("untranslatable", "").strip().lower() in {"1", "true"}
        if effective == "ignore" or untranslatable:
            continue

        text = row.get("text", "")
        location = row.get("location", "").strip()

        key_5 = (
            location,
            row.get("parent", "").strip(),
            row.get("name", "").strip(),
            row.get("type", "").strip(),
            text,
        )

        if effective == "static":
            exact_keys.setdefault(key_5, []).append((i, row))
        elif effective == "literal":
            if location:
                exact_keys.setdefault(key_5, []).append((i, row))
            else:
                literal_global.setdefault(text, []).append((i, row))
        elif effective == "pattern":
            if location:
                scoped_pattern_keys.setdefault(key_5, []).append((i, row))
            else:
                pattern_global.setdefault(text, []).append((i, row))
        elif effective == "substr":
            substr_global.setdefault(text, []).append((i, row))

    def _emit(label: str, store: dict, is_tuple_key: bool):
        for key, occurrences in store.items():
            if len(occurrences) <= 1:
                continue
            row_nums = ", ".join(str(n) for n, _ in occurrences)
            if is_tuple_key:
                loc, parent, name, type_, text = key
                text_preview = _preview(text, 40)
                msg = (
                    f"{label} ({len(occurrences)}개): "
                    f"location={loc!r}, parent={parent!r}, name={name!r}, type={type_!r}, "
                    f"text={text_preview} (행: {row_nums})"
                )
            else:
                text_preview = _preview(key, 40)
                msg = (
                    f"{label} ({len(occurrences)}개): "
                    f"text={text_preview} (행: {row_nums})"
                )
            for row_num, _ in occurrences:
                errors.append((row_num, msg))

    _emit("exact 매칭 중복 (static/scoped literal)", exact_keys, True)
    _emit("전역 literal 중복", literal_global, False)
    _emit("scoped pattern 중복", scoped_pattern_keys, True)
    _emit("전역 pattern 중복", pattern_global, False)
    _emit("전역 substr 중복", substr_global, False)

    return errors


def check_duplicates_cross_sheet(
    sheets: list[tuple[str, list, list[dict]]],
) -> list[tuple[str, int, str]]:
    """
    체크 7b (ERROR): 시트 간 중복 키 검사.
    시트 내 중복은 check_duplicates 가 담당. 이 함수는 서로 다른 시트에
    걸쳐 같은 런타임 키가 등장할 때만 보고한다.
    반환: [(sheet_name, row_num, msg), ...]
    """
    errors: list[tuple[str, int, str]] = []
    exact_keys: dict[tuple, list] = {}
    literal_global: dict[str, list] = {}
    scoped_pattern_keys: dict[tuple, list] = {}
    pattern_global: dict[str, list] = {}
    substr_global: dict[str, list] = {}

    for sheet_name, _header, rows in sheets:
        for i, row in enumerate(rows, start=2):
            effective = _effective_method(row)
            untranslatable = row.get("untranslatable", "").strip().lower() in {"1", "true"}
            if effective == "ignore" or untranslatable:
                continue

            text = row.get("text", "")
            location = row.get("location", "").strip()
            key_5 = (
                location,
                row.get("parent", "").strip(),
                row.get("name", "").strip(),
                row.get("type", "").strip(),
                text,
            )

            if effective == "static":
                exact_keys.setdefault(key_5, []).append((sheet_name, i, row))
            elif effective == "literal":
                if location:
                    exact_keys.setdefault(key_5, []).append((sheet_name, i, row))
                else:
                    literal_global.setdefault(text, []).append((sheet_name, i, row))
            elif effective == "pattern":
                if location:
                    scoped_pattern_keys.setdefault(key_5, []).append((sheet_name, i, row))
                else:
                    pattern_global.setdefault(text, []).append((sheet_name, i, row))
            elif effective == "substr":
                substr_global.setdefault(text, []).append((sheet_name, i, row))

    def _emit(label: str, store: dict, is_tuple_key: bool):
        for key, occurrences in store.items():
            sheet_set = {sn for sn, _, _ in occurrences}
            if len(occurrences) <= 1 or len(sheet_set) <= 1:
                # 시트 내 중복은 check_duplicates 가 처리
                continue
            locs = ", ".join(f"{sn}:{n}" for sn, n, _ in occurrences)
            if is_tuple_key:
                loc, parent, name, type_, text = key
                text_preview = _preview(text, 40)
                msg = (
                    f"{label} (시트간, {len(occurrences)}개): "
                    f"location={loc!r}, parent={parent!r}, name={name!r}, type={type_!r}, "
                    f"text={text_preview} [{locs}]"
                )
            else:
                text_preview = _preview(key, 40)
                msg = (
                    f"{label} (시트간, {len(occurrences)}개): "
                    f"text={text_preview} [{locs}]"
                )
            for sn, row_num, _ in occurrences:
                errors.append((sn, row_num, msg))

    _emit("exact 매칭 중복 (static/scoped literal)", exact_keys, True)
    _emit("전역 literal 중복", literal_global, False)
    _emit("scoped pattern 중복", scoped_pattern_keys, True)
    _emit("전역 pattern 중복", pattern_global, False)
    _emit("전역 substr 중복", substr_global, False)

    return errors


# ==========================================
# 출력 (Tee)
# ==========================================

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
    """검증 결과. error_count 가 0 이면 통과."""

    def __init__(self):
        self.error_tsv = 0
        self.error_flags = 0
        self.error_dup = 0
        self.error_method = 0
        self.warn_ws = 0
        self.warn_empty_method = 0
        self.warn_tsv_soft = 0
        self.log_path: Path | None = None

    @property
    def error_count(self) -> int:
        return (
            self.error_tsv + self.error_flags + self.error_dup + self.error_method
        )

    @property
    def warning_count(self) -> int:
        return self.warn_ws + self.warn_empty_method + self.warn_tsv_soft

    @property
    def ok(self) -> bool:
        return self.error_count == 0


# ==========================================
# 검증 실행
# ==========================================

REQUIRED_COLUMNS = [
    "method", "filename", "filetype", "location",
    "parent", "name", "type", "unique_id",
    "text", "translation",
    "Transliteration", "Machine translated", "Confused", "untranslatable",
]


def validate_xlsx(xlsx_path: Path, tsv_dir: Path, soft: bool = False) -> ValidationResult:
    """
    Translation.xlsx 의 모든 번역 시트 (MetaData 제외) 를 검증.

    soft=False (--hard, 기본): TSV 매칭 실패 → ERROR (빌드 차단)
    soft=True  (--soft):       TSV 매칭 실패 → WARNING (빌드 계속, 해당 행 제외)
    """
    result = ValidationResult()

    if not xlsx_path.exists():
        raise FileNotFoundError(f"xlsx 파일이 없습니다: {xlsx_path}")
    if not tsv_dir.exists():
        raise FileNotFoundError(
            f"TSV 디렉토리가 없습니다: {tsv_dir}\n먼저 extract_tscn_text.py 를 실행하세요."
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = xlsx_path.parent / ".log" / f"validate_translation_{timestamp}.log"
    result.log_path = log_path
    tee = Tee(log_path)

    try:
        tee.print(f"검증 대상: {xlsx_path}")
        tee.print(f"TSV 소스:  {tsv_dir}")
        tee.print(f"로그 파일: {log_path}")
        tee.print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        meta = load_metadata(xlsx_path)
        for line in format_metadata_lines(meta):
            tee.print(line)
        tee.print()

        tee.print("TSV 인덱스 빌드 중...")
        tsv_index = load_tsv_index(tsv_dir)
        total_tsv_entries = sum(len(v) for v in tsv_index.values())
        tee.print(f"  unique_id 수: {len(tsv_index)}, 총 레코드: {total_tsv_entries}")

        tres_texts = load_tres_text_set(tsv_dir)
        gd_texts = load_gd_text_set(tsv_dir)
        tee.print(f"  tres text 수: {len(tres_texts)}, gd text 수: {len(gd_texts)}")

        tee.print("Translation.xlsx 로드 중...")
        sheets = load_all_translation_sheets(xlsx_path)
        if not sheets:
            tee.print("[ERROR] 번역 시트가 없습니다 (MetaData 외 시트 없음)")
            raise ValueError("번역 시트 없음")
        total_row_count = sum(len(rows) for _, _, rows in sheets)
        tee.print(f"  시트 {len(sheets)}개, 총 데이터 행 {total_row_count}개")
        for sheet_name, _, rows in sheets:
            tee.print(f"    {sheet_name}: {len(rows)}행")
        tee.print()

        for sheet_name, header, rows in sheets:
            missing = [c for c in REQUIRED_COLUMNS if c not in header]
            if missing:
                tee.print(f"[ERROR] [{sheet_name}] 필수 컬럼 누락: {missing}")
                tee.print(f"  실제 헤더: {header}")
                raise ValueError(f"[{sheet_name}] 필수 컬럼 누락: {missing}")

            # 시트별 중복 키 검사를 위해 행 수집
            issues_by_row: dict = {}

            for i, row in enumerate(rows, start=2):
                local_issues = []

                for msg in check_tsv_match(row, tsv_index):
                    if soft:
                        local_issues.append(("WARN", "TSV 매칭 (soft)", msg))
                        result.warn_tsv_soft += 1
                    else:
                        local_issues.append(("ERROR", "TSV 매칭", msg))
                        result.error_tsv += 1

                for msg in check_tres_text(row, tres_texts):
                    if soft:
                        local_issues.append(("WARN", "tres 매칭 (soft)", msg))
                        result.warn_tsv_soft += 1
                    else:
                        local_issues.append(("ERROR", "tres 매칭", msg))
                        result.error_tsv += 1

                for msg in check_gd_text(row, gd_texts):
                    local_issues.append(("WARN", "gd 매칭", msg))
                    result.warn_tsv_soft += 1

                for msg in check_whitespace(row):
                    local_issues.append(("WARN", "공백", msg))
                    result.warn_ws += 1

                for msg in check_flags(row):
                    local_issues.append(("ERROR", "플래그", msg))
                    result.error_flags += 1

                for msg in check_method_fields(row):
                    local_issues.append(("ERROR", "method", msg))
                    result.error_method += 1

                for msg in check_empty_method(row):
                    local_issues.append(("WARN", "빈 method", msg))
                    result.warn_empty_method += 1

                if local_issues:
                    issues_by_row.setdefault(i, []).extend(local_issues)

            # 시트 내 중복 키 검사
            for row_num, msg in check_duplicates(rows):
                issues_by_row.setdefault(row_num, []).append(("ERROR", "중복 키", msg))
                result.error_dup += 1

            if issues_by_row:
                tee.print(f"[{sheet_name}]")
                for i in sorted(issues_by_row.keys()):
                    row = rows[i - 2]
                    text_preview = _preview(row.get("text", ""), 60)
                    tee.print(f"  Row {i}: text={text_preview}")
                    for level, label, msg in issues_by_row[i]:
                        tee.print(f"    [{level}] {label}: {msg}")
                tee.print()

        # 시트 간 중복 키 검사 (같은 런타임 키가 여러 시트에 걸쳐 존재)
        cross_dup_by_sheet: dict = {}
        for sn, row_num, msg in check_duplicates_cross_sheet(sheets):
            cross_dup_by_sheet.setdefault(sn, {}).setdefault(row_num, []).append(msg)
            result.error_dup += 1
        if cross_dup_by_sheet:
            tee.print("[시트간 중복]")
            sheet_rows_map = {sn: rows for sn, _, rows in sheets}
            for sn in sorted(cross_dup_by_sheet.keys()):
                tee.print(f"  [{sn}]")
                for i in sorted(cross_dup_by_sheet[sn].keys()):
                    row = sheet_rows_map[sn][i - 2]
                    text_preview = _preview(row.get("text", ""), 60)
                    tee.print(f"    Row {i}: text={text_preview}")
                    for msg in cross_dup_by_sheet[sn][i]:
                        tee.print(f"      [ERROR] 중복 키: {msg}")
            tee.print()

        tee.print("=" * 60)
        tee.print(f"검증 완료: {total_row_count}행 검사 (mode={'soft' if soft else 'hard'})")
        tee.print(
            f"  ERROR {result.error_count}개  "
            f"(TSV 매칭 {result.error_tsv}, 플래그 {result.error_flags}, "
            f"중복 키 {result.error_dup}, method {result.error_method})"
        )
        tee.print(
            f"  WARN  {result.warning_count}개  "
            f"(공백 {result.warn_ws}, 빈 method {result.warn_empty_method}"
            f"{f', TSV soft {result.warn_tsv_soft}' if result.warn_tsv_soft else ''})"
        )

        return result
    finally:
        tee.close()


def main() -> int:
    # --soft / --hard 파싱
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    soft = "--soft" in flags

    if not args:
        print("사용법: python validate_translation.py <locale> [--soft|--hard]")
        print("  --hard (기본): TSV 매칭 실패 → ERROR (빌드 차단)")
        print("  --soft:        TSV 매칭 실패 → WARNING (빌드 계속)")
        print("예: python validate_translation.py Korean --soft")
        return 1

    locale = args[0]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    xlsx_path = (mod_root / locale / "Translation.xlsx").resolve()
    tsv_dir = (mod_root / ".tmp" / "extracted_text").resolve()

    if not xlsx_path.exists():
        print(f"[ERROR] xlsx 파일이 없습니다: {xlsx_path}")
        return 1

    try:
        result = validate_xlsx(xlsx_path, tsv_dir, soft=soft)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        return 1

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
