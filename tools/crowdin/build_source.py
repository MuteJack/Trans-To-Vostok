"""Build Crowdin source TSV files from Translations/Template.

Reads Template TSVs (canonical structure with empty translation column)
and writes slim source TSVs to Crowdin_Mirror/source/<category>/<sheet>.tsv
with the columns Crowdin expects:

    identifier, source_phrase, context, labels, max_length

Filters out rows that should not be pushed:
    - method=ignore (Translation only)
    - untranslatable=1 (Translation)
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
    temp_id_for_translation,
    temp_id_for_texture,
    make_translation_id,
    make_texture_id,
)

TSV_ROOT = REPO / "Translations"
MIRROR_ROOT = REPO / "Crowdin_Mirror"
SOURCE_LOCALE = "Template"
SKIP_SHEETS = {"MetaData"}

CATEGORIES = ["Translation", "Texture"]

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


def _identifier_for(row: dict, fallback_fn) -> str:
    """Prefer the TSV's `identifier` column (numeric_id assigned by Crowdin,
    or a `tmp:` bootstrap value from register_new_strings.py). Fall back to a
    fresh temp_id only for rows that completely lack an identifier — this
    path is for safety; the canonical flow is register → push → fetch.
    Returns "" for rows that should not be pushed (ignore / empty text)."""
    cid = (row.get("identifier") or "").strip()
    if cid:
        return cid
    return fallback_fn(row)


def _compose_context(location_hint: str, description: str) -> str:
    """Combine the row's DESCRIPTION with a human-readable location hint.

    Order is `<description>\\n<location_hint>` (description first) on purpose:
    Crowdin's importer applies a strip heuristic to the first line of a
    multi-line context value when that line looks like a path or composite
    identifier (treats it as a stale auto-tag and removes it). Putting the
    description first puts non-path-like content on the first line, so the
    strip never fires.

    Crowdin still auto-prepends `<identifier>\\n` on top, giving a final
    stored context of `<numeric_id>\\n<description>\\n<location_hint>`. For
    rows without a description we collapse to a single-line `<location_hint>`
    (also exempt from the multi-line strip).
    """
    parts = [p for p in (description, location_hint) if p]
    return "\n".join(parts)


def _translation_location_hint(row: dict) -> str:
    """Legacy `T:filename:parent:name:type:property:unique_id:sha1` composite.

    Used as a per-row position marker in the context column. Crowdin's web
    editor preserves this format when the value is saved manually, so we
    send it via file import as a second-line context value (after the
    DESCRIPTION) and hope the strip heuristic only targets the first line.
    """
    return make_translation_id(row)


def _texture_location_hint(row: dict) -> str:
    """Legacy `X:<File_Name>:<sha1(Text)>` composite — same rationale as
    `_translation_location_hint`."""
    return make_texture_id(row)


def _row_to_translation_source(row: dict) -> dict | None:
    cid = _identifier_for(row, temp_id_for_translation)
    if not cid:
        return None
    return {
        "identifier": cid,
        "source_phrase": row.get("text", ""),
        "translation": "",
        "context": _compose_context(_translation_location_hint(row),
                                    row.get("DESCRIPTION", "")),
        "labels": _join_labels(row.get("WHERE", ""), row.get("SUB", ""), row.get("KIND", "")),
        "max_length": (row.get("max_length") or "").strip(),
    }


def _row_to_texture_source(row: dict) -> dict | None:
    cid = _identifier_for(row, temp_id_for_texture)
    if not cid:
        return None
    return {
        "identifier": cid,
        "source_phrase": row.get("Text", ""),
        "translation": "",
        "context": _compose_context(_texture_location_hint(row),
                                    row.get("File Directory", "")),
        "labels": _join_labels(row.get("Where", ""), row.get("Sub", ""), row.get("Type", "")),
        "max_length": (row.get("max_length") or "").strip(),
    }


CATEGORY_BUILDERS = {
    "Translation": _row_to_translation_source,
    "Texture": _row_to_texture_source,
}


def build_category(category: str) -> tuple[int, int, int]:
    """Returns (files_written, total_rows, dedup_count)."""
    src_dir = TSV_ROOT / SOURCE_LOCALE / "tsv" / category
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
