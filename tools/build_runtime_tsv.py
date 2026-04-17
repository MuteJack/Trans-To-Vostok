"""
Translation.xlsx → 런타임 TSV 빌드 스크립트.

동작:
1. <locale>/Translation.xlsx 를 validate_xlsx() 로 검증 (에러면 빌드 실패)
2. MetaData 를 제외한 모든 시트의 행 수집
3. ignore=1 인 행 제외
4. translation 비어있는 행 제외
5. method + location 기준으로 5 개 런타임 TSV 로 분류:
       translation_static.tsv           — method=static                      (5필드 + text + translation)
       translation_literal_scoped.tsv   — method=literal/"" + location        (5필드 + text + translation)
       translation_pattern_scoped.tsv   — method=pattern + location           (5필드 + text + translation)
       translation_literal.tsv          — method=literal/"" + no location     (text + translation)
       translation_pattern.tsv          — method=pattern + no location        (text + translation)
6. 원자적 쓰기 (.tmp → rename)

런타임 매칭 우선순위 (translator.gd 가 이 순서로 시도):
    1. static exact          (exact 5-tuple, TSV 검증됨)
    2. scoped literal exact  (exact 5-tuple, 동적 텍스트)
    3. scoped pattern exact  (컨텍스트 완전 일치 + 정규식)
    4. literal global        (text-only)
    5. pattern global        (정규식 전역)
    6. static score          (부분 컨텍스트 점수 매칭, 게임 업데이트 fallback)
    7. scoped literal score  (동적 텍스트 부분 컨텍스트 매칭)
    8. scoped pattern score  (정규식 + 부분 컨텍스트)

사용법:
    python build_runtime_tsv.py <locale>

예시:
    python build_runtime_tsv.py Korean
"""
import csv
import sys
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
    validate_xlsx,
    load_all_translation_sheets,
    load_metadata,
    _effective_method,
)


# 컨텍스트 포함 TSV (static / scoped literal / scoped pattern)
COLUMNS_SCOPED = ["location", "parent", "name", "type", "text", "translation"]
# 전역 TSV (literal / pattern)
COLUMNS_GLOBAL = ["text", "translation"]

BOOL_TRUE = {"1", "true"}


def classify_rows(rows: list[dict]) -> tuple[dict, dict]:
    """
    행을 5개 런타임 버킷으로 분류.

    제외 조건:
        - method=ignore               (운영적 제외)
        - untranslatable=1             (번역 불가 텍스트)
        - translation 비어있음          (미번역)

    반환:
        buckets: { bucket_name: [row, ...], ... }
        stats:   { bucket_name: count, ..., "excluded_ignore": N, ... }
    """
    buckets: dict[str, list] = {
        "static": [],
        "literal_scoped": [],
        "pattern_scoped": [],
        "literal_global": [],
        "pattern_global": [],
        "substr": [],
    }
    stats = {
        "total": len(rows),
        "excluded_ignore": 0,
        "excluded_untranslatable": 0,
        "excluded_untranslated": 0,
    }
    for name in buckets.keys():
        stats[name] = 0

    for row in rows:
        effective = _effective_method(row)
        if effective == "ignore":
            stats["excluded_ignore"] += 1
            continue

        if row.get("untranslatable", "").strip().lower() in BOOL_TRUE:
            stats["excluded_untranslatable"] += 1
            continue

        if row.get("translation", "") == "":
            stats["excluded_untranslated"] += 1
            continue
        location = row.get("location", "").strip()

        if effective == "static":
            buckets["static"].append(row)
            stats["static"] += 1
        elif effective == "literal":
            if location:
                buckets["literal_scoped"].append(row)
                stats["literal_scoped"] += 1
            else:
                buckets["literal_global"].append(row)
                stats["literal_global"] += 1
        elif effective == "pattern":
            if location:
                buckets["pattern_scoped"].append(row)
                stats["pattern_scoped"] += 1
            else:
                buckets["pattern_global"].append(row)
                stats["pattern_global"] += 1
        elif effective == "substr":
            buckets["substr"].append(row)
            # substr → literal_global 에도 이중 출력 (정확 일치 시 tier 4 에서 빠르게 히트)
            text = row.get("text", "")
            translation = row.get("translation", "")
            conflict = False
            for existing in buckets["literal_global"]:
                if existing.get("text", "") == text and existing.get("translation", "") != translation:
                    conflict = True
                    print(
                        f"[WARN] substr/literal 번역 충돌: text={text!r} "
                        f"(substr={translation!r} vs literal={existing.get('translation', '')!r})",
                        file=sys.stderr,
                    )
                    break
            if not conflict:
                buckets["literal_global"].append(row)
            stats["substr"] += 1

    return buckets, stats


def write_tsv(out_path: Path, columns: list[str], rows: list[dict]) -> None:
    """TSV 를 원자적으로 쓴다."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([row.get(c, "") for c in columns])
        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    soft = "--soft" in flags

    if not args:
        print("사용법: python build_runtime_tsv.py <locale> [--soft|--hard]")
        print("  --hard (기본): TSV 매칭 실패 → ERROR (빌드 차단)")
        print("  --soft:        TSV 매칭 실패 → WARNING (빌드 계속)")
        print("예: python build_runtime_tsv.py Korean --soft")
        return 1

    locale = args[0]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    locale_dir = mod_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"
    tsv_dir = mod_root / ".tmp" / "extracted_text"

    if not locale_dir.exists():
        print(f"[ERROR] 로케일 폴더가 없습니다: {locale_dir}")
        return 1
    if not xlsx_path.exists():
        print(f"[ERROR] xlsx 파일이 없습니다: {xlsx_path}")
        return 1

    # 1. 검증
    print(f"[1/4] 검증 중... ({locale}, {'soft' if soft else 'hard'})")
    try:
        result = validate_xlsx(xlsx_path, tsv_dir, soft=soft)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] 검증 실패: {e}")
        return 1

    print(f"  → 로그: {result.log_path}")
    if not result.ok:
        print(
            f"[ERROR] 검증 실패: {result.error_count}개 에러 "
            f"(TSV {result.error_tsv}, 플래그 {result.error_flags}, "
            f"중복 {result.error_dup}, method {result.error_method})"
        )
        print("빌드를 중단합니다. 위 로그를 확인하세요.")
        raise SystemExit(1)

    if result.warning_count > 0:
        print(f"  경고 {result.warning_count}개 (진행 계속)")
    print()

    # 2. xlsx 로드 (모든 번역 시트 병합)
    print("[2/4] xlsx 로드 중...")
    sheets = load_all_translation_sheets(xlsx_path)
    all_rows: list[dict] = []
    for _sheet_name, _header, rows in sheets:
        all_rows.extend(rows)
    print(f"  → 시트 {len(sheets)}개, 총 {len(all_rows)}행 로드")
    print()

    # 3. 분류
    print("[3/4] 행 분류 중...")
    buckets, stats = classify_rows(all_rows)
    print(f"  static                 {stats['static']:4d}행")
    print(f"  literal_scoped         {stats['literal_scoped']:4d}행")
    print(f"  pattern_scoped         {stats['pattern_scoped']:4d}행")
    print(f"  literal (global)       {stats['literal_global']:4d}행")
    print(f"  pattern (global)       {stats['pattern_global']:4d}행")
    print(f"  substr                 {stats['substr']:4d}행")
    print(f"  제외 (ignore)          {stats['excluded_ignore']:4d}행")
    print(f"  제외 (untranslatable)  {stats['excluded_untranslatable']:4d}행")
    print(f"  제외 (미번역)          {stats['excluded_untranslated']:4d}행")
    print()

    # 4. metadata.tsv 생성
    print("[4/5] metadata.tsv 생성 중...")
    meta = load_metadata(xlsx_path)
    meta_path = locale_dir / "metadata.tsv"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["field", "value"])
        for k, v in meta.items():
            writer.writerow([k, v])
    print(f"  → {meta_path.relative_to(mod_root)} ({len(meta)}개 필드)")
    print()

    # 5. TSV 작성
    print("[5/5] TSV 작성 중...")

    outputs = [
        (locale_dir / "translation_static.tsv",         COLUMNS_SCOPED, buckets["static"]),
        (locale_dir / "translation_literal_scoped.tsv", COLUMNS_SCOPED, buckets["literal_scoped"]),
        (locale_dir / "translation_pattern_scoped.tsv", COLUMNS_SCOPED, buckets["pattern_scoped"]),
        (locale_dir / "translation_literal.tsv",        COLUMNS_GLOBAL, buckets["literal_global"]),
        (locale_dir / "translation_pattern.tsv",        COLUMNS_GLOBAL, buckets["pattern_global"]),
        (locale_dir / "translation_substr.tsv",         COLUMNS_GLOBAL, buckets["substr"]),
    ]

    for out_path, columns, rows in outputs:
        write_tsv(out_path, columns, rows)
        print(f"  → {out_path.relative_to(mod_root)} ({len(rows)}행)")

    # 구 파일 정리: translation.tsv, translation_expression.tsv 는 더 이상 사용 안 함
    for legacy_name in ("translation.tsv", "translation_expression.tsv"):
        legacy_path = locale_dir / legacy_name
        if legacy_path.exists():
            try:
                legacy_path.unlink()
                print(f"  × {legacy_path.relative_to(mod_root)} (구 포맷 삭제)")
            except OSError as e:
                print(f"  [WARN] 구 파일 삭제 실패: {legacy_path} ({e})")

    print()
    print("=" * 60)
    print(f"빌드 완료: {locale}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
