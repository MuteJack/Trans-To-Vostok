"""Build Crowdin source TSV files from Translation_TSV/Template.

Reads Template TSVs (canonical structure with empty translation column)
and writes slim source TSVs to Crowdin_Mirror/source/<category>/<sheet>.tsv
with the columns Crowdin expects:

    identifier, source_phrase, context, labels, max_length

Filters out rows that should not be pushed:
    - method=ignore (Translation only)
    - untranslatable=1 (Translation/Glossary)
    - empty text

Dedups rows with identical composite_id within the same file (most
common for Translation global rows: substr / literal global / pattern
global — all with no location, so same text → same id).

Usage:
    python tools/crowdin/build_source.py
"""
import csv
import sys
from pathlib import Path

# Path setup
SCRIPT_DIR = Path(__file__).resolve().parent              # tools/crowdin
TOOLS_DIR = SCRIPT_DIR.parent                              # tools
REPO = TOOLS_DIR.parent                                    # repo root

sys.path.insert(0, str(TOOLS_DIR))
from crowdin.identifier import (
    make_translation_id,
    make_glossary_id,
    make_texture_id,
)

TSV_ROOT = REPO / "Translation_TSV"
MIRROR_ROOT = REPO / "Crowdin_Mirror"
SOURCE_LOCALE = "Template"
SKIP_SHEETS = {"MetaData"}

CATEGORIES = ["Translation", "Glossary", "Texture"]

# Columns we'll output to Crowdin source TSV
OUTPUT_COLUMNS = ["identifier", "source_phrase", "translation", "context", "labels", "max_length"]


def _load_tsv(path: Path) -> tuple[list[str], list[dict]]:
    """Load a TSV file as (header, list of row-dicts)."""
    rows = list(csv.reader(open(path, encoding="utf-8"), delimiter="\t"))
    if not rows:
        return [], []
    header = rows[0]
    data = []
    for r in rows[1:]:
        while len(r) < len(header):
            r.append("")
        data.append(dict(zip(header, r)))
    return header, data


def _write_tsv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(c, "") for c in header])


def _join_labels(*values: str) -> str:
    """Join non-empty values with ';' for Crowdin labels column."""
    return ";".join(v.strip() for v in values if v and v.strip())


def _row_to_translation_source(row: dict) -> dict | None:
    cid = make_translation_id(row)
    if not cid:
        return None
    return {
        "identifier": cid,
        "source_phrase": row.get("text", ""),
        "translation": "",
        "context": row.get("DESCRIPTION", ""),
        "labels": _join_labels(row.get("WHERE", ""), row.get("SUB", ""), row.get("KIND", "")),
        "max_length": (row.get("max_length") or "").strip(),
    }


def _row_to_glossary_source(row: dict) -> dict | None:
    cid = make_glossary_id(row)
    if not cid:
        return None
    return {
        "identifier": cid,
        "source_phrase": row.get("text", ""),
        "translation": "",
        "context": row.get("DESCRIPTION", ""),
        "labels": _join_labels(
            row.get("Category", ""),
            row.get("Sub-Category", ""),
            row.get("Class", ""),
        ),
        "max_length": (row.get("max_length") or "").strip(),
    }


def _row_to_texture_source(row: dict) -> dict | None:
    cid = make_texture_id(row)
    if not cid:
        return None
    return {
        "identifier": cid,
        "source_phrase": row.get("Text", ""),
        "translation": "",
        "context": row.get("File Directory", ""),  # texture has no DESCRIPTION; use directory hint
        "labels": _join_labels(row.get("Where", ""), row.get("Sub", ""), row.get("Type", "")),
        "max_length": (row.get("max_length") or "").strip(),
    }


CATEGORY_BUILDERS = {
    "Translation": _row_to_translation_source,
    "Glossary": _row_to_glossary_source,
    "Texture": _row_to_texture_source,
}


def build_category(category: str) -> tuple[int, int, int]:
    """Returns (files_written, total_rows, dedup_count)."""
    src_dir = TSV_ROOT / SOURCE_LOCALE / category
    out_dir = MIRROR_ROOT / "source" / category
    builder = CATEGORY_BUILDERS[category]
    if not src_dir.exists():
        print(f"  [{category}] no source dir: {src_dir}")
        return 0, 0, 0
    files_written = 0
    total_rows = 0
    dedup_count = 0
    for tsv_path in sorted(src_dir.glob("*.tsv")):
        if tsv_path.stem in SKIP_SHEETS:
            continue
        _, data = _load_tsv(tsv_path)
        out_rows: list[dict] = []
        seen_ids: set[str] = set()
        skipped = 0
        for row in data:
            built = builder(row)
            if built is None:
                skipped += 1
                continue
            cid = built["identifier"]
            if cid in seen_ids:
                dedup_count += 1
                continue
            seen_ids.add(cid)
            out_rows.append(built)
        out_path = out_dir / tsv_path.name
        _write_tsv(out_path, OUTPUT_COLUMNS, out_rows)
        print(f"  [{category}/{tsv_path.stem:25s}] in={len(data):5d} out={len(out_rows):5d} "
              f"skipped={skipped} dedup={dedup_count if False else '-'}")
        files_written += 1
        total_rows += len(out_rows)
    return files_written, total_rows, dedup_count


def main() -> int:
    print(f"Source : {TSV_ROOT / SOURCE_LOCALE}")
    print(f"Output : {MIRROR_ROOT / 'source'}")
    print()
    grand_files = 0
    grand_rows = 0
    grand_dedup = 0
    for cat in CATEGORIES:
        files, rows, dedup = build_category(cat)
        grand_files += files
        grand_rows += rows
        grand_dedup += dedup
    print()
    print(f"=== Done ===")
    print(f"  files written : {grand_files}")
    print(f"  rows written  : {grand_rows}")
    print(f"  dedup'd ids   : {grand_dedup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
