"""
TSV와 xlsx를 비교해 번역 커버리지를 리포트한다.

매칭 분류:
- direct:      xlsx의 일반 행이 unique_id로 1:1 매칭 (번역 완료)
- literal:     xlsx의 #literal 행이 text로 매칭 (fallback 번역)
- expression:  xlsx의 #expression 행의 패턴이 text와 매칭 (fallback 번역)
- ignored:     xlsx에 있고 ignore=1 (의도적 제외, 미번역 아님)
- empty:       xlsx에 있지만 translated 비어있음 (번역 대기)
- missing:     xlsx에 아예 없음 (새로 추가 필요)

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

# 같은 폴더 모듈 import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_translation import (
    _preview,
    load_xlsx_main,
    Tee,
)


IGNORE_VALUES = {"1", "true"}


# ==========================================
# Pattern 컴파일 (translator.gd와 동일 로직)
# ==========================================

def compile_pattern(text: str) -> re.Pattern:
    """
    {name} 과 * 를 지원하는 패턴을 Python 정규식으로 컴파일.
    translator.gd의 _compile_pattern 과 동작 일치.
    """
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
        # 정규식 특수 문자 이스케이프
        if c in r"\.^$+?()[]|{}":
            result.append("\\" + c)
        else:
            result.append(c)
        i += 1
    return re.compile("^" + "".join(result) + "$")


# ==========================================
# TSV 로드
# ==========================================

def load_tsv_entries(tsv_dir: Path) -> list[dict]:
    """extracted_text/ 의 모든 .tsv 파일을 로드."""
    entries = []
    for tsv_file in sorted(tsv_dir.rglob("*.tsv")):
        try:
            with open(tsv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    uid = (row.get("unique_id") or "").strip()
                    if not uid:
                        continue
                    entries.append({
                        "unique_id": uid,
                        "location": (row.get("location") or "").strip(),
                        "parent": (row.get("parent") or "").strip(),
                        "name": (row.get("name") or "").strip(),
                        "type": (row.get("type") or "").strip(),
                        "text": row.get("text") or "",
                        "_tsv_file": tsv_file.name,
                    })
        except Exception as e:
            print(f"[WARN] TSV 읽기 실패: {tsv_file} ({e})")
    return entries


# ==========================================
# xlsx 분석
# ==========================================

def analyze_xlsx(rows: list[dict]) -> tuple[set, set, set, dict, list]:
    """
    xlsx를 분석하여:
    - direct_uids: 직접 번역된 unique_id 집합 (일반 행, translated 있음, ignore 아님)
    - ignored_uids: ignore=1 로 표시된 unique_id 집합 (의도적 제외)
    - empty_uids: xlsx에 있지만 translated 비어있는 unique_id 집합
    - literal_map: {text: translated} (#literal 행, ignore 아님)
    - expression_list: [(compiled_regex, translated_template), ...] (#expression 행, ignore 아님)
    """
    direct_uids: set = set()
    ignored_uids: set = set()
    empty_uids: set = set()
    literal_map: dict = {}
    expression_list: list = []

    for row in rows:
        uid = row.get("unique_id", "").strip()
        location = row.get("location", "").strip()
        ignore = row.get("ignore", "").strip().lower()
        translated = row.get("translated", "")
        text = row.get("text", "")

        # ignored는 일반/특수 구분 없이 "의도적 제외"로 기록
        if ignore in IGNORE_VALUES:
            if uid:
                ignored_uids.add(uid)
            continue

        # 특수 (#literal, #expression) 는 translated 비어있으면 스킵
        if location == "#literal":
            if translated:
                literal_map[text] = translated
            continue
        if location == "#expression":
            if translated:
                try:
                    regex = compile_pattern(text)
                    expression_list.append((regex, translated))
                except re.error:
                    pass
            continue

        # 일반 행
        if uid:
            if translated:
                direct_uids.add(uid)
            else:
                empty_uids.add(uid)

    return direct_uids, ignored_uids, empty_uids, literal_map, expression_list


# ==========================================
# 매칭 분류
# ==========================================

def classify_entry(
    entry: dict,
    direct_uids: set,
    ignored_uids: set,
    empty_uids: set,
    literal_map: dict,
    expression_list: list,
) -> tuple[str, str]:
    """
    TSV 엔트리의 번역 상태를 분류.
    반환: (status, method)
        status: "direct" | "ignored" | "literal" | "expression" | "empty" | "missing"
        method: 추가 정보 (매칭 방법)
    """
    uid = entry["unique_id"]
    text = entry["text"]

    # 1. ignored (의도적 제외)
    if uid in ignored_uids:
        return ("ignored", "")

    # 2. 직접 매칭
    if uid in direct_uids:
        return ("direct", "")

    # 3. #literal 매칭 (text 완전 일치)
    if text in literal_map:
        return ("literal", "#literal")

    # 4. #expression 매칭 (패턴)
    for regex, _trans in expression_list:
        if regex.match(text):
            return ("expression", f"#expression: {regex.pattern}")

    # 5. xlsx에는 있지만 translated 비어있음
    if uid in empty_uids:
        return ("empty", "")

    # 6. xlsx에 전혀 없음
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

    # 로그 파일
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = locale_dir / ".log" / f"check_untranslated_{timestamp}.log"
    tee = Tee(log_path)

    try:
        tee.print(f"xlsx:   {xlsx_path}")
        tee.print(f"TSV:    {tsv_dir}")
        tee.print(f"로그:   {log_path}")
        tee.print(f"실행:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        tee.print()

        # 1. xlsx 로드 및 분석
        tee.print("xlsx 로드 중...")
        _header, rows, sheet_name = load_xlsx_main(xlsx_path)
        (
            direct_uids,
            ignored_uids,
            empty_uids,
            literal_map,
            expression_list,
        ) = analyze_xlsx(rows)
        tee.print(
            f"  {sheet_name} 시트, {len(rows)}행"
            f" → 직접 {len(direct_uids)}개, "
            f"ignored {len(ignored_uids)}개, "
            f"empty {len(empty_uids)}개, "
            f"#literal {len(literal_map)}개, "
            f"#expression {len(expression_list)}개"
        )
        tee.print()

        # 2. TSV 로드
        tee.print("TSV 로드 중...")
        tsv_entries = load_tsv_entries(tsv_dir)
        tee.print(f"  {len(tsv_entries)}개 엔트리")
        tee.print()

        # 3. 분류: 파일별로 집계 및 상세
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
                entry,
                direct_uids,
                ignored_uids,
                empty_uids,
                literal_map,
                expression_list,
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
            else:  # missing
                bucket["missing"] += 1
                bucket["missing_entries"].append(entry)

        # 4. 파일별 요약
        tee.print("=" * 80)
        tee.print("파일별 요약 (ignored 제외 유효 엔트리 기준)")
        tee.print("=" * 80)

        file_names = sorted(per_file.keys())
        max_fname = max((len(n) for n in file_names), default=20)

        total_all = 0
        effective_all = 0     # total - ignored
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

            effective = total - ignored            # 번역이 필요한 실제 엔트리
            translated = direct + fallback

            total_all += total
            effective_all += effective
            direct_all += direct
            fallback_all += fallback
            ignored_all += ignored
            empty_all += empty
            missing_all += missing

            tee.print(
                f"[{fname:<{max_fname}}] "
                f"번역 {translated}/{effective} ({format_percent(translated, effective)}), "
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
                continue  # 전부 직접/ignored인 파일은 상세 출력 생략

            tee.print()
            tee.print(f"[{fname}]")

            # 5-1. xlsx에 없음 (missing)
            if b["missing_entries"]:
                tee.print(f"  missing - xlsx에 없음 ({b['missing']}개):")
                for e in b["missing_entries"]:
                    tee.print(
                        f"    uid={e['unique_id']}  "
                        f"name={e['name']}  "
                        f"type={e['type']}  "
                        f"text={_preview(e['text'], 50)}"
                    )

            # 5-2. xlsx에 있지만 translated 비어있음 (empty)
            if b["empty_entries"]:
                tee.print(f"  empty - xlsx에 있지만 미번역 ({b['empty']}개):")
                for e in b["empty_entries"]:
                    tee.print(
                        f"    uid={e['unique_id']}  "
                        f"name={e['name']}  "
                        f"type={e['type']}  "
                        f"text={_preview(e['text'], 50)}"
                    )

            # 5-3. fallback 번역 (literal/expression)
            if b["fallback_entries"]:
                tee.print(
                    f"  fallback - Literal/Expression으로 매칭 "
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
