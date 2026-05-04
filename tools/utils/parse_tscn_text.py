"""
Parse .tscn files and save translation-target text as TSV.

Column order: filename, filetype, location, parent, name, type, unique_id, text

Usage:
    python parse_tscn_text.py                    # use default input/output paths
    python parse_tscn_text.py <source_dir>       # specify input directory
    python parse_tscn_text.py <src> <out>        # specify input + output

Defaults:
    source_dir = <mod_root>/.tmp/pck_recovered/
    output_dir = <mod_root>/.tmp/parsed_text/

Output:
    For each .tscn file under the input directory, generate a .tscn.tsv (double extension).
    (e.g., pck_recovered/Scenes/Menu.tscn → parsed_text/Scenes/Menu.tscn.tsv)

Output fields:
    filename   relative path without extension (e.g. "Scenes/Menu")
    filetype   "tscn"
    location   scene name used for matching — for .tscn entries, same as filename
    parent     parent node path within the scene
    name       node name
    type       node class
    unique_id  .tscn internal identifier
    text       extracted source text
"""
import csv
import json
import re
import sys
from pathlib import Path

# Windows console Korean output support
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


def _decode_attrs(header: str) -> dict:
    """Parse attributes from [node name="X" type="Y" parent="Z" unique_id=123]."""
    attrs = {}
    # key=value pattern: value supports both "double quotes" and unquoted/numeric forms
    pattern = re.compile(r'(\w+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^\s\]]+))')
    for m in pattern.finditer(header):
        key = m.group(1)
        val = m.group(2) if m.group(2) is not None else m.group(3)
        # un-escape (\" → ", \\ → \)
        if m.group(2) is not None:
            val = val.replace('\\"', '"').replace("\\\\", "\\")
        attrs[key] = val
    return attrs


def _extract_string_property(body: str, prop_name: str) -> str | None:
    """
    Find 'prop_name = "..."' in the node body and return its value.
    Supports multi-line strings and escapes.
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
    """Parse one .tscn file and return a list of nodes.
    If extra_properties is given, those properties are also extracted as separate rows."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")

    nodes = []
    # find all [node ...] headers
    node_header_re = re.compile(r'^\[node\s+([^\]]+)\]', re.MULTILINE)
    matches = list(node_header_re.finditer(text))

    # valid TSCN section keywords (only sections starting with these are "real" separators)
    # used to distinguish from text content like [ADDED] in a changelog.
    section_re = re.compile(
        r'\n\[(node|ext_resource|sub_resource|connection|editable|resource|gd_scene|gd_resource)\b'
    )

    for idx, m in enumerate(matches):
        attrs = _decode_attrs(m.group(1))

        # body = end of current header ~ start of next section
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
    Parse one file and save as TSV.
    Only emit nodes that have text (skip empty nodes).
    filename is the relative path without extension. For .tscn entries, location is the same value.
    Returns: (total node count, node count with text)
    """
    nodes = parse_tscn(src_tscn, extra_properties)
    text_nodes = [n for n in nodes if n["text"]]

    # do not create a file if there is no text
    if not text_nodes:
        return len(nodes), 0

    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_tsv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(OUT_COLUMNS)
        for n in text_nodes:
            writer.writerow([
                filename,          # filename (without extension)
                "tscn",            # filetype
                filename,          # location (same as filename for .tscn entries)
                n["parent"],
                n["name"],
                n["type"],
                n.get("_prop", "text"),  # property (text / containerName / title / info, etc.)
                n["unique_id"],
                n["text"],
            ])

    return len(nodes), len(text_nodes)


def load_tscn_config(config_path: Path) -> dict:
    """
    Load parse_list_tscn.json. Returns defaults if absent.

    Schema:
        extra_properties: [str]   — extra properties applied to all .tscn files
        groups: [                 — extra properties applied only to specific files
            {
                "name": "...",            (optional, for display)
                "targets": ["UI/Interface.tscn", ...],
                "extra_properties": ["type", ...]
            }
        ]
    """
    default = {"extra_properties": [], "groups": []}
    if not config_path.exists():
        print(f"[INFO] parse_list_tscn.json not found, using default config")
        return default
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        for key, val in default.items():
            if key not in data:
                data[key] = val
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] Failed to read parse_list_tscn.json: {e}, using default config")
        return default


def _build_per_file_extras(config: dict) -> dict:
    """
    Convert config's groups into a mapping of file relative path → list of extra properties.
    The file path specified in targets (e.g. "UI/Interface.tscn") is used as the key.
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
    # script_dir = mods/Trans To Vostok/tools/utils
    mod_root = script_dir.parent.parent
    default_src = (mod_root / ".tmp" / "pck_recovered").resolve()
    default_out = (mod_root / ".tmp" / "parsed_text").resolve()

    src_arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_src
    out_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_out

    # load parse_list_tscn.json (located in tools/, one level up from utils/)
    config_path = script_dir.parent / "parse_list_tscn.json"
    config = load_tscn_config(config_path)
    global_extra = config.get("extra_properties", [])
    per_file_extras = _build_per_file_extras(config)
    print(f"Config: {config_path.name}")
    print(f"  global extra_properties: {global_extra}")
    if per_file_extras:
        print(f"  per-file extra_properties: {len(per_file_extras)} files")
    print()

    if not src_arg.exists():
        print(f"[ERROR] Input path not found: {src_arg}")
        return 1

    # supports both a single file and a directory
    if src_arg.is_file():
        if src_arg.suffix.lower() != ".tscn":
            print(f"[ERROR] Not a .tscn file: {src_arg}")
            return 1
        tscn_files = [src_arg]
        src_dir = src_arg.parent
    else:
        src_dir = src_arg
        tscn_files = sorted(src_arg.rglob("*.tscn"))
        if not tscn_files:
            print(f"[ERROR] No .tscn files found: {src_arg}")
            return 1

    print(f"Input:  {src_dir}")
    print(f"Output: {out_dir}")
    print(f"Target files: {len(tscn_files)}")
    print()

    total_nodes = 0
    total_texts = 0
    processed = 0
    failed = 0

    for tscn in tscn_files:
        rel_tscn = tscn.relative_to(src_dir)
        rel_posix = rel_tscn.as_posix()
        # filename = relative path without extension (e.g. "Scenes/Menu")
        # location = matching key — same as filename for .tscn entries
        filename = rel_tscn.with_suffix("").as_posix()
        # output file: double extension including the original extension (e.g. "Scenes/Menu.tscn.tsv")
        out_path = out_dir / (rel_posix + ".tsv")
        # merge global + per-file extra_properties
        file_extra = per_file_extras.get(rel_posix, [])
        combined_extra = list(global_extra) + file_extra if (global_extra or file_extra) else None
        try:
            n, t = process_file(tscn, out_path, filename, combined_extra)
            total_nodes += n
            total_texts += t
            processed += 1
            if t > 0:
                print(f"  [OK] {rel_tscn.as_posix()}  ({t} texts / {n} nodes)")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {rel_tscn.as_posix()}: {e}")

    print()
    print(f"Done: {processed} files processed ({failed} failed)")
    print(f"  Total nodes: {total_nodes}")
    print(f"  Nodes with text: {total_texts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
