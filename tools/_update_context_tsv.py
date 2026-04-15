"""
[임시 도구] Translation.tsv 의 컨텍스트 필드를 추출 TSV 기준으로 업데이트.

워크플로:
    1. _xlsx_to_tsv.py 로 Translation.xlsx → .tmp/_{Sheet}.tsv 들 덤프
    2. 이 도구로 .tmp/_*.tsv 전체의 컨텍스트 필드 갱신
    3. 업데이트된 시트별 TSV 를 엑셀에 수동으로 붙여넣기 (서식 보존)

업데이트 대상 필드 (unique_id, text 가 .tscn.tsv 에서 찾아지면):
    filename, filetype, location, parent, name, type

매칭 키: (unique_id, text) 튜플
    Godot 은 .tscn 파일 내부에서만 unique_id 유일성을 보장하므로
    서로 다른 씬에 같은 uid 가 존재할 수 있다 (복사-붙여넣기 등).
    xlsx 의 text 를 함께 키로 써서 정확한 씬을 특정한다.

소스: .tmp/extracted_text/**/*.tscn.tsv (extract_tscn_text.py 출력)

.tres.tsv 엔트리는 unique_id 가 없어 매칭 대상이 아니며, 기존 행의
filename/filetype 등은 그대로 유지된다.

사용법:
    python _update_context_tsv.py                    # 기본: .tmp/_*.tsv 전체
    python _update_context_tsv.py <tsv_dir>          # TSV 디렉토리 지정
    python _update_context_tsv.py <tsv_dir> <extracted_dir>

출력: 입력 파일 위치에 덮어쓰기 (원본은 .bak 로 자동 백업)
"""
import csv
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


# 업데이트할 필드들
UPDATE_FIELDS = ["filename", "filetype", "location", "parent", "name", "type"]


def build_uid_text_index(extracted_dir: Path) -> dict:
    """
    .tmp/extracted_text/**/*.tscn.tsv 에서 (unique_id, text) → 컨텍스트 dict 를 만든다.

    uid 는 .tscn 파일 내부에서만 유일하므로 서로 다른 씬에 같은 uid 가
    존재할 수 있다. text 를 함께 키로 써서 구분한다.

    같은 (uid, text) 가 중복되면 경고 후 첫 발견 사용.
    """
    index: dict[tuple[str, str], dict] = {}
    conflicts: list[tuple[str, str, str, str]] = []

    for tsv_file in sorted(extracted_dir.rglob("*.tscn.tsv")):
        try:
            with open(tsv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    uid = (row.get("unique_id") or "").strip()
                    text = row.get("text") or ""
                    if not uid:
                        continue
                    key = (uid, text)
                    ctx = {k: (row.get(k) or "") for k in UPDATE_FIELDS}
                    if key in index:
                        existing = index[key]
                        if any(existing[k] != ctx[k] for k in UPDATE_FIELDS):
                            conflicts.append((uid, text, existing.get("filename", ""), ctx.get("filename", "")))
                    else:
                        index[key] = ctx
        except Exception as e:
            print(f"[WARN] TSV 읽기 실패: {tsv_file} ({e})", file=sys.stderr)

    if conflicts:
        print(f"[WARN] (unique_id, text) 충돌 {len(conflicts)}건 (첫 발견 사용):", file=sys.stderr)
        for uid, text, a, b in conflicts[:5]:
            preview = text if len(text) < 40 else text[:37] + "..."
            print(f"  uid={uid} text={preview!r}: {a!r} vs {b!r}", file=sys.stderr)
        if len(conflicts) > 5:
            print(f"  ... 외 {len(conflicts) - 5}건", file=sys.stderr)

    return index


def update_tsv(tsv_path: Path, index: dict) -> tuple[int, int, int, int]:
    """
    TSV 를 읽어 (unique_id, text) 가 인덱스에 있는 행의 컨텍스트 필드를 업데이트.
    반환: (total_rows_with_uid, updated_rows, unchanged_rows, not_found_rows)
    """
    with open(tsv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        rows = list(reader)

    if not rows:
        print("[ERROR] 빈 TSV", file=sys.stderr)
        return (0, 0, 0, 0)

    header = rows[0]
    # 헤더 → 인덱스. 동일 이름이 여러 번이면 첫 번째 사용
    col_idx: dict[str, int] = {}
    for i, h in enumerate(header):
        if h not in col_idx:
            col_idx[h] = i

    uid_col = col_idx.get("unique_id")
    text_col = col_idx.get("text")
    if uid_col is None:
        print("[ERROR] 헤더에 'unique_id' 컬럼이 없습니다.", file=sys.stderr)
        print(f"  실제 헤더: {header}", file=sys.stderr)
        return (0, 0, 0, 0)
    if text_col is None:
        print("[ERROR] 헤더에 'text' 컬럼이 없습니다.", file=sys.stderr)
        print(f"  실제 헤더: {header}", file=sys.stderr)
        return (0, 0, 0, 0)

    # 업데이트 대상 컬럼 인덱스 확인
    target_cols: dict[str, int] = {}
    missing_cols = []
    for field in UPDATE_FIELDS:
        if field in col_idx:
            target_cols[field] = col_idx[field]
        else:
            missing_cols.append(field)

    if missing_cols:
        print(f"[ERROR] 헤더에 누락된 컬럼: {missing_cols}", file=sys.stderr)
        print(f"  실제 헤더: {header}", file=sys.stderr)
        return (0, 0, 0, 0)

    total = 0
    updated = 0
    unchanged = 0
    not_found = 0

    for i in range(1, len(rows)):
        row = rows[i]
        # 컬럼 수가 헤더보다 짧으면 pad
        if len(row) < len(header):
            row.extend([""] * (len(header) - len(row)))
            rows[i] = row

        uid = row[uid_col].strip() if uid_col < len(row) else ""
        text = row[text_col] if text_col < len(row) else ""
        if not uid:
            continue
        total += 1

        ctx = index.get((uid, text))
        if ctx is None:
            not_found += 1
            continue

        # 기존 값과 비교해 실제 변경 여부 확인
        changed = False
        for field, ci in target_cols.items():
            new_val = ctx[field]
            if row[ci] != new_val:
                row[ci] = new_val
                changed = True

        if changed:
            updated += 1
        else:
            unchanged += 1

    # 백업 후 덮어쓰기
    bak_path = tsv_path.with_suffix(tsv_path.suffix + ".bak")
    tsv_path.replace(bak_path)
    try:
        with open(tsv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            for row in rows:
                writer.writerow(row)
    except Exception:
        # 실패 시 백업 복원
        bak_path.replace(tsv_path)
        raise

    return (total, updated, unchanged, not_found)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent

    default_tsv_dir = mod_root / ".tmp"
    default_extracted = mod_root / ".tmp" / "extracted_text"

    tsv_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_tsv_dir.resolve()
    extracted_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_extracted.resolve()

    if not tsv_dir.exists():
        print(f"[ERROR] TSV 디렉토리가 없습니다: {tsv_dir}", file=sys.stderr)
        print("  먼저 _xlsx_to_tsv.py 를 실행해 시트별 TSV 를 만드세요.", file=sys.stderr)
        return 1
    if not extracted_dir.exists():
        print(f"[ERROR] 추출 디렉토리가 없습니다: {extracted_dir}", file=sys.stderr)
        print("  먼저 extract_tscn_text.py 를 실행하세요.", file=sys.stderr)
        return 1

    # 시트별 TSV 파일 수집 (_xlsx_to_tsv.py 출력 패턴)
    tsv_files = sorted(tsv_dir.glob("_*.tsv"))
    if not tsv_files:
        print(f"[ERROR] {tsv_dir} 에 _*.tsv 파일이 없습니다.", file=sys.stderr)
        print("  먼저 _xlsx_to_tsv.py 를 실행하세요.", file=sys.stderr)
        return 1

    print(f"대상 디렉:  {tsv_dir}")
    print(f"대상 파일:  {[f.name for f in tsv_files]}")
    print(f"추출 디렉:  {extracted_dir}")
    print()

    print("(unique_id, text) 인덱스 빌드 중...")
    index = build_uid_text_index(extracted_dir)
    print(f"  인덱스된 (uid, text) 쌍: {len(index)}개")
    print()

    grand_total = 0
    grand_updated = 0
    grand_unchanged = 0
    grand_not_found = 0

    for tsv_path in tsv_files:
        print(f"[{tsv_path.name}] 업데이트 중...")
        total, updated, unchanged, not_found = update_tsv(tsv_path, index)
        print(f"  rows={total}  updated={updated}  unchanged={unchanged}  not_found={not_found}")
        grand_total += total
        grand_updated += updated
        grand_unchanged += unchanged
        grand_not_found += not_found

    print()
    print("=" * 60)
    print(f"전체: {len(tsv_files)}개 시트 TSV 처리")
    print(f"  unique_id 있는 행:  {grand_total}개")
    print(f"  업데이트됨:         {grand_updated}개")
    print(f"  이미 최신:          {grand_unchanged}개")
    print(f"  인덱스에 없음:      {grand_not_found}개  (uid+text 조합이 tscn 소스에 없음)")
    print()
    print("백업: 각 _*.tsv 파일 옆에 .bak 생성")
    print("다음 단계: 각 TSV 의 데이터 영역을 해당 엑셀 시트에 수동 붙여넣기")
    return 0


if __name__ == "__main__":
    sys.exit(main())
