"""
.gd 파일에서 UI 텍스트 할당을 찾는다.

대상 패턴:
    xxx.text = "..."            → 정적 리터럴
    xxx.text = "..." + var       → 연결식 (동적)
    xxx.text = "..." % args      → 포맷 문자열
    xxx.set_text("...")          → 함수 호출
    xxx.tooltip_text = "..."     → 툴팁
    xxx.placeholder_text = "..." → 플레이스홀더

사용법:
    python extract_gd_text.py [source_dir] [output_file]

기본값 (tools/ 기준):
    source_dir  = ../.tmp/pck_recovered/Scripts/
    output_file = ../.tmp/extracted_text/dynamic_strings.tsv
"""
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


# 문자열 리터럴 추출 (이스케이프 인식)
STRING_LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')

# 주석 제거 (간단한 휴리스틱: 문자열 바깥의 #부터 줄 끝까지)
def strip_comment(line: str) -> str:
    in_str = False
    escape = False
    for i, c in enumerate(line):
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if c == "#" and not in_str:
            return line[:i]
    return line


# 텍스트 할당 패턴 (target.property = value)
ASSIGN_PROPS = ["text", "tooltip_text", "placeholder_text", "hint_tooltip"]
PROP_ALT = "|".join(ASSIGN_PROPS)

# 예: label.text = ..., $HUD/Label.text = ..., get_node("x").text = ...
ASSIGN_RE = re.compile(
    rf'(?P<target>[^\s=]+?)\s*\.\s*(?P<prop>{PROP_ALT})\s*=\s*(?P<value>.+)$'
)

# 함수 호출 패턴: xxx.set_text("...")
SET_TEXT_RE = re.compile(r'(?P<target>[^\s]+?)\s*\.\s*set_text\s*\(\s*(?P<value>.+?)\s*\)')


def classify(value: str, literals: list[str]) -> str:
    """value 표현식과 리터럴들로부터 kind 판정."""
    if not literals:
        return "none"
    v = value.strip()
    # 오로지 하나의 리터럴만, 연결/포맷/함수호출 없음
    if len(literals) == 1:
        # value가 정확히 "..."인 경우
        only = '"' + literals[0].replace('\\', '\\\\').replace('"', '\\"') + '"'
        if v == only:
            return "literal"
    if "+" in v:
        return "concat"
    if "%" in v:
        return "format"
    return "literal-multi"


def parse_gd(path: Path) -> list[dict]:
    """.gd 파일을 한 줄씩 스캔."""
    results = []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="replace")

    for lineno, raw_line in enumerate(content.splitlines(), 1):
        line = strip_comment(raw_line).rstrip()
        if not line:
            continue

        # 1) xxx.text = value 패턴
        m = ASSIGN_RE.search(line)
        if m:
            target = m.group("target")
            prop = m.group("prop")
            value = m.group("value").strip()
            literals = STRING_LIT.findall(value)
            if literals:
                kind = classify(value, literals)
                for lit in literals:
                    results.append({
                        "file": path.name,
                        "line": lineno,
                        "target": f"{target}.{prop}",
                        "kind": kind,
                        "literal": lit,
                        "expression": value[:120],
                    })
            continue  # 한 줄에 set_text와 .text =가 동시에 있을 리 없음

        # 2) xxx.set_text("...") 패턴
        m = SET_TEXT_RE.search(line)
        if m:
            target = m.group("target")
            value = m.group("value").strip()
            literals = STRING_LIT.findall(value)
            if literals:
                kind = classify(value, literals)
                for lit in literals:
                    results.append({
                        "file": path.name,
                        "line": lineno,
                        "target": f"{target}.set_text",
                        "kind": kind,
                        "literal": lit,
                        "expression": value[:120],
                    })

    return results


def main():
    script_dir = Path(__file__).resolve().parent
    default_src = (script_dir / "../.tmp/pck_recovered/Scripts").resolve()
    default_out = (script_dir / "../.tmp/extracted_text/dynamic_strings.tsv").resolve()

    src_arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_src
    out_arg = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_out

    if not src_arg.exists():
        print(f"[ERROR] 입력 경로가 없습니다: {src_arg}")
        return 1

    # 파일/디렉토리 모두 지원
    if src_arg.is_file():
        gd_files = [src_arg] if src_arg.suffix == ".gd" else []
    else:
        gd_files = sorted(src_arg.rglob("*.gd"))

    if not gd_files:
        print(f"[ERROR] .gd 파일이 없습니다: {src_arg}")
        return 1

    print(f"입력: {src_arg}")
    print(f"출력: {out_arg}")
    print(f"대상: {len(gd_files)}개 .gd 파일")
    print()

    all_results = []
    for gd in gd_files:
        results = parse_gd(gd)
        all_results.extend(results)

    # 파일명 + 라인 기준 정렬
    all_results.sort(key=lambda r: (r["file"], r["line"]))

    # TSV 저장
    out_arg.parent.mkdir(parents=True, exist_ok=True)
    with open(out_arg, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["file", "line", "target", "kind", "literal", "expression"])
        for r in all_results:
            writer.writerow([r["file"], r["line"], r["target"], r["kind"], r["literal"], r["expression"]])

    print(f"추출 결과: {len(all_results)}개")
    print()

    # 통계
    kind_counts = {}
    for r in all_results:
        kind_counts[r["kind"]] = kind_counts.get(r["kind"], 0) + 1
    print("== Kind 분포 ==")
    for k, v in sorted(kind_counts.items(), key=lambda x: -x[1]):
        print(f"  {k:15s}: {v}")
    print()

    # 고유 리터럴 수
    unique_literals = set(r["literal"] for r in all_results)
    print(f"고유 리터럴: {len(unique_literals)}개")

    # concat/format 리터럴만 필터 (동적 텍스트의 힌트)
    dynamic_lits = set(r["literal"] for r in all_results if r["kind"] in ("concat", "format"))
    print(f"동적 패턴 조각: {len(dynamic_lits)}개")

    return 0


if __name__ == "__main__":
    sys.exit(main())
