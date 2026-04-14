"""
Godot .tres 파일에서 지정한 필드 값을 추출한다.

[resource] 블록 내부의 `field = "value"` 패턴을 찾아 값을 TSV로 출력한다.
여러 줄 문자열(개행 포함)과 이스케이프된 따옴표(\")를 정확히 처리한다.

출력 파일 확장자는 `.tres.tsv` 로 `.tscn` 추출본(*.tsv)과 구분한다.

사용법:
    python extract_tres_text.py --fields <필드,목록> [옵션]

옵션:
    --input <DIR>       대상 디렉토리 (하위 재귀)
    --fields <LIST>     추출할 필드 (콤마 구분). 예: name,description
    --output <FILE>     출력 TSV 경로 (기본: stdout)
    --class <NAME>      script_class 필터 (선택사항). 예: EventData

예시:
    # Events 디렉토리의 모든 .tres 에서 name/description 추출
    python extract_tres_text.py \\
        --input ../.tmp/pck_recovered/Events/List \\
        --fields name,description \\
        --output ../.tmp/extracted_text/Events.tres.tsv
"""
import argparse
import csv
import re
import sys
from pathlib import Path

# Windows 콘솔 한글 출력 지원
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


def _find_resource_block(text: str) -> tuple[int, int]:
    """
    [resource] 블록의 본문 시작~끝 오프셋을 반환.
    [resource] 라인 다음부터 파일 끝까지가 블록 본문.
    """
    m = re.search(r"^\[resource\]\s*$", text, re.MULTILINE)
    if not m:
        return (-1, -1)
    return (m.end(), len(text))


def _find_script_class(text: str) -> str:
    """[gd_resource ...] 헤더에서 script_class 추출."""
    m = re.search(
        r'\[gd_resource\b[^\]]*script_class\s*=\s*"([^"]*)"',
        text,
    )
    if m:
        return m.group(1)
    return ""


def _extract_string_field(body: str, field_name: str) -> str | None:
    """
    [resource] 블록 안에서 `field_name = "값"` 을 찾아 값을 반환.
    이스케이프된 따옴표(\")와 여러 줄 문자열을 처리한다.
    찾지 못하면 None 반환.
    """
    pattern = re.compile(
        rf'^{re.escape(field_name)}\s*=\s*"', re.MULTILINE
    )
    m = pattern.search(body)
    if not m:
        return None

    i = m.end()  # 여는 따옴표 다음 위치
    chars = []
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            # 이스케이프 시퀀스 처리
            nxt = body[i + 1]
            if nxt == "n":
                chars.append("\n")
            elif nxt == "t":
                chars.append("\t")
            elif nxt == "r":
                chars.append("\r")
            elif nxt == '"':
                chars.append('"')
            elif nxt == "\\":
                chars.append("\\")
            else:
                chars.append(nxt)
            i += 2
            continue
        if c == '"':
            # 닫는 따옴표 발견
            return "".join(chars)
        chars.append(c)
        i += 1
    return None  # 닫는 따옴표를 못 찾음


def parse_tres(path: Path, fields: list[str]) -> dict | None:
    """
    한 개의 .tres 파일에서 지정한 필드 값들을 dict로 반환.
    파일이 리소스가 아니거나 필드가 하나도 없으면 None 반환.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"[WARN] 읽기 실패: {path} ({e})", file=sys.stderr)
        return None

    script_class = _find_script_class(text)
    body_start, body_end = _find_resource_block(text)
    if body_start < 0:
        return None
    body = text[body_start:body_end]

    result = {"_script_class": script_class}
    found_any = False
    for field in fields:
        val = _extract_string_field(body, field)
        if val is not None:
            result[field] = val
            found_any = True
        else:
            result[field] = ""
    return result if found_any else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=".tres 파일에서 필드 값 추출",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input",
        required=True,
        help="대상 디렉토리 (하위 재귀)",
    )
    parser.add_argument(
        "--fields",
        required=True,
        help="추출할 필드 (콤마 구분). 예: name,description",
    )
    parser.add_argument(
        "--output",
        help="출력 TSV 경로 (기본: stdout). 관례: .tres.tsv 확장자 권장",
    )
    parser.add_argument(
        "--class",
        dest="class_filter",
        help="script_class 필터 (선택). 예: EventData",
    )
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    if not input_dir.exists():
        print(f"[ERROR] 입력 디렉토리가 없습니다: {input_dir}", file=sys.stderr)
        return 1
    if not input_dir.is_dir():
        print(f"[ERROR] 디렉토리가 아닙니다: {input_dir}", file=sys.stderr)
        return 1

    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    if not fields:
        print("[ERROR] --fields 가 비어있습니다.", file=sys.stderr)
        return 1

    tres_files = sorted(input_dir.rglob("*.tres"))
    if not tres_files:
        print(f"[ERROR] .tres 파일이 없습니다: {input_dir}", file=sys.stderr)
        return 1

    # 결과 수집: (파일 상대경로, script_class, field, value)
    rows: list[tuple[str, str, str, str]] = []
    for tres in tres_files:
        parsed = parse_tres(tres, fields)
        if parsed is None:
            continue
        if args.class_filter and parsed["_script_class"] != args.class_filter:
            continue
        rel = tres.relative_to(input_dir).as_posix()
        for field in fields:
            value = parsed.get(field, "")
            if value == "":
                continue  # 빈 값은 스킵
            rows.append((rel, parsed["_script_class"], field, value))

    # 출력
    if args.output:
        out_path = Path(args.output).resolve()
        if not out_path.name.endswith(".tres.tsv"):
            print(
                f"[WARN] 출력 파일 확장자는 '.tres.tsv' 를 권장합니다: {out_path.name}",
                file=sys.stderr,
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        f = open(out_path, "w", encoding="utf-8", newline="")
        close_on_done = True
    else:
        f = sys.stdout
        close_on_done = False

    try:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["file", "class", "field", "text"])
        for row in rows:
            writer.writerow(row)
    finally:
        if close_on_done:
            f.close()

    if args.output:
        print(f"\n완료: {len(rows)}개 엔트리 ({len(tres_files)}개 파일 스캔)")
        print(f"출력: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
