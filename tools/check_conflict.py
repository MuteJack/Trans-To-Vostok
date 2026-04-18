"""
xlsx 내 번역 충돌 검사.

공백을 제거한 text 기준으로, 같은 원문에 **다른 번역**이 등록된 경우를 경고한다.
같은 원문이 여러 method/context 에 걸쳐 다르게 번역되면 일관성이 깨지므로 리뷰 대상.

검사 대상:
    - ignore / untranslatable=1 행은 제외
    - translation 이 비어있는 행은 제외
    - 공백 제거 후 text 가 같고 translation 이 다르면 충돌

현재는 WARNING 만 출력 (ERROR 아님, 종료 코드 0).

사용법:
    python check_conflict.py <locale>

예시:
    python check_conflict.py Korean

로그:
    <locale>/.log/check_conflict_YYYYMMDD_HHMMSS.log
"""
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


BOOL_TRUE = {"1", "true"}


def _normalize_text(s: str) -> str:
    """공백/탭/개행을 모두 제거한 비교용 키."""
    return "".join(s.split())


def collect_conflicts(sheets: list) -> list[dict]:
    """
    시트별 행을 돌며 (stripped_text → [entry, ...]) 로 그룹핑.
    translation 이 다르면 충돌로 판정.

    entry: {sheet, row_idx, method, filename, filetype, location,
            parent, name, property, text, translation}
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    total_eligible = 0

    for sheet_name, _header, rows in sheets:
        for i, row in enumerate(rows, start=2):  # 2 = 헤더 제외 첫 행
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

    # 번역이 서로 다른 그룹만 충돌로 추출
    conflicts: list[dict] = []
    for key, entries in groups.items():
        if len(entries) < 2:
            continue
        # 공백 제거한 translation 도 비교 (화이트스페이스 차이는 충돌 아님)
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
        print("사용법: python check_conflict.py <locale>")
        print("예: python check_conflict.py Korean")
        return 1

    locale = sys.argv[1]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    locale_dir = mod_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"

    if not xlsx_path.exists():
        print(f"[ERROR] xlsx 파일이 없습니다: {xlsx_path}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = locale_dir / ".log" / f"check_conflict_{timestamp}.log"
    tee = Tee(log_path)

    try:
        tee.print(f"xlsx: {xlsx_path}")
        tee.print(f"로그: {log_path}")
        tee.print(f"실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        tee.print()

        tee.print("xlsx 로드 중...")
        sheets = load_all_translation_sheets(xlsx_path)
        tee.print(f"  시트 {len(sheets)}개")
        tee.print()

        tee.print("충돌 검사 중... (공백 제거한 text 기준)")
        conflicts, total_eligible = collect_conflicts(sheets)
        tee.print(f"  검사 대상 행: {total_eligible}개")
        tee.print(f"  충돌 그룹: {len(conflicts)}개")
        tee.print()

        if not conflicts:
            tee.print("충돌 없음.")
            return 0

        # 충돌 그룹을 엔트리 수 내림차순으로 정렬
        conflicts.sort(key=lambda c: len(c["entries"]), reverse=True)

        tee.print("=" * 80)
        tee.print(f"[WARNING] 번역 충돌 {len(conflicts)}건")
        tee.print("=" * 80)

        for idx, c in enumerate(conflicts, 1):
            tee.print()
            tee.print(
                f"#{idx}  원문(공백제거): {_preview(c['key'], 50)}  "
                f"— {len(c['entries'])}개 엔트리, {c['distinct_count']}종 번역"
            )
            # translation 별 그룹 표시
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
        tee.print(f"요약: {len(conflicts)}개 충돌 그룹, 총 검사 대상 {total_eligible}개 행")
        return 0
    finally:
        tee.close()


if __name__ == "__main__":
    sys.exit(main())
