"""
[테스트] .gd 파일에서 UI 텍스트 할당을 찾아 통일 포맷 TSV 로 출력.

감지 패턴:
    xxx.text = "..."                → .text 속성 할당
    xxx.tooltip_text = "..."        → 툴팁
    xxx.placeholder_text = "..."    → 플레이스홀더
    gameData.tooltip = "..."        → 인터랙트 텍스트 (커스텀)
    xxx.set_text("...")             → 함수 호출

자동 판정:
    TRANSLATE   — 2글자 이상 영어 단어 포함 → 번역 대상
    SKIP        — 기호/단위/숫자만 → 번역 불필요

출력:
    .tmp/_extracted_text/Scripts/{파일명}.gd.tsv
    통일 컬럼: filename, filetype, location, parent, name, type, unique_id, text

사용법:
    python _extract_gd_text.py [source_dir]
"""
import csv
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


STRING_LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')
SET_TEXT_RE = re.compile(r'(?P<target>[^\s]+?)\s*\.\s*set_text\s*\(\s*(?P<value>.+?)\s*\)')
MESSAGE_RE = re.compile(r'(?P<target>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(\s*(?P<value>"[^"]*"(?:\s*\+\s*.+?)?)\s*[,)]')
DICT_ENTRY_RE = re.compile(r'^\s*"(?P<key>[^"]+)"\s*:\s*"(?P<value>[^"]*)"')

# gd_list.json 에서 로드되는 설정 (기본값)
DEFAULT_CONFIG = {
    "properties": ["text", "tooltip_text", "placeholder_text", "hint_tooltip", "tooltip"],
    "functions": ["Loader.Message"],
    "units": ["kg", "mb", "px", "ms", "db", "hp", "rip", "str", "int", "var", "res"],
    "targets": ["Scripts"],
    "dict_extract": True,
}


def load_gd_config(config_path: Path) -> dict:
    """gd_list.json 을 로드. 없으면 기본값 반환."""
    if not config_path.exists():
        print(f"[INFO] gd_list.json 없음, 기본 설정 사용")
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        # 기본값 병합
        for key, default in DEFAULT_CONFIG.items():
            if key not in data:
                data[key] = default
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] gd_list.json 읽기 실패: {e}, 기본 설정 사용")
        return dict(DEFAULT_CONFIG)


def build_assign_re(properties: list) -> re.Pattern:
    """properties 목록으로 ASSIGN_RE 컴파일."""
    prop_alt = "|".join(re.escape(p) for p in properties)
    return re.compile(
        rf'(?P<target>[^\s=]+?)\s*\.\s*(?P<prop>{prop_alt})\s*=\s*(?P<value>.+)$'
    )

# 통일 출력 컬럼 (tscn/tres 와 동일)
OUT_COLUMNS = ["filename", "filetype", "location", "parent", "name", "type", "unique_id", "text"]


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


def is_translatable(lit: str, units: set) -> bool:
    words = re.findall(r'[A-Za-z]{2,}', lit)
    meaningful = [w for w in words if w.lower() not in units]

    return len(meaningful) > 0


def classify_kind(value: str, literals: list[str]) -> str:
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


def build_pattern_hint(value: str) -> str:
    tokens = re.split(r'\s*\+\s*', value)
    parts = []
    for token in tokens:
        token = token.strip()
        m = STRING_LIT.match(token)
        if m:
            parts.append(m.group(1))
        else:
            # 함수 호출 "Func(...)" → 함수명만 추출
            func_m = re.match(r'([A-Za-z_]\w*)\s*\(', token)
            if func_m:
                parts.append("{" + func_m.group(1) + "}")
            else:
                # str(x), int(x) 래퍼 제거 후 변수명 추출
                var_name = re.sub(r'^(?:str|int|float)\s*\(\s*', '', token)
                var_name = re.sub(r'\s*\)\s*$', '', var_name)
                var_name = var_name.strip().split(".")[-1].split("[")[0]
                parts.append("{" + (var_name or "?") + "}")
    return "".join(parts)


def parse_gd(path: Path, rel_path: str = "", config: dict = None) -> list[dict]:
    """하나의 .gd 파일을 파싱해 번역 대상 행 리스트 반환."""
    if config is None:
        config = DEFAULT_CONFIG
    assign_re = build_assign_re(config["properties"])
    message_funcs = set(config["functions"])
    units = set(config["units"])
    do_dict = config.get("dict_extract", True)
    results = []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="replace")

    # rel_path: pck_recovered 기준 상대 경로 (확장자 제외, e.g. "Scripts/Fire")
    if not rel_path:
        rel_path = "Scripts/" + path.stem

    # 딕셔너리 블록 추적: "var name = {" 로 시작 → "}" 로 끝날 때까지
    current_dict_var: str = ""
    DICT_START_RE = re.compile(r'(?:var|const)\s+(?P<name>\w+)\s*=\s*\{')

    for lineno, raw_line in enumerate(content.splitlines(), 1):
        line = strip_comment(raw_line).rstrip()
        if not line:
            continue

        # 딕셔너리 블록 시작/끝 추적
        ds = DICT_START_RE.search(line)
        if ds:
            current_dict_var = ds.group("name")
        if current_dict_var and "}" in line and "{" not in line:
            current_dict_var = ""
            continue

        # 매칭 시도 1: .text = ... / gameData.tooltip = ...
        m = assign_re.search(line)
        if not m:
            m2 = SET_TEXT_RE.search(line)
            if m2:
                target = m2.group("target") + ".set_text"
                value = m2.group("value").strip()
            else:
                # 매칭 시도 1b: Loader.Message("...", ...) 등
                msg_found = False
                for func_name in message_funcs:
                    if func_name in line:
                        mm = MESSAGE_RE.search(line)
                        if mm and mm.group("target") == func_name:
                            target = func_name
                            value = mm.group("value").strip()
                            msg_found = True
                            break
                if not msg_found:
                    # 매칭 시도 2: 딕셔너리 "key": "value" (블록 안에서만)
                    if do_dict and current_dict_var:
                        dm = DICT_ENTRY_RE.search(line)
                        if dm:
                            dict_key = dm.group("key")
                            dict_val = dm.group("value")
                            if dict_val and is_translatable(dict_val, units):
                                results.append({
                                    "filename": rel_path,
                                    "filetype": "gd",
                                    "location": "",
                                    "parent": "",
                                    "name": f"{current_dict_var}.{dict_key}",
                                    "type": "dict",
                                    "unique_id": str(lineno),
                                    "text": dict_val,
                                })
                    continue
        else:
            target = m.group("target") + "." + m.group("prop")
            value = m.group("value").strip()

        literals = STRING_LIT.findall(value)
        if not literals:
            continue

        kind = classify_kind(value, literals)

        # literal: 각 리터럴을 개별 행으로
        # concat/format: 패턴 힌트를 text로 (1행)
        if kind == "literal":
            for lit in literals:
                if not is_translatable(lit, units):
                    continue
                results.append({
                    "filename": rel_path,
                    "filetype": "gd",
                    "location": "",
                    "parent": "",
                    "name": target,     # 변수명 (메타데이터)
                    "type": kind,       # literal/concat/format
                    "unique_id": str(lineno),  # 줄 번호 (참고용)
                    "text": lit,
                })
        elif kind in ("concat", "format", "literal-multi"):
            # 번역 대상 리터럴이 있는 경우만
            if not any(is_translatable(lit, units) for lit in literals):
                continue
            pattern = build_pattern_hint(value)
            results.append({
                "filename": rel_path,
                "filetype": "gd",
                "location": "",
                "parent": "",
                "name": target,
                "type": kind,
                "unique_id": str(lineno),
                "text": pattern,
            })

    return results


def write_tsv(out_path: Path, rows: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(OUT_COLUMNS)
            for row in rows:
                writer.writerow([row.get(c, "") for c in OUT_COLUMNS])
        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def main():
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent

    # gd_list.json 로드
    config_path = script_dir / "gd_list.json"
    config = load_gd_config(config_path)
    print(f"설정: {config_path.name}")
    print(f"  properties: {config['properties']}")
    print(f"  functions:  {config['functions']}")
    print(f"  targets:    {config['targets']}")
    print(f"  dict:       {config['dict_extract']}")
    print()

    pck_root = (mod_root / ".tmp" / "pck_recovered").resolve()
    output_dir = (mod_root / ".tmp" / "extracted_text").resolve()

    # targets 에서 소스 디렉토리 수집
    if len(sys.argv) > 1:
        src_dirs = [Path(sys.argv[1]).resolve()]
    else:
        src_dirs = [(pck_root / t).resolve() for t in config["targets"]]

    gd_files = []
    for src in src_dirs:
        if not src.exists():
            print(f"[WARN] 경로 없음: {src}")
            continue
        if src.is_file():
            if src.suffix == ".gd":
                gd_files.append(src)
        else:
            gd_files.extend(sorted(src.rglob("*.gd")))

    if not gd_files:
        print("[ERROR] .gd 파일이 없습니다")
        return 1

    print(f"출력: {output_dir}")
    print(f"대상: {len(gd_files)}개 .gd 파일")
    print()

    total_files = 0
    total_rows = 0
    all_rows: list[dict] = []

    for gd in gd_files:
        # pck_recovered 기준 상대 경로 (확장자 제외)
        try:
            rel = gd.resolve().relative_to(pck_root)
        except ValueError:
            rel = Path(gd.name)
        rel_no_ext = rel.with_suffix("").as_posix()  # e.g., "Scripts/Fire"

        rows = parse_gd(gd, rel_no_ext, config)
        if not rows:
            continue
        # 파일별 .gd.tsv 출력 (디렉토리 구조 유지)
        out_path = output_dir / (rel.as_posix() + ".tsv")  # Scripts/Fire.gd.tsv
        write_tsv(out_path, rows)
        total_files += 1
        total_rows += len(rows)
        all_rows.extend(rows)
        print(f"  [OK] {gd.name}  ({len(rows)}개)")

    # 합본 출력 (join 필드가 있을 때만)
    join_name = config.get("join", "")
    if join_name and all_rows:
        joined_path = output_dir / f"{join_name}.gd.joined.tsv"
        write_tsv(joined_path, all_rows)
        print(f"\n  합본: {joined_path.relative_to(output_dir)}")

    print()
    print(f"완료: {total_files}개 파일, {total_rows}개 엔트리")

    # 통계
    literals = [r for r in all_rows if r["type"] == "literal"]
    dicts = [r for r in all_rows if r["type"] == "dict"]
    patterns = [r for r in all_rows if r["type"] in ("concat", "format", "literal-multi")]
    print(f"  literal: {len(literals)}개, dict: {len(dicts)}개, pattern 후보: {len(patterns)}개")

    return 0


if __name__ == "__main__":
    sys.exit(main())
