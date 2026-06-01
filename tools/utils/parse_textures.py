"""
Scan recovered PCK assets and emit a texture catalogue TSV + PNG copies.

The output is the texture-side analogue of .tmp/parsed_text/ — a source-of-truth
dataset that future tooling (e.g. validate_texture.py) can compare against
Texture.xlsx.

Outputs:
    <out_dir>/textures.tsv          — catalogue with File Directory + File Name
    <out_dir>/<rel_path>/<file>.png — copy of every .png, mirroring the source tree

Catalogue columns (canonical Texture TSV schema subset):
    File Directory  — Windows-style path with leading backslash, no trailing slash
                      (e.g. "\\Assets\\Sign_Mines\\Files")
    File Name       — base filename with extension (e.g. "TX_Sign_Mines_AL.png")

Usage:
    python parse_textures.py                  # use default input/output paths
    python parse_textures.py <src>            # specify input directory
    python parse_textures.py <src> <out_dir>  # specify input + output directory

Defaults:
    src     = <mod_root>/.tmp/pck_recovered/
    out_dir = <mod_root>/.tmp/parsed_textures/
"""
import csv
import shutil
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


TEXTURE_EXTENSIONS = {".png"}
OUT_COLUMNS = ["File Directory", "File Name"]


def to_canonical_dir(rel_dir: Path) -> str:
    """Convert a relative directory path to canonical Texture-TSV form.

    "Assets/Sign_Mines/Files"  ->  "\\Assets\\Sign_Mines\\Files"
    "."                        ->  ""
    """
    s = rel_dir.as_posix()
    if s in ("", "."):
        return ""
    return "\\" + s.replace("/", "\\")


def collect_textures(src_dir: Path) -> list[tuple[Path, str, str]]:
    """Return sorted (src_path, File Directory, File Name) tuples for every texture under src_dir."""
    entries: list[tuple[Path, str, str]] = []
    for path in src_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXTURE_EXTENSIONS:
            continue
        rel_dir = path.parent.relative_to(src_dir)
        entries.append((path, to_canonical_dir(rel_dir), path.name))
    entries.sort(key=lambda e: (e[1], e[2]))
    return entries


def write_tsv(out_path: Path, entries: list[tuple[Path, str, str]]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(OUT_COLUMNS)
        for _, file_dir, file_name in entries:
            writer.writerow([file_dir, file_name])


def copy_textures(entries: list[tuple[Path, str, str]], src_dir: Path, out_dir: Path) -> int:
    """Copy each texture to out_dir, mirroring the source directory tree. Skips up-to-date files."""
    copied = 0
    for src_path, _, _ in entries:
        rel = src_path.relative_to(src_dir)
        dst_path = out_dir / rel
        if dst_path.exists() and dst_path.stat().st_mtime >= src_path.stat().st_mtime \
                and dst_path.stat().st_size == src_path.stat().st_size:
            continue
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        copied += 1
    return copied


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent.parent
    default_src = (mod_root / ".tmp" / "pck_recovered").resolve()
    default_out = (mod_root / ".tmp" / "parsed_textures").resolve()

    src = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_src
    out_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else default_out

    if not src.exists():
        print(f"[ERROR] Input path not found: {src}")
        return 1
    if not src.is_dir():
        print(f"[ERROR] Input is not a directory: {src}")
        return 1

    tsv_path = out_dir / "textures.tsv"
    print(f"Input:  {src}")
    print(f"Output: {out_dir}")
    print(f"Extensions: {sorted(TEXTURE_EXTENSIONS)}")
    print()

    entries = collect_textures(src)
    write_tsv(tsv_path, entries)
    copied = copy_textures(entries, src, out_dir)

    print(f"Done: {len(entries)} textures cataloged ({copied} copied, {len(entries) - copied} up-to-date)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
