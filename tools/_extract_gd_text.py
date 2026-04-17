"""
[테스트] .gd 파일에서 UI 텍스트 할당을 찾아 분류.

감지 패턴:
    xxx.text = "..."                → .text 속성 할당
    xxx.tooltip_text = "..."        → 툴팁
    xxx.placeholder_text = "..."    → 플레이스홀더
    gameData.tooltip = "..."        → 인터랙트 텍스트 (커스텀)
    xxx.set_text("...")             → 함수 호출

분류:
    literal     — 순수 문자열 리터럴 (번역 대상 후보)
    concat      — 문자열 + 변수 결합 (패턴 후보)
    format      — 포맷 문자열 (패턴/숫자)
    literal-multi — 여러 리터럴 포함

자동 판정:
    TRANSLATE   — 2글자 이상 영어 단어 포함 → 번역 대상
    SKIP        — 기호/단위/숫자만 → 번역 불필요

사용법:
    python _extract_gd_text.py [source_dir]

기본값:
    source_dir = ../.tmp/pck_recovered/Scripts/
    출력: ../.tmp/extracted_text/gd_dynamic_strings.tsv
"""
import csv
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


# 문자열 리터럴 추출 (이스케이프 인식)
STRING_LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')

# 주석 제거
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


# 텍스트 할당 패턴
ASSIGN_PROPS = ["text", "tooltip_text", "placeholder_text", "hint_tooltip", "tooltip"]
PROP_ALT = "|".join(ASSIGN_PROPS)

ASSIGN_RE = re.compile(
    rf'(?P<target>[^\s=]+?)\s*\.\s*(?P<prop>{PROP_ALT})\s*=\s*(?P<value>.+)$'
)

SET_TEXT_RE = re.compile(r'(?P<target>[^\s]+?)\s*\.\s*set_text\s*\(\s*(?P<value>.+?)\s*\)')

# 번역 판정용
UNITS = {"kg", "mb", "px", "ms", "db", "hp", "rip", "str", "int", "var", "res"}


def classify(value: str, literals: list[str]) -> str:
    if not literals:
        return "none"
    v = value.strip()
    if len(literals) == 1:
        only = '"' + literals[0].replace('\\', '\\\\').replace('"', '\\"') + '"'
        if v == only:
            return "literal"
    if "+" in v:
        return "concat"
    if "%" in v:
        return "format"
    return "literal-multi"


def is_translatable(lit: str) -> bool:
    """2글자 이상 영어 단어가 있고 단위가 아니면 번역 대상."""
    words = re.findall(r'[A-Za-z]{2,}', lit)
    meaningful = [w for w in words if w.lower() not in UNITS]
    return len(meaningful) > 0


def build_pattern_hint(value: str) -> str:
    """concat 표현식에서 패턴 힌트를 생성. 변수를 {var}로 치환."""
    parts = []
    i = 0
    in_str = False
    current = ""

    tokens = re.split(r'\s*\+\s*', value)
    for token in tokens:
        token = token.strip()
        m = STRING_LIT.match(token)
        if m:
            parts.append(m.group(1))
        else:
            # 변수명 추출
            var_name = re.sub(r'str\(|int\(|float\(|\)', '', token)
            var_name = var_name.strip().split(".")[-1].split("[")[0]
            if var_name:
                parts.append("{" + var_name + "}")
            else:
                parts.append("{?}")

    return "".join(parts)


def parse_gd(path: Path) -> list[dict]:
    results = []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="replace")

    for lineno, raw_line in enumerate(content.splitlines(), 1):
        line = strip_comment(raw_line).rstrip()
        if not line:
            continue

        m = ASSIGN_RE.search(line)
        if m:
            target = m.group("target")
            prop = m.group("prop")
            value = m.group("value").strip()
            literals = STRING_LIT.findall(value)
            if literals:
                kind = classify(value, literals)
                pattern_hint = build_pattern_hint(value) if kind in ("concat", "format") else ""
                translatable = any(is_translatable(lit) for lit in literals)
                for lit in literals:
                    results.append({
                        "file": path.name,
                        "line": lineno,
                        "target": f"{target}.{prop}",
                        "kind": kind,
                        "translatable": "TRANSLATE" if translatable else "SKIP",
                        "literal": lit,
                        "pattern_hint": pattern_hint,
                        "expression": value[:120],
                    })
            continue

        m = SET_TEXT_RE.search(line)
        if m:
            target = m.group("target")
            value = m.group("value").strip()
            literals = STRING_LIT.findall(value)
            if literals:
                kind = classify(value, literals)
                pattern_hint = build_pattern_hint(value) if kind in ("concat", "format") else ""
                translatable = any(is_translatable(lit) for lit in literals)
                for lit in literals:
                    results.append({
                        "file": path.name,
                        "line": lineno,
                        "target": f"{target}.set_text",
                        "kind": kind,
                        "translatable": "TRANSLATE" if translatable else "SKIP",
                        "literal": lit,
                        "pattern_hint": pattern_hint,
                        "expression": value[:120],
                    })

    return results


OUT_COLUMNS = ["file", "line", "target", "kind", "translatable", "literal", "pattern_hint", "expression"]


def main():
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    default_src = (mod_root / ".tmp" / "pck_recovered" / "Scripts").resolve()
    default_out = (mod_root / ".tmp" / "extracted_text" / "gd_dynamic_strings.tsv").resolve()

    src_arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_src
    out_arg = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_out

    if not src_arg.exists():
        print(f"[ERROR] 입력 경로가 없습니다: {src_arg}")
        return 1

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
        all_results.extend(parse_gd(gd))

    all_results.sort(key=lambda r: (r["file"], r["line"]))

    # TSV 저장
    out_arg.parent.mkdir(parents=True, exist_ok=True)
    with open(out_arg, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(OUT_COLUMNS)
        for r in all_results:
            writer.writerow([r.get(c, "") for c in OUT_COLUMNS])

    # 통계
    translate_count = sum(1 for r in all_results if r["translatable"] == "TRANSLATE")
    skip_count = sum(1 for r in all_results if r["translatable"] == "SKIP")

    kind_counts = {}
    for r in all_results:
        kind_counts[r["kind"]] = kind_counts.get(r["kind"], 0) + 1

    print(f"추출 결과: {len(all_results)}개")
    print()
    print("== Kind 분포 ==")
    for k, v in sorted(kind_counts.items(), key=lambda x: -x[1]):
        print(f"  {k:15s}: {v}")
    print()
    print(f"== 판정 ==")
    print(f"  TRANSLATE: {translate_count}")
    print(f"  SKIP:      {skip_count}")
    print()

    # 번역 대상만 요약
    unique_translate = set()
    for r in all_results:
        if r["translatable"] == "TRANSLATE":
            if r["kind"] == "literal":
                unique_translate.add(("literal", r["literal"]))
            elif r["pattern_hint"]:
                unique_translate.add(("pattern", r["pattern_hint"]))

    print(f"== 고유 번역 대상 (중복 제거) ==")
    literals = sorted(v for t, v in unique_translate if t == "literal")
    patterns = sorted(v for t, v in unique_translate if t == "pattern")

    if literals:
        print(f"\n  리터럴 ({len(literals)}개):")
        for lit in literals:
            print(f"    {lit!r}")

    if patterns:
        print(f"\n  패턴 후보 ({len(patterns)}개):")
        for pat in patterns:
            print(f"    {pat!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
