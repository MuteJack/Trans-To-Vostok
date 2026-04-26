"""
Parse Godot .tres files and extract specified field values.

Finds `field = "value"` patterns inside [resource] blocks and outputs the values to TSV.
Correctly handles multi-line strings (including newlines) and escaped quotes (\").

For each source .tres file, one .tres.tsv file is generated. The output path mirrors
the source's pck_recovered-relative path under parsed_text.

    pck_recovered/Events/List/D1_Generalist.tres
        ↓
    parsed_text/Events/List/D1_Generalist.tres.tsv

Output columns: filetype, location, field, text

Run modes:
  1) batch (recommended): python parse_tres_text.py  or --config <path>
     Reads tres_list.json and processes multiple groups at once.
     Default path: tres_list.json next to this script.
  2) single job:           python parse_tres_text.py --input <dir> --fields <list>

Usage:
    python parse_tres_text.py                       # use default tres_list.json
    python parse_tres_text.py --config other.json   # use a different config
    python parse_tres_text.py --input Events/List --fields name,description

tres_list.json schema:
    {
      "groups": [
        {
          "name": "Events",                     # optional (for progress display)
          "dir": "Events",                      # path relative to pck_recovered
          "fields": ["name", "description"],    # fields to extract
          "targets": ["List"]                   # paths relative to dir (file/directory)
        }
      ]
    }
"""
import argparse
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


# Fixed output TSV columns (unified with the tscn extraction tool)
# .tres entries have no node hierarchy, so location/parent/type/unique_id are left blank.
# The prop column holds the tres field name (e.g. "name", "description").
OUT_COLUMNS = ["filename", "filetype", "location", "parent", "name", "type", "property", "unique_id", "text"]

# default path
DEFAULT_CONFIG_NAME = "tres_list.json"


# ==========================================
# .tres parser
# ==========================================

_SUB_RESOURCE_RE = re.compile(r"^\[sub_resource\b", re.MULTILINE)


def _find_resource_block(text: str) -> tuple[int, int]:
    """
    Return the start/end offsets of the [resource] block body.
    The block body spans from the line after [resource] to the end of file.
    """
    m = re.search(r"^\[resource\]\s*$", text, re.MULTILINE)
    if not m:
        return (-1, -1)
    return (m.end(), len(text))


def _count_sub_resources(text: str) -> int:
    """Count [sub_resource ...] blocks. For warning logs."""
    return len(_SUB_RESOURCE_RE.findall(text))


def _extract_string_field(body: str, field_name: str) -> str | None:
    """
    Find `field_name = "value"` inside the [resource] block and return the value.
    Handles escaped quotes (\") and multi-line strings.
    Returns None if not found.
    """
    pattern = re.compile(
        rf'^{re.escape(field_name)}\s*=\s*"', re.MULTILINE
    )
    m = pattern.search(body)
    if not m:
        return None

    i = m.end()  # position after opening quote
    chars = []
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            # handle escape sequences
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
            # closing quote found
            return "".join(chars)
        chars.append(c)
        i += 1
    return None  # closing quote not found


def parse_tres(path: Path, fields: list[str]) -> dict | None:
    """
    Return the specified field values from one .tres file as a dict.
    Returns None if the file is not a resource or if no fields are extracted.

    Note: Currently only the [resource] block is parsed. Strings inside
    [sub_resource] blocks are not extracted; only a warning is logged when found.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"[WARN] Failed to read: {path} ({e})", file=sys.stderr)
        return None

    sub_count = _count_sub_resources(text)
    if sub_count > 0:
        print(
            f"[WARN] {path.name}: found {sub_count} [sub_resource] blocks - current parser only handles [resource] blocks, so these are skipped.",
            file=sys.stderr,
        )

    body_start, body_end = _find_resource_block(text)
    if body_start < 0:
        return None
    body = text[body_start:body_end]

    result: dict = {}
    found_any = False
    for field in fields:
        val = _extract_string_field(body, field)
        if val is not None and val != "":
            result[field] = val
            found_any = True
    return result if found_any else None


# ==========================================
# extraction logic
# ==========================================

def _collect_tres_files(target_path: Path) -> list[Path]:
    """If target is a file, return [file]; if a directory, return recursive *.tres list."""
    if target_path.is_file():
        if target_path.suffix == ".tres":
            return [target_path]
        return []
    if target_path.is_dir():
        return sorted(target_path.rglob("*.tres"))
    return []


def collect_target_files(
    pck_root: Path,
    dir_rel: str,
    targets: list[str],
) -> list[Path]:
    """
    Resolve a group's targets and return the list of .tres file paths to process.
    """
    base = (pck_root / dir_rel).resolve() if dir_rel else pck_root
    out: list[Path] = []
    for target in targets:
        target_path = (base / target).resolve() if target else base
        if not target_path.exists():
            print(
                f"[WARN] target path not found: {target_path} "
                f"(dir={dir_rel!r}, target={target!r})",
                file=sys.stderr,
            )
            continue
        tres_files = _collect_tres_files(target_path)
        if not tres_files:
            print(
                f"[WARN] no .tres files: {target_path}",
                file=sys.stderr,
            )
            continue
        out.extend(tres_files)
    return out


def tres_to_rows(
    tres_path: Path,
    fields: list[str],
    pck_root: Path,
) -> list[dict]:
    """
    Extract rows from one .tres file. Returns an empty list if none of the specified fields are found.

    Each row uses the same 8-column structure as the tscn extraction tool.
    Since .tres has no Godot node hierarchy:
      - filename  = relative path without extension
      - filetype  = "tres"
      - location  = "" (blank; defaults to global text matching)
      - parent    = ""
      - name      = ""
      - type      = ""
      - unique_id = ""
      - property  = tres field name (e.g. "description")
      - text      = field value
    """
    parsed = parse_tres(tres_path, fields)
    if parsed is None:
        return []

    try:
        rel = tres_path.resolve().relative_to(pck_root)
        filename = rel.with_suffix("").as_posix()
    except ValueError:
        filename = str(tres_path.resolve())

    rows: list[dict] = []
    for field in fields:
        if field not in parsed:
            continue
        rows.append({
            "filename": filename,
            "filetype": "tres",
            "location": "",
            "parent": "",
            "name": "",
            "type": "",
            "unique_id": "",
            "property": field,
            "text": parsed[field],
        })
    return rows


def write_tsv(out_path: Path, rows: list[dict]) -> None:
    """Atomically write a list of rows as TSV."""
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


# ==========================================
# batch mode (tres_list.json)
# ==========================================

def run_batch(
    config_path: Path,
    pck_root: Path,
    output_dir: Path,
) -> int:
    """Run each group from tres_list.json. Returns: error code."""
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse failed: {config_path} ({e})", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"[ERROR] Failed to read config: {config_path} ({e})", file=sys.stderr)
        return 1

    groups = config.get("groups")
    if not isinstance(groups, list) or not groups:
        print(f"[ERROR] config missing 'groups' array: {config_path}", file=sys.stderr)
        return 1

    # basic integrity check (name is optional)
    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            print(f"[ERROR] groups[{i}] is not an object", file=sys.stderr)
            return 1
        for required in ("dir", "fields", "targets"):
            if required not in g:
                print(f"[ERROR] groups[{i}] missing '{required}'", file=sys.stderr)
                return 1
        if not isinstance(g["fields"], list) or not g["fields"]:
            print(f"[ERROR] groups[{i}].fields is empty or not an array", file=sys.stderr)
            return 1
        if not isinstance(g["targets"], list) or not g["targets"]:
            print(f"[ERROR] groups[{i}].targets is empty or not an array", file=sys.stderr)
            return 1

    print(f"config: {config_path}")
    print(f"pck_root: {pck_root}")
    print(f"Output: {output_dir}")
    print(f"Group count: {len(groups)}")
    print()

    total_files_written = 0
    total_rows = 0
    for idx, g in enumerate(groups, start=1):
        name = g.get("name", f"group {idx}")
        dir_rel = g["dir"]
        fields = g["fields"]
        targets = g["targets"]

        print(f"[{idx}/{len(groups)}] {name}")
        print(f"    dir:     {dir_rel}")
        print(f"    targets: {targets}")
        print(f"    fields:  {fields}")

        tres_files = collect_target_files(pck_root, dir_rel, targets)
        group_rows = 0
        group_files = 0
        joined_rows: list[dict] = []
        for tres in tres_files:
            rows = tres_to_rows(tres, fields, pck_root)
            if not rows:
                continue
            try:
                rel = tres.resolve().relative_to(pck_root)
            except ValueError:
                print(f"[WARN] Skipping file outside pck_root: {tres}", file=sys.stderr)
                continue
            out_path = output_dir / (rel.as_posix() + ".tsv")
            write_tsv(out_path, rows)
            joined_rows.extend(rows)
            group_rows += len(rows)
            group_files += 1

        # if a join field is specified, also output the whole group as a combined TSV
        join_name = g.get("join")
        if join_name and joined_rows:
            join_path = output_dir / dir_rel / f"{join_name}.tres.joined.tsv"
            write_tsv(join_path, joined_rows)
            print(f"    -> {group_files} files, {group_rows} entries")
            print(f"    -> joined: {join_path.relative_to(output_dir)}")
        else:
            print(f"    -> {group_files} files, {group_rows} entries")
        print()
        total_files_written += group_files
        total_rows += group_rows

    print("=" * 60)
    print(f"Done: {len(groups)} groups, {total_files_written} TSV files, {total_rows} entries")
    return 0


# ==========================================
# single job mode (--input / --fields)
# ==========================================

def run_single_job(
    input_dir: Path,
    fields: list[str],
    pck_root: Path,
    output_dir: Path,
) -> int:
    """
    Extract fields from a single directory.
    Generates a .tres.tsv at the mirrored path for each .tres file.
    """
    if not input_dir.exists():
        print(f"[ERROR] Input path not found: {input_dir}", file=sys.stderr)
        return 1
    if not input_dir.is_dir():
        print(f"[ERROR] Not a directory: {input_dir}", file=sys.stderr)
        return 1
    if not fields:
        print("[ERROR] --fields is empty.", file=sys.stderr)
        return 1

    tres_files = sorted(input_dir.rglob("*.tres"))
    if not tres_files:
        print(f"[ERROR] No .tres files: {input_dir}", file=sys.stderr)
        return 1

    files_written = 0
    total_rows = 0
    for tres in tres_files:
        rows = tres_to_rows(tres, fields, pck_root)
        if not rows:
            continue
        try:
            rel = tres.resolve().relative_to(pck_root)
        except ValueError:
            print(f"[WARN] Skipping file outside pck_root: {tres}", file=sys.stderr)
            continue
        out_path = output_dir / (rel.as_posix() + ".tsv")
        write_tsv(out_path, rows)
        files_written += 1
        total_rows += len(rows)

    print(f"\nDone: {files_written} TSV files, {total_rows} entries")
    print(f"Output: {output_dir}")
    return 0


# ==========================================
# entry point
# ==========================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract field values from .tres files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--config", help=f"Path to tres_list.json (default: tools/{DEFAULT_CONFIG_NAME})")
    parser.add_argument("--input", help="Single job mode: target directory (recursive)")
    parser.add_argument("--fields", help="Single job mode: fields to extract (comma-separated)")
    args = parser.parse_args()

    # path basis
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent              # mods/Trans To Vostok
    pck_root = (mod_root / ".tmp" / "pck_recovered").resolve()
    parsed_dir = (mod_root / ".tmp" / "parsed_text").resolve()

    # cannot specify both --input and --config
    if args.input and args.config:
        print("[ERROR] --input and --config cannot be used together.", file=sys.stderr)
        return 1

    # single job mode
    if args.input:
        if not args.fields:
            print("[ERROR] --fields must also be specified when using --input.", file=sys.stderr)
            return 1
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        input_dir = Path(args.input).resolve()
        return run_single_job(input_dir, fields, pck_root, parsed_dir)

    # batch mode
    if args.config:
        config_path = Path(args.config).resolve()
    else:
        config_path = (script_dir / DEFAULT_CONFIG_NAME).resolve()

    if not config_path.exists():
        print(f"[ERROR] Config file not found: {config_path}", file=sys.stderr)
        print("  Specify a path with --config, or run a single job with --input / --fields.",
              file=sys.stderr)
        return 1

    if not pck_root.exists():
        print(f"[ERROR] pck_root not found: {pck_root}", file=sys.stderr)
        print("  Run decompile_gdc.bat first to generate pck_recovered.", file=sys.stderr)
        return 1

    return run_batch(config_path, pck_root, parsed_dir)


if __name__ == "__main__":
    sys.exit(main())
