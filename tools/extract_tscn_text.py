"""
.tscn 파일에서 텍스트를 추출해 TSV로 저장.

컬럼 순서: name, type, parent, unique_id, text

사용법:
    python extract_tscn_text.py                    # 기본 입력/출력 경로 사용
    python extract_tscn_text.py <source_dir>       # 입력 디렉토리 지정
    python extract_tscn_text.py <src> <out>        # 입력 + 출력 지정

기본값 (tools/ 기준):
    source_dir = ../.tmp/pck_recovered/
    output_dir = ../.tmp/extracted_text/

출력:
    입력 디렉토리의 .tscn 파일마다 동일한 구조로 .tsv 생성.
    (예: pck_recovered/Scenes/Menu.tscn → extracted_text/Scenes/Menu.tsv)
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


def _decode_attrs(header: str) -> dict:
    """[node name="X" type="Y" parent="Z" unique_id=123] 의 속성 파싱."""
    attrs = {}
    # 키=값 패턴: 값은 "큰따옴표" 또는 숫자/무인용 모두 지원
    pattern = re.compile(r'(\w+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^\s\]]+))')
    for m in pattern.finditer(header):
        key = m.group(1)
        val = m.group(2) if m.group(2) is not None else m.group(3)
        # 이스케이프 해제 (\" → ", \\ → \)
        if m.group(2) is not None:
            val = val.replace('\\"', '"').replace("\\\\", "\\")
        attrs[key] = val
    return attrs


def _extract_text_property(body: str) -> str | None:
    """
    노드 본문에서 'text = "..."' 를 찾아 값을 반환.
    여러 줄 문자열과 이스케이프 처리 지원.
    """
    # "text = " 시작 위치 찾기 (라인 시작 기준)
    m = re.search(r'^text\s*=\s*"', body, re.MULTILINE)
    if not m:
        return None

    i = m.end()
    result = []
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            if nxt == "n":
                result.append("\n")
            elif nxt == "t":
                result.append("\t")
            elif nxt == "r":
                result.append("\r")
            elif nxt == '"':
                result.append('"')
            elif nxt == "\\":
                result.append("\\")
            else:
                result.append(nxt)
            i += 2
            continue
        if c == '"':
            # 닫는 따옴표 발견
            return "".join(result)
        result.append(c)
        i += 1
    # 닫는 따옴표를 못 찾았으면 파싱 실패
    return None


def parse_tscn(path: Path) -> list[dict]:
    """하나의 .tscn 파일을 파싱해 노드 리스트 반환."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")

    nodes = []
    # [node ...] 헤더를 모두 찾음
    node_header_re = re.compile(r'^\[node\s+([^\]]+)\]', re.MULTILINE)
    matches = list(node_header_re.finditer(text))

    # 유효한 TSCN 섹션 키워드 (이것들로 시작해야 "진짜" 섹션 구분자)
    # changelog의 [ADDED] 같은 텍스트 내용과 구분하기 위함.
    section_re = re.compile(
        r'\n\[(node|ext_resource|sub_resource|connection|editable|resource|gd_scene|gd_resource)\b'
    )

    for idx, m in enumerate(matches):
        attrs = _decode_attrs(m.group(1))

        # 본문 = 현재 헤더 끝 ~ 다음 섹션 시작
        body_start = m.end()
        search_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        section_m = section_re.search(text, body_start, search_end)
        body_end = section_m.start() if section_m else search_end

        body = text[body_start:body_end]
        text_val = _extract_text_property(body)

        nodes.append({
            "name": attrs.get("name", ""),
            "type": attrs.get("type", ""),
            "parent": attrs.get("parent", ""),
            "unique_id": attrs.get("unique_id", ""),
            "text": text_val if text_val is not None else "",
        })

    return nodes


def process_file(src_tscn: Path, out_tsv: Path, location: str) -> tuple[int, int]:
    """
    파일 하나를 파싱해 TSV로 저장.
    텍스트가 있는 노드만 출력 (빈 노드는 스킵).
    반환: (전체 노드 수, 텍스트 있는 노드 수)
    """
    nodes = parse_tscn(src_tscn)
    text_nodes = [n for n in nodes if n["text"]]

    # 텍스트가 하나도 없으면 파일 생성 안 함
    if not text_nodes:
        return len(nodes), 0

    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_tsv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["location", "name", "type", "parent", "unique_id", "text"])
        for n in text_nodes:
            writer.writerow([location, n["name"], n["type"], n["parent"], n["unique_id"], n["text"]])

    return len(nodes), len(text_nodes)


def main():
    script_dir = Path(__file__).resolve().parent
    # script_dir = mods/Trans To Vostok/tools
    # ../.tmp = mods/Trans To Vostok/.tmp
    default_src = (script_dir / "../.tmp/pck_recovered").resolve()
    default_out = (script_dir / "../.tmp/extracted_text").resolve()

    src_arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_src
    out_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_out

    if not src_arg.exists():
        print(f"[ERROR] 입력 경로가 없습니다: {src_arg}")
        return 1

    # 파일 하나 또는 디렉토리 모두 지원
    if src_arg.is_file():
        if src_arg.suffix.lower() != ".tscn":
            print(f"[ERROR] .tscn 파일이 아닙니다: {src_arg}")
            return 1
        tscn_files = [src_arg]
        src_dir = src_arg.parent
    else:
        src_dir = src_arg
        tscn_files = sorted(src_arg.rglob("*.tscn"))
        if not tscn_files:
            print(f"[ERROR] .tscn 파일을 찾을 수 없습니다: {src_arg}")
            return 1

    print(f"입력: {src_dir}")
    print(f"출력: {out_dir}")
    print(f"대상 파일: {len(tscn_files)}개")
    print()

    total_nodes = 0
    total_texts = 0
    processed = 0
    failed = 0

    for tscn in tscn_files:
        rel_tscn = tscn.relative_to(src_dir)
        # location = 확장자 제거 + 슬래시 통일 (예: "Scenes/Menu", "UI/Settings")
        location = rel_tscn.with_suffix("").as_posix()
        out_path = out_dir / rel_tscn.with_suffix(".tsv")
        try:
            n, t = process_file(tscn, out_path, location)
            total_nodes += n
            total_texts += t
            processed += 1
            if t > 0:
                print(f"  [OK] {location}  ({t}개 텍스트 / {n}개 노드)")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {location}: {e}")

    print()
    print(f"완료: {processed}개 파일 처리 (실패 {failed}개)")
    print(f"  총 노드: {total_nodes}")
    print(f"  텍스트 있는 노드: {total_texts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
