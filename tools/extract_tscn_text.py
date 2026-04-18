"""
.tscn 파일에서 텍스트를 추출해 TSV로 저장.

컬럼 순서: filename, filetype, location, parent, name, type, unique_id, text

사용법:
    python extract_tscn_text.py                    # 기본 입력/출력 경로 사용
    python extract_tscn_text.py <source_dir>       # 입력 디렉토리 지정
    python extract_tscn_text.py <src> <out>        # 입력 + 출력 지정

기본값 (tools/ 기준):
    source_dir = ../.tmp/pck_recovered/
    output_dir = ../.tmp/extracted_text/

출력:
    입력 디렉토리의 .tscn 파일마다 .tscn.tsv (이중 확장자) 생성.
    (예: pck_recovered/Scenes/Menu.tscn → extracted_text/Scenes/Menu.tscn.tsv)

출력 필드:
    filename   확장자 없는 상대 경로 (예: "Scenes/Menu")
    filetype   "tscn"
    location   매칭에 사용되는 씬 이름 — .tscn 엔트리는 filename과 동일
    parent     씬 내 부모 노드 경로
    name       노드 이름
    type       노드 클래스
    unique_id  .tscn 내부 식별자
    text       추출된 원문
"""
import csv
import json
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


def _extract_string_property(body: str, prop_name: str) -> str | None:
    """
    노드 본문에서 'prop_name = "..."' 를 찾아 값을 반환.
    여러 줄 문자열과 이스케이프 처리 지원.
    """
    m = re.search(rf'^{re.escape(prop_name)}\s*=\s*"', body, re.MULTILINE)
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
            return "".join(result)
        result.append(c)
        i += 1
    return None


def parse_tscn(path: Path, extra_properties: list[str] | None = None) -> list[dict]:
    """하나의 .tscn 파일을 파싱해 노드 리스트 반환.
    extra_properties가 있으면 해당 속성도 별도 행으로 추출."""
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
        text_val = _extract_string_property(body, "text")

        nodes.append({
            "name": attrs.get("name", ""),
            "type": attrs.get("type", ""),
            "parent": attrs.get("parent", ""),
            "unique_id": attrs.get("unique_id", ""),
            "text": text_val if text_val is not None else "",
            "_prop": "text",
        })

        if extra_properties:
            for prop in extra_properties:
                val = _extract_string_property(body, prop)
                if val:
                    nodes.append({
                        "name": attrs.get("name", ""),
                        "type": attrs.get("type", ""),
                        "parent": attrs.get("parent", ""),
                        "unique_id": attrs.get("unique_id", ""),
                        "text": val,
                        "_prop": prop,
                    })

    return nodes


OUT_COLUMNS = ["filename", "filetype", "location", "parent", "name", "type", "property", "unique_id", "text"]


def process_file(src_tscn: Path, out_tsv: Path, filename: str,
                  extra_properties: list[str] | None = None) -> tuple[int, int]:
    """
    파일 하나를 파싱해 TSV로 저장.
    텍스트가 있는 노드만 출력 (빈 노드는 스킵).
    filename 은 확장자 없는 상대 경로. .tscn 엔트리에서는 location 도 동일값.
    반환: (전체 노드 수, 텍스트 있는 노드 수)
    """
    nodes = parse_tscn(src_tscn, extra_properties)
    text_nodes = [n for n in nodes if n["text"]]

    # 텍스트가 하나도 없으면 파일 생성 안 함
    if not text_nodes:
        return len(nodes), 0

    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_tsv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(OUT_COLUMNS)
        for n in text_nodes:
            writer.writerow([
                filename,          # filename (확장자 없음)
                "tscn",            # filetype
                filename,          # location (.tscn 엔트리는 filename 과 동일)
                n["parent"],
                n["name"],
                n["type"],
                n.get("_prop", "text"),  # property (text / containerName / title / info 등)
                n["unique_id"],
                n["text"],
            ])

    return len(nodes), len(text_nodes)


def load_tscn_config(config_path: Path) -> dict:
    """
    tscn_list.json 로드. 없으면 기본값 반환.

    스키마:
        extra_properties: [str]   — 전체 .tscn 에 적용할 추가 프로퍼티
        groups: [                 — 특정 파일에만 적용할 추가 프로퍼티
            {
                "name": "...",            (선택, 표시용)
                "targets": ["UI/Interface.tscn", ...],
                "extra_properties": ["type", ...]
            }
        ]
    """
    default = {"extra_properties": [], "groups": []}
    if not config_path.exists():
        print(f"[INFO] tscn_list.json 없음, 기본 설정 사용")
        return default
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        for key, val in default.items():
            if key not in data:
                data[key] = val
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] tscn_list.json 읽기 실패: {e}, 기본 설정 사용")
        return default


def _build_per_file_extras(config: dict) -> dict:
    """
    config 의 groups 를 파일 상대경로 → 추가 프로퍼티 리스트 매핑으로 변환.
    targets 에 지정된 파일 경로(예: "UI/Interface.tscn")를 키로 사용.
    """
    per_file: dict[str, list[str]] = {}
    for g in config.get("groups", []):
        props = g.get("extra_properties", [])
        if not props:
            continue
        for target in g.get("targets", []):
            target_posix = target.replace("\\", "/")
            if target_posix in per_file:
                per_file[target_posix].extend(props)
            else:
                per_file[target_posix] = list(props)
    return per_file


def main():
    script_dir = Path(__file__).resolve().parent
    # script_dir = mods/Trans To Vostok/tools
    # ../.tmp = mods/Trans To Vostok/.tmp
    default_src = (script_dir / "../.tmp/pck_recovered").resolve()
    default_out = (script_dir / "../.tmp/extracted_text").resolve()

    src_arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_src
    out_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_out

    # tscn_list.json 로드
    config_path = script_dir / "tscn_list.json"
    config = load_tscn_config(config_path)
    global_extra = config.get("extra_properties", [])
    per_file_extras = _build_per_file_extras(config)
    print(f"설정: {config_path.name}")
    print(f"  전역 extra_properties: {global_extra}")
    if per_file_extras:
        print(f"  파일별 extra_properties: {len(per_file_extras)}개 파일")
    print()

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
        rel_posix = rel_tscn.as_posix()
        # filename = 확장자 없는 상대 경로 (예: "Scenes/Menu")
        # location = 매칭 키 — .tscn 엔트리는 filename 과 동일
        filename = rel_tscn.with_suffix("").as_posix()
        # 출력 파일: 원본 확장자 포함한 이중 확장자 (예: "Scenes/Menu.tscn.tsv")
        out_path = out_dir / (rel_posix + ".tsv")
        # 전역 + 파일별 extra_properties 병합
        file_extra = per_file_extras.get(rel_posix, [])
        combined_extra = list(global_extra) + file_extra if (global_extra or file_extra) else None
        try:
            n, t = process_file(tscn, out_path, filename, combined_extra)
            total_nodes += n
            total_texts += t
            processed += 1
            if t > 0:
                print(f"  [OK] {rel_tscn.as_posix()}  ({t}개 텍스트 / {n}개 노드)")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {rel_tscn.as_posix()}: {e}")

    print()
    print(f"완료: {processed}개 파일 처리 (실패 {failed}개)")
    print(f"  총 노드: {total_nodes}")
    print(f"  텍스트 있는 노드: {total_texts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
