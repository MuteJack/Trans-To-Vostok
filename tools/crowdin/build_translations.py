"""Build Crowdin translation upload files from existing locale TSVs.

Reads Translations/<locale>/{Translation,Glossary,Texture}/*.tsv and
writes per-locale translation TSVs to:

    Crowdin_Mirror/translations/<locale>/<category>/<sheet>.tsv

Output format mirrors the source file scheme (multicolumn CSV):

    identifier, source_phrase, translation, context, labels, max_length

`source_phrase` is the English source, `translation` is the locale's
translation. Crowdin matches rows by `identifier` on upload.

Filters mirror build_source.py so identifiers stay aligned:
    - method=ignore (Translation only)
    - untranslatable=1
    - empty source text (no id) or empty translation (nothing to seed)
    - dedup by identifier within file (first non-empty translation wins)

Usage:
    python tools/crowdin/build_translations.py             # all locales
    python tools/crowdin/build_translations.py Korean      # one locale only
"""
import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
REPO = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
from crowdin.identifier import (
    make_translation_id,
    make_glossary_id,
    make_texture_id,
)

TSV_ROOT = REPO / "Translations"
MIRROR_ROOT = REPO / "Crowdin_Mirror"
TEMPLATE_LOCALE = "Template"
SKIP_SHEETS = {"MetaData"}

CATEGORIES = ["Translation", "Glossary", "Texture"]
OUTPUT_COLUMNS = ["identifier", "source_phrase", "translation", "context", "labels", "max_length"]

SOURCE_FIELD = {
    "Translation": "text",
    "Glossary": "text",
    "Texture": "Text",
}
TRANSLATION_FIELD = {
    "Translation": "translation",
    "Glossary": "translation",
    "Texture": "Translation",
}

ID_FUNC = {
    "Translation": make_translation_id,
    "Glossary": make_glossary_id,
    "Texture": make_texture_id,
}


def _load_tsv(path: Path) -> list[dict]:
    rows = list(csv.reader(open(path, encoding="utf-8"), delimiter="\t"))
    if not rows:
        return []
    header = rows[0]
    data = []
    for r in rows[1:]:
        while len(r) < len(header):
            r.append("")
        data.append(dict(zip(header, r)))
    return data


def _write_tsv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(c, "") for c in header])


def discover_locales() -> list[str]:
    return sorted(
        d.name for d in TSV_ROOT.iterdir()
        if d.is_dir() and d.name != TEMPLATE_LOCALE
    )


def build_locale_category(locale: str, category: str) -> tuple[int, int]:
    """Returns (files_written, rows_written)."""
    src_dir = TSV_ROOT / locale / category
    out_dir = MIRROR_ROOT / "translations" / locale / category
    if not src_dir.exists():
        return 0, 0
    id_func = ID_FUNC[category]
    src_field = SOURCE_FIELD[category]
    tx_field = TRANSLATION_FIELD[category]
    files_written = 0
    rows_written = 0
    for tsv_path in sorted(src_dir.glob("*.tsv")):
        if tsv_path.stem in SKIP_SHEETS:
            continue
        data = _load_tsv(tsv_path)
        out_rows: list[dict] = []
        seen_ids: set[str] = set()
        empty_tx = 0
        no_id = 0
        for row in data:
            tx = (row.get(tx_field) or "").strip()
            if not tx:
                empty_tx += 1
                continue
            cid = id_func(row)
            if not cid:
                no_id += 1
                continue
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            out_rows.append({
                "identifier": cid,
                "source_phrase": (row.get(src_field) or "").strip(),
                "translation": tx,
                "context": "",
                "labels": "",
                "max_length": "",
            })
        out_path = out_dir / tsv_path.name
        _write_tsv(out_path, OUTPUT_COLUMNS, out_rows)
        print(f"  [{locale}/{category}/{tsv_path.stem:25s}] "
              f"in={len(data):5d} out={len(out_rows):5d} "
              f"empty_tx={empty_tx} no_id={no_id}")
        files_written += 1
        rows_written += len(out_rows)
    return files_written, rows_written


def main(argv: list[str]) -> int:
    if len(argv) >= 2:
        locales = [argv[1]]
    else:
        locales = discover_locales()

    print(f"Source : {TSV_ROOT}")
    print(f"Output : {MIRROR_ROOT / 'translations'}")
    print(f"Locales: {', '.join(locales)}")
    print()

    grand_files = 0
    grand_rows = 0
    for locale in locales:
        print(f"=== {locale} ===")
        for cat in CATEGORIES:
            f, r = build_locale_category(locale, cat)
            grand_files += f
            grand_rows += r
        print()

    print("=== Done ===")
    print(f"  files written : {grand_files}")
    print(f"  rows written  : {grand_rows}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
