"""Build <locale>/texture_meta.json from canonical Texture TSVs.

Emits a flat JSON map: rel_path -> method ("replace" | "blend"),
consumed at runtime by texture_loader.gd to decide how to apply each
mod-side texture.

  - replace : substitute the original texture wholesale (default)
  - blend   : composite mod overlay PNG on top of the original via
              Image.blend_rect at runtime (preserves PBR maps, ships
              only the translated text portion)

Rows with empty File Directory + File Name are skipped (no asset path
to key on).

Usage:
    python tools/utils/build_texture_meta.py <locale>
"""
import csv
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
TRANSLATIONS_ROOT = PROJECT_ROOT / "Translations"
PKG_ROOT = PROJECT_ROOT / "Trans To Vostok"  # dev-time runtime mod root

CATEGORY = "Texture"
OUTPUT_NAME = "texture_meta.json"

VALID_METHODS = {"replace", "blend"}


def _normalize_path(file_directory: str, file_name: str) -> str:
    """Join 'File Directory' + 'File Name' into a runtime rel path.

    File Directory uses Windows-style backslashes and may have a leading
    slash (e.g. '\\Assets\\Sign_Mines\\Files'). Runtime expects forward
    slashes and no leading slash:
        '\\Assets\\Sign_Mines\\Files' + 'TX_Sign_Mines_AL.png'
        -> 'Assets/Sign_Mines/Files/TX_Sign_Mines_AL.png'
    """
    fd = (file_directory or "").strip().replace("\\", "/").strip("/")
    fn = (file_name or "").strip()
    if not fn:
        return ""
    return f"{fd}/{fn}" if fd else fn


def build(locale: str) -> int:
    src_dir = TRANSLATIONS_ROOT / locale / "tsv" / CATEGORY
    out_path = PKG_ROOT / locale / OUTPUT_NAME

    if not src_dir.exists():
        print(f"[SKIP] {locale}: TSV dir not found ({src_dir})")
        return 0

    meta: dict[str, str] = {}
    duplicates: list[tuple[str, str, str]] = []  # (rel, existing, new)
    invalid: list[tuple[Path, int, str]] = []    # (tsv, row_num, method)

    for tsv in sorted(src_dir.glob("*.tsv")):
        with open(tsv, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row_num, row in enumerate(reader, start=2):
                method = (row.get("method") or "").strip().lower()
                if not method:
                    method = "replace"
                if method not in VALID_METHODS:
                    invalid.append((tsv, row_num, method))
                    continue

                rel = _normalize_path(
                    row.get("File Directory", ""),
                    row.get("File Name", ""),
                )
                if not rel:
                    continue

                if rel in meta and meta[rel] != method:
                    duplicates.append((rel, meta[rel], method))
                meta[rel] = method

    if invalid:
        print(f"[WARN] {len(invalid)} rows with invalid method value:")
        for tsv, row_num, method in invalid[:5]:
            print(f"  {tsv.name}:{row_num}  method={method!r}")
        if len(invalid) > 5:
            print(f"  ... and {len(invalid) - 5} more")

    if duplicates:
        print(f"[WARN] {len(duplicates)} path collisions (same file with different method):")
        for rel, old, new in duplicates[:5]:
            print(f"  {rel}: {old!r} -> {new!r}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    counts = {m: sum(1 for v in meta.values() if v == m) for m in VALID_METHODS}
    counts_str = ", ".join(f"{m}={n}" for m, n in counts.items())
    print(f"[OK] {locale}: {len(meta)} entries ({counts_str})")
    print(f"     {out_path}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(f"Usage: python {Path(__file__).name} <locale>")
        return 1
    return build(argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
