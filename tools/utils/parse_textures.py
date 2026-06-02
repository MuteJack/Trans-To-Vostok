"""
Scan recovered PCK assets and emit a texture catalogue TSV + PNG copies.

The output is the texture-side analogue of .tmp/parsed_text/ — a source-of-truth
dataset that future tooling (e.g. validate_texture.py) can compare against
Texture.xlsx, and that lets us detect upstream texture changes across game
versions by diffing the sha256 column between snapshots.

Outputs:
    <out_dir>/textures.tsv          — per-PNG row: catalogue path + fingerprint
    <out_dir>/<rel_path>/<file>.png — copy of every .png, mirroring the source tree

textures.tsv columns:
    File Directory  — Windows-style path with leading backslash, no trailing slash
                      (e.g. "\\Assets\\Sign_Mines\\Files"). Matches the canonical
                      Texture xlsx schema so rows can be joined directly.
    File Name       — base filename with extension (e.g. "TX_Sign_Mines_AL.png")
    size            — file size in bytes
    sha256          — hex SHA-256 of raw file bytes (game-version change signal)

Hash computation lives in the sibling `hash_textures` library (sha256_of).

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
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hash_textures import TEXTURE_EXTENSIONS, sha256_of

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


OUT_COLUMNS = ["File Directory", "File Name", "size", "sha256"]
PROGRESS_EVERY = 250


def to_canonical_dir(rel_dir: Path) -> str:
    """Convert a relative directory path to canonical Texture-TSV form.

    "Assets/Sign_Mines/Files"  ->  "\\Assets\\Sign_Mines\\Files"
    "."                        ->  ""
    """
    s = rel_dir.as_posix()
    if s in ("", "."):
        return ""
    return "\\" + s.replace("/", "\\")


def collect_textures(src_dir: Path) -> list[tuple[Path, str, str, int, str]]:
    """Return sorted (src_path, File Directory, File Name, size, sha256) tuples
    for every texture under src_dir.

    sha256 is computed up-front so write_tsv can stay a pure formatter.
    """
    pngs = sorted(p for p in src_dir.rglob("*") if p.is_file()
                  and p.suffix.lower() in TEXTURE_EXTENSIONS)
    total = len(pngs)
    print(f"PNGs to scan: {total}")
    start = time.time()
    entries: list[tuple[Path, str, str, int, str]] = []
    for i, path in enumerate(pngs, 1):
        rel_dir = path.parent.relative_to(src_dir)
        size = path.stat().st_size
        digest = sha256_of(path)
        entries.append((path, to_canonical_dir(rel_dir), path.name, size, digest))
        if i % PROGRESS_EVERY == 0:
            print(f"  {i}/{total}  ({time.time() - start:.1f}s)")
    elapsed = time.time() - start
    if total:
        print(f"Scanned {total} files in {elapsed:.1f}s ({total / elapsed:.0f} files/sec)")
    entries.sort(key=lambda e: (e[1], e[2]))
    return entries


def write_tsv(out_path: Path, entries: list[tuple[Path, str, str, int, str]]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(OUT_COLUMNS)
        for _, file_dir, file_name, size, digest in entries:
            writer.writerow([file_dir, file_name, size, digest])


def copy_textures(entries: list[tuple[Path, str, str, int, str]], src_dir: Path, out_dir: Path) -> int:
    """Copy each texture to out_dir, mirroring the source directory tree. Skips up-to-date files."""
    copied = 0
    for src_path, _, _, _, _ in entries:
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
    print(f"\nCataloged: {len(entries)} textures ({copied} copied, {len(entries) - copied} up-to-date)")
    print(f"Wrote: {tsv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
