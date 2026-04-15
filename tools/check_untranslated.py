"""
추출된 TSV 와 Translation.xlsx 를 비교해 번역 커버리지를 리포트한다.

매칭 분류:
- direct:      xlsx 의 static 또는 scoped literal 행이 5-tuple 로 매칭 (번역 완료)
- literal:     xlsx 의 전역 literal 행이 text 로 매칭 (fallback 번역)
- expression:  xlsx 의 전역 pattern 행 정규식이 text 와 매칭 (fallback 번역)
- ignored:     xlsx 에 있고 ignore=1 (의도적 제외, 미번역 아님)
- empty:       xlsx 에 있지만 translation 비어있음 (번역 대기)
- missing:     xlsx 에 아예 없음 (새로 추가 필요)

사용법:
    python check_untranslated.py <locale>

예시:
    python check_untranslated.py Korean

출력:
    화면 + <locale>/.log/check_untranslated_YYYYMMDD_HHMMSS.log
"""
import csv
import re
import sys
from collections import defaultdict
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
    Tee,
)


IGNORE_VALUES = {"1", "true"}


# ==========================================
# 패턴 컴파일 (translator.gd 와 동일 로직)
# ==========================================

def compile_pattern(text: str) -> re.Pattern:
    """{name} 과 * 를 지원하는 패턴을 Python 정규식으로 컴파일."""
    placeholder_re = re.compile(r"\{(\w+)\}")
    result = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == "{":
            m = placeholder_re.match(text, i)
            if m:
                name = m.group(1)
                result.append(f"(?P<{name}>.+?)")
                i = m.end()
                continue
        if c == "*":
            result.append("(?:.+?)")
            i += 1
            continue
        if c in r"\.^$+?()[]|{}":
            result.append("\\" + c)
        else:
            result.append(c)
        i += 1
    return re.compile("^" + "".join(result) + "$")


# ==========================================
# 추출 TSV 로드
# ==========================================

def load_tsv_entries(tsv_dir: Path) -> list[dict]:
    """
    extracted_text/ 의 이중 확장자 TSV 파일을 로드.

    대상:
        *.tscn.tsv  — unique_id 있는 scn 엔트리
        *.tres.tsv  — unique_id 없는 tres 엔트리
    """
    entries = []
    tsv_files = sorted(tsv_dir.rglob("*.tscn.tsv")) + sorted(tsv_dir.rglob("*.tres.tsv"))
    for tsv_file in tsv_files:
        try:
            with open(tsv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    text = row.get("text") or ""
                    if not text:
                        continue
                    filetype = (row.get("filetype") or "").strip()
                    uid = (row.get("unique_id") or "").strip()
                    # tscn 엔트리는 uid 필수, tres 는 없음 허용
                    if filetype == "tscn" and not uid:
                        continue
                    entries.append({
                        "unique_id": uid,
                        "filename": (row.get("filename") or "").strip(),
                        "filetype": filetype,
                        "location": (row.get("location") or "").strip(),
                        "parent": (row.get("parent") or "").strip(),
                        "name": (row.get("name") or "").strip(),
                        "type": (row.get("type") or "").strip(),
                        "text": text,
                        "_tsv_file": tsv_file.name,
                    })
        except Exception as e:
            print(f"[WARN] TSV 읽기 실패: {tsv_file} ({e})")
    return entries


# ==========================================
# xlsx 분석 (새 스키마: method / translation)
# ==========================================

def analyze_xlsx(rows: list[dict]) -> tuple[dict, dict, dict, dict, list]:
    """
    xlsx 행을 런타임 매칭 모델에 맞춰 인덱싱.

    반환:
      - direct_keys:   { (location, parent, name, type, text): translation } — static + scoped literal
      - ignored_keys:  set of 5-tuples (ignore=1 행)
      - empty_keys:    set of 5-tuples (xlsx 에 있지만 translation 비어있음)
      - literal_map:   {text: translation} — 전역 literal
      - pattern_list:  [(compiled_regex, template), ...] — 전역 pattern
    """
    direct_keys: dict = {}
    ignored_keys: set = set()
    empty_keys: set = set()
    literal_map: dict = {}
    pattern_list: list = []

    for row in rows:
        ignore = row.get("ignore", "").strip().lower()
        translation = row.get("translation", "")
        text = row.get("text", "")
        location = row.get("location", "").strip()
        parent = row.get("parent", "").strip()
        name = row.get("name", "").strip()
        type_ = row.get("type", "").strip()
        effective = _effective_method(row)

        key_5 = (location, parent, name, type_, text)

        if ignore in IGNORE_VALUES:
            # 전역 literal/pattern 은 5-tuple 이 무의미하므로 별도 기록 X
            if effective in ("static",) or (effective == "literal" and location):
                ignored_keys.add(key_5)
            continue

        if effective == "static":
            if translation:
                direct_keys[key_5] = translation
            else:
                empty_keys.add(key_5)

        elif effective == "literal":
            if location:
                # scoped literal — direct 키 공간
                if translation:
                    direct_keys[key_5] = translation
                else:
                    empty_keys.add(key_5)
            else:
                # 전역 literal
                if translation:
                    literal_map[text] = translation

        elif effective == "pattern":
            if location:
                # scoped pattern 은 현재 리포트 모델에서 전역 pattern 과 동일 취급
                if translation:
                    try:
                        regex = compile_pattern(text)
                        pattern_list.append((regex, translation))
                    except re.error:
                        pass
            else:
                if translation:
                    try:
                        regex = compile_pattern(text)
                        pattern_list.append((regex, translation))
                    except re.error:
                        pass

    return direct_keys, ignored_keys, empty_keys, literal_map, pattern_list


# ==========================================
# TSV 엔트리 분류
# ==========================================

def classify_entry(
    entry: dict,
    direct_keys: dict,
    ignored_keys: set,
    empty_keys: set,
    literal_map: dict,
    pattern_list: list,
) -> tuple[str, str]:
    """
    TSV 엔트리의 번역 상태를 분류.
    반환: (status, method)
        status: "direct" | "ignored" | "literal" | "expression" | "empty" | "missing"
    """
    text = entry["text"]
    filetype = entry.get("filetype", "")

    # tscn 엔트리는 5-tuple 로 우선 조회
    if filetype == "tscn":
        key_5 = (
            entry["location"],
            entry["parent"],
            entry["name"],
            entry["type"],
            text,
        )
        if key_5 in ignored_keys:
            return ("ignored", "")
        if key_5 in direct_keys:
            return ("direct", "")
        if key_5 in empty_keys:
            # text-only fallback 이 있으면 그걸 쓰지만, 리포트는 empty 우선
            return ("empty", "")

    # tres 또는 5-tuple 매칭 실패 → text-only fallback
    if text in literal_map:
        return ("literal", "literal")

    for regex, _tmpl in pattern_list:
        if regex.match(text):
            return ("expression", f"pattern: {regex.pattern}")

    return ("missing", "")


# ==========================================
# 메인
# ==========================================

def format_percent(n: int, total: int) -> str:
    if total == 0:
        return "-"
    return f"{n / total * 100:.1f}%"


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: python check_untranslated.py <locale>")
        print("예: python check_untranslated.py Korean")
        return 1

    locale = sys.argv[1]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    locale_dir = mod_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"
    tsv_dir = mod_root / ".tmp" / "extracted_text"

    if not xlsx_path.exists():
        print(f"[ERROR] xlsx 파일이 없습니다: {xlsx_path}")
        return 1
    if not tsv_dir.exists():
        print(f"[ERROR] TSV 디렉토리가 없습니다: {tsv_dir}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = locale_dir / ".log" / f"check_untranslated_{timestamp}.log"
    tee = Tee(log_path)

    try:
        tee.print(f"xlsx:   {xlsx_path}")
        tee.print(f"TSV:    {tsv_dir}")
        tee.print(f"로그:   {log_path}")
        tee.print(f"실행:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        tee.print()

        # 1. xlsx 로드 및 분석 (모든 번역 시트 병합)
        tee.print("xlsx 로드 중...")
        sheets = load_all_translation_sheets(xlsx_path)
        all_rows: list[dict] = []
        for sheet_name, _header, rows in sheets:
            all_rows.extend(rows)
        tee.print(f"  시트 {len(sheets)}개, 총 {len(all_rows)}행")

        (
            direct_keys,
            ignored_keys,
            empty_keys,
            literal_map,
            pattern_list,
        ) = analyze_xlsx(all_rows)
        tee.print(
            f"  → direct {len(direct_keys)}개, "
            f"ignored {len(ignored_keys)}개, "
            f"empty {len(empty_keys)}개, "
            f"literal {len(literal_map)}개, "
            f"pattern {len(pattern_list)}개"
        )
        tee.print()

        # 2. 추출 TSV 로드
        tee.print("추출 TSV 로드 중...")
        tsv_entries = load_tsv_entries(tsv_dir)
        tee.print(f"  {len(tsv_entries)}개 엔트리")
        tee.print()

        # 3. 분류
        per_file: dict = defaultdict(lambda: {
            "total": 0,
            "direct": 0,
            "literal": 0,
            "expression": 0,
            "ignored": 0,
            "empty": 0,
            "missing": 0,
            "empty_entries": [],
            "missing_entries": [],
            "fallback_entries": [],
        })

        for entry in tsv_entries:
            fname = entry["_tsv_file"]
            status, method = classify_entry(
                entry, direct_keys, ignored_keys, empty_keys, literal_map, pattern_list
            )
            bucket = per_file[fname]
            bucket["total"] += 1
            if status == "direct":
                bucket["direct"] += 1
            elif status == "literal":
                bucket["literal"] += 1
                bucket["fallback_entries"].append((entry, method))
            elif status == "expression":
                bucket["expression"] += 1
                bucket["fallback_entries"].append((entry, method))
            elif status == "ignored":
                bucket["ignored"] += 1
            elif status == "empty":
                bucket["empty"] += 1
                bucket["empty_entries"].append(entry)
            else:
                bucket["missing"] += 1
                bucket["missing_entries"].append(entry)

        # 4. 파일별 요약
        tee.print("=" * 80)
        tee.print("파일별 요약 (ignored 제외 유효 엔트리 기준)")
        tee.print("=" * 80)

        file_names = sorted(per_file.keys())
        max_fname = max((len(n) for n in file_names), default=20)

        total_all = 0
        effective_all = 0
        direct_all = 0
        fallback_all = 0
        ignored_all = 0
        empty_all = 0
        missing_all = 0

        for fname in file_names:
            b = per_file[fname]
            total = b["total"]
            direct = b["direct"]
            fallback = b["literal"] + b["expression"]
            ignored = b["ignored"]
            empty = b["empty"]
            missing = b["missing"]

            effective = total - ignored
            translation_count = direct + fallback

            total_all += total
            effective_all += effective
            direct_all += direct
            fallback_all += fallback
            ignored_all += ignored
            empty_all += empty
            missing_all += missing

            tee.print(
                f"[{fname:<{max_fname}}] "
                f"번역 {translation_count}/{effective} ({format_percent(translation_count, effective)}), "
                f"직접 {direct}/{effective} ({format_percent(direct, effective)}), "
                f"fallback {fallback}, "
                f"ignored {ignored}"
            )

        tee.print()
        tee.print(
            f"[전체] "
            f"번역 {direct_all + fallback_all}/{effective_all} "
            f"({format_percent(direct_all + fallback_all, effective_all)}), "
            f"직접 {direct_all}/{effective_all} ({format_percent(direct_all, effective_all)}), "
            f"fallback {fallback_all}, "
            f"ignored {ignored_all}, "
            f"empty {empty_all}, "
            f"missing {missing_all}"
        )
        tee.print()

        # 5. 파일별 상세
        tee.print("=" * 80)
        tee.print("파일별 상세")
        tee.print("=" * 80)

        for fname in file_names:
            b = per_file[fname]
            if (
                b["missing"] == 0
                and b["empty"] == 0
                and len(b["fallback_entries"]) == 0
            ):
                continue

            tee.print()
            tee.print(f"[{fname}]")

            if b["missing_entries"]:
                tee.print(f"  missing - xlsx에 없음 ({b['missing']}개):")
                for e in b["missing_entries"]:
                    tee.print(
                        f"    uid={e['unique_id']}  "
                        f"name={e['name']}  "
                        f"type={e['type']}  "
                        f"text={_preview(e['text'], 50)}"
                    )

            if b["empty_entries"]:
                tee.print(f"  empty - xlsx에 있지만 미번역 ({b['empty']}개):")
                for e in b["empty_entries"]:
                    tee.print(
                        f"    uid={e['unique_id']}  "
                        f"name={e['name']}  "
                        f"type={e['type']}  "
                        f"text={_preview(e['text'], 50)}"
                    )

            if b["fallback_entries"]:
                tee.print(
                    f"  fallback - literal/pattern 으로 매칭 "
                    f"({len(b['fallback_entries'])}개):"
                )
                for e, method in b["fallback_entries"]:
                    tee.print(
                        f"    uid={e['unique_id']}  "
                        f"name={e['name']}  "
                        f"text={_preview(e['text'], 50)}  "
                        f"← {method}"
                    )

        tee.print()
        tee.print("=" * 80)
        tee.print(
            f"완료: 전체 {total_all}개 중 "
            f"ignored {ignored_all} 제외 유효 {effective_all}개, "
            f"번역 {direct_all + fallback_all} "
            f"({format_percent(direct_all + fallback_all, effective_all)}), "
            f"empty {empty_all}, missing {missing_all}"
        )

        return 0
    finally:
        tee.close()


if __name__ == "__main__":
    sys.exit(main())
