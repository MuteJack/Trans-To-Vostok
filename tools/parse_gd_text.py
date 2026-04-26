"""
Parse .gd files to find UI text assignments and output as unified-format TSV.

Detected patterns:
    xxx.text = "..."                → .text property assignment
    xxx.tooltip_text = "..."        → tooltip
    xxx.placeholder_text = "..."    → placeholder
    gameData.tooltip = "..."        → interact text (custom)
    xxx.set_text("...")             → function call

Auto-classification:
    TRANSLATE   — contains English word of 2+ chars → translation target
    SKIP        — only symbols/units/numbers → no translation needed

Output:
    .tmp/parsed_text/Scripts/{filename}.gd.tsv
    unified columns: filename, filetype, location, parent, name, type, unique_id, text

Usage:
    python parse_gd_text.py [source_dir]
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
DICT_ENTRY_RE = re.compile(r'^\s*"(?P<key>[^"]+)"\s*:\s*"(?P<value>[^"]*)"')


def extract_func_first_arg(line: str, func_name: str) -> str | None:
    """Extract the first argument of a function call by paren counting.
    Correctly handles nested parens like str(int(x))."""
    idx = line.find(func_name + "(")
    if idx < 0:
        idx = line.find(func_name + " (")
        if idx < 0:
            return None
        idx += len(func_name) + 1
    else:
        idx += len(func_name)

    # position of opening paren after func_name
    paren_start = line.find("(", idx)
    if paren_start < 0:
        return None

    depth = 0
    in_str = False
    escape = False
    arg_start = paren_start + 1
    i = arg_start

    while i < len(line):
        c = line[i]
        if escape:
            escape = False
            i += 1
            continue
        if c == "\\":
            escape = True
            i += 1
            continue
        if c == '"':
            in_str = not in_str
            i += 1
            continue
        if in_str:
            i += 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                return line[arg_start:i].strip()
            depth -= 1
        elif c == "," and depth == 0:
            return line[arg_start:i].strip()
        i += 1
    return None

# config loaded from gd_list.json (defaults)
DEFAULT_CONFIG = {
    "properties": ["text", "tooltip_text", "placeholder_text", "hint_tooltip", "tooltip"],
    "functions": ["Loader.Message"],
    "units": ["kg", "mb", "px", "ms", "db", "hp", "rip", "str", "int", "var", "res"],
    "targets": ["Scripts"],
    "dict_extract": True,
}


def load_gd_config(config_path: Path) -> dict:
    """Load gd_list.json. Returns defaults if absent."""
    if not config_path.exists():
        print(f"[INFO] gd_list.json 없음, 기본 설정 사용")
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        # merge defaults
        for key, default in DEFAULT_CONFIG.items():
            if key not in data:
                data[key] = default
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] gd_list.json 읽기 실패: {e}, 기본 설정 사용")
        return dict(DEFAULT_CONFIG)


def build_assign_re(properties: list) -> re.Pattern:
    """Compile ASSIGN_RE from the properties list."""
    prop_alt = "|".join(re.escape(p) for p in properties)
    return re.compile(
        rf'(?P<target>[^\s=]+?)\s*\.\s*(?P<prop>{prop_alt})\s*(?<!=)=(?!=)\s*(?P<value>.+)$'
    )


def build_compare_re(properties: list) -> re.Pattern:
    """Detect comparison expressions like xxx.text == "...". """
    prop_alt = "|".join(re.escape(p) for p in properties)
    return re.compile(
        rf'(?P<target>[^\s=]+?)\s*\.\s*(?P<prop>{prop_alt})\s*==\s*(?P<value>"(?:[^"\\]|\\.)*")'
    )


# unified output columns (same as tscn/tres — property is left blank, for alignment with xlsx schema)
OUT_COLUMNS = ["method", "filename", "filetype", "location", "parent", "name", "type", "property", "unique_id", "text"]


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
            # function call "Func(...)" → extract only function name
            func_m = re.match(r'([A-Za-z_]\w*)\s*\(', token)
            if func_m:
                parts.append("{" + func_m.group(1) + "}")
            else:
                # strip str(x)/int(x) wrappers, then extract variable name
                var_name = re.sub(r'^(?:str|int|float)\s*\(\s*', '', token)
                var_name = re.sub(r'\s*\)\s*$', '', var_name)
                var_name = var_name.strip().split(".")[-1].split("[")[0]
                parts.append("{" + (var_name or "?") + "}")
    return "".join(parts)


def parse_gd(path: Path, rel_path: str = "", config: dict = None) -> list[dict]:
    """Parse one .gd file and return a list of translation-target rows."""
    if config is None:
        config = DEFAULT_CONFIG
    assign_re = build_assign_re(config["properties"])
    compare_re = build_compare_re(config["properties"])
    message_funcs = set(config["functions"])
    units = set(config["units"])
    do_dict = config.get("dict_extract", True)
    results = []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="replace")

    # rel_path: relative path from pck_recovered (without extension, e.g. "Scripts/Fire")
    if not rel_path:
        rel_path = "Scripts/" + path.stem

    # track dictionary blocks: starting at "var name = {" → ending at "}"
    current_dict_var: str = ""
    DICT_START_RE = re.compile(r'(?:var|const)\s+(?P<name>\w+)\s*=\s*\{')

    for lineno, raw_line in enumerate(content.splitlines(), 1):
        line = strip_comment(raw_line).rstrip()
        if not line:
            continue

        # track dictionary block start/end
        ds = DICT_START_RE.search(line)
        if ds:
            current_dict_var = ds.group("name")
        if current_dict_var and "}" in line and "{" not in line:
            current_dict_var = ""
            continue

        # match attempt 1: .text = ... / gameData.tooltip = ...
        m = assign_re.search(line)
        if not m:
            # set_text() — extract argument by paren counting
            st_target_m = re.search(r'([^\s]+?)\s*\.\s*set_text\s*\(', line)
            if st_target_m:
                arg = extract_func_first_arg(line, "set_text")
                if arg is not None:
                    target = st_target_m.group(1) + ".set_text"
                    value = arg
                else:
                    st_target_m = None
            if not st_target_m:
                # match attempt 1b: Loader.Message("...", ...) etc. — paren counting
                msg_found = False
                for func_name in message_funcs:
                    if func_name in line:
                        arg = extract_func_first_arg(line, func_name)
                        if arg is not None:
                            target = func_name
                            value = arg
                            msg_found = True
                            break
                if not msg_found:
                    # match attempt 2: xxx.text == "..." comparison (evidence of a displayed value)
                    cm = compare_re.search(line)
                    if cm:
                        lit = STRING_LIT.search(cm.group("value"))
                        if lit and is_translatable(lit.group(1), units):
                            results.append({
                                "method": "substr",
                                "filename": rel_path,
                                "filetype": "gd",
                                "location": "",
                                "parent": "",
                                "name": cm.group("target") + "." + cm.group("prop"),
                                "type": "compare",
                                "unique_id": str(lineno),
                                "text": lit.group(1),
                            })
                            continue
                    # match attempt 3: dictionary "key": "value" (inside block only)
                    if do_dict and current_dict_var:
                        dm = DICT_ENTRY_RE.search(line)
                        if dm:
                            dict_key = dm.group("key")
                            dict_val = dm.group("value")
                            if dict_val and is_translatable(dict_val, units):
                                results.append({
                                    "method": "substr",
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

        # literal: emit each literal as its own row
        # concat/format: emit one row with the pattern hint as text
        if kind == "literal":
            for lit in literals:
                if not is_translatable(lit, units):
                    continue
                results.append({
                    "method": "substr",
                    "filename": rel_path,
                    "filetype": "gd",
                    "location": "",
                    "parent": "",
                    "name": target,
                    "type": kind,
                    "unique_id": str(lineno),
                    "text": lit,
                })
        elif kind in ("concat", "format", "literal-multi"):
            # only when at least one literal is a translation target
            if not any(is_translatable(lit, units) for lit in literals):
                continue
            pattern = build_pattern_hint(value)
            # patterns made up only of placeholders are not translation targets
            if not re.sub(r'\{[^}]*\}', '', pattern).strip():
                continue
            results.append({
                "method": "pattern",
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

    # load gd_list.json
    config_path = script_dir / "gd_list.json"
    config = load_gd_config(config_path)
    print(f"설정: {config_path.name}")
    print(f"  properties: {config['properties']}")
    print(f"  functions:  {config['functions']}")
    print(f"  targets:    {config['targets']}")
    print(f"  dict:       {config['dict_extract']}")
    print()

    pck_root = (mod_root / ".tmp" / "pck_recovered").resolve()
    output_dir = (mod_root / ".tmp" / "parsed_text").resolve()

    # collect source directories from targets
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
        # relative path from pck_recovered (without extension)
        try:
            rel = gd.resolve().relative_to(pck_root)
        except ValueError:
            rel = Path(gd.name)
        rel_no_ext = rel.with_suffix("").as_posix()  # e.g., "Scripts/Fire"

        rows = parse_gd(gd, rel_no_ext, config)
        if not rows:
            continue
        # write per-file .gd.tsv (preserve directory structure)
        out_path = output_dir / (rel.as_posix() + ".tsv")  # Scripts/Fire.gd.tsv
        write_tsv(out_path, rows)
        total_files += 1
        total_rows += len(rows)
        all_rows.extend(rows)
        print(f"  [OK] {gd.name}  ({len(rows)}개)")

    # combined output (only when join field is set)
    join_name = config.get("join", "")
    if join_name and all_rows:
        joined_path = output_dir / f"{join_name}.gd.joined.tsv"
        write_tsv(joined_path, all_rows)
        print(f"\n  합본: {joined_path.relative_to(output_dir)}")

    print()
    print(f"완료: {total_files}개 파일, {total_rows}개 엔트리")

    # statistics
    literals = [r for r in all_rows if r["type"] == "literal"]
    dicts = [r for r in all_rows if r["type"] == "dict"]
    patterns = [r for r in all_rows if r["type"] in ("concat", "format", "literal-multi")]
    print(f"  literal: {len(literals)}개, dict: {len(dicts)}개, pattern 후보: {len(patterns)}개")

    return 0


if __name__ == "__main__":
    sys.exit(main())
