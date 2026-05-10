"""Apply Crowdin pull results to canonical TSVs.

Reads Crowdin_Mirror/translations/<locale>/<cat>/*.tsv (downloaded by
`crowdin download`) and updates the `translation` column of the matching
rows in Translations/<locale>/<cat>/*.tsv (canonical, committed).

Matching is by the composite identifier — recomputed from each canonical
row's structural columns and looked up against the Crowdin TSV's
`identifier` column. Rows excluded from Crowdin (untranslatable=1,
method=ignore, empty text) are skipped.

Empty translation on Crowdin (untranslated rows) is IGNORED — local canonical
translation is preserved. This avoids wiping our committed translations when
Crowdin's downloaded file includes the row with an empty translation cell
(common when a string has no translation yet on Crowdin's side).

If a translator wants to delete a translation on Crowdin and have it removed
from repo, they should do so via the Crowdin web UI then commit the manual
empty value in xlsx; the pipeline won't blank it automatically.

Usage:
    python tools/crowdin/apply_to_repo.py             # all locales
    python tools/crowdin/apply_to_repo.py Korean      # one locale
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

TRANSLATIONS_ROOT = REPO / "Translations"
MIRROR_ROOT = REPO / "Crowdin_Mirror"
TEMPLATE_LOCALE = "Template"
SKIP_SHEETS = {"MetaData"}

CATEGORIES = ["Translation", "Glossary", "Texture"]

# Per-category column name for the translation cell in the canonical TSV.
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


def _load_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    rows = list(csv.reader(open(path, encoding="utf-8"), delimiter="\t"))
    if not rows:
        return [], []
    header = rows[0]
    norm = []
    for r in rows[1:]:
        while len(r) < len(header):
            r.append("")
        norm.append(r)
    return header, norm


def _write_tsv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    tmp.replace(path)


def discover_locales() -> list[str]:
    src = MIRROR_ROOT / "translations"
    if not src.exists():
        return []
    return sorted(
        d.name for d in src.iterdir()
        if d.is_dir() and d.name != TEMPLATE_LOCALE
    )


def apply_locale_category(locale: str, category: str) -> dict:
    src_dir = MIRROR_ROOT / "translations" / locale / category
    dst_dir = TRANSLATIONS_ROOT / locale / category
    stats = {"sheets": 0, "updated": 0, "unchanged": 0, "missing_canon": 0}
    if not src_dir.exists():
        return stats
    if not dst_dir.exists():
        print(f"  [WARN] {locale}/{category}: canonical dir missing")
        return stats

    id_func = ID_FUNC[category]
    tx_field = TRANSLATION_FIELD[category]

    for src_tsv in sorted(src_dir.glob("*.tsv")):
        if src_tsv.stem in SKIP_SHEETS:
            continue
        src_header, src_rows = _load_tsv(src_tsv)
        if "identifier" not in src_header or "translation" not in src_header:
            print(f"  [WARN] {src_tsv.name}: missing required columns ({src_header})")
            continue
        id_idx = src_header.index("identifier")
        tx_idx = src_header.index("translation")
        crowdin_map: dict[str, str] = {}
        for r in src_rows:
            cid = r[id_idx].strip()
            if cid:
                crowdin_map[cid] = r[tx_idx]

        dst_tsv = dst_dir / src_tsv.name
        if not dst_tsv.exists():
            print(f"  [WARN] canonical TSV missing: {dst_tsv.relative_to(REPO)}")
            continue
        dst_header, dst_rows = _load_tsv(dst_tsv)
        if tx_field not in dst_header:
            print(f"  [WARN] {dst_tsv.name}: no '{tx_field}' column")
            continue
        dst_tx_idx = dst_header.index(tx_field)

        sheet_updated = 0
        sheet_unchanged = 0
        sheet_skipped_empty = 0
        seen_cids: set[str] = set()
        for r in dst_rows:
            row_dict = dict(zip(dst_header, r))
            cid = id_func(row_dict)
            if not cid:
                continue
            seen_cids.add(cid)
            if cid not in crowdin_map:
                continue
            new_tx = crowdin_map[cid]
            if not new_tx.strip():
                # Crowdin row exists but has no translation -- preserve local.
                sheet_skipped_empty += 1
                continue
            if r[dst_tx_idx] == new_tx:
                sheet_unchanged += 1
            else:
                r[dst_tx_idx] = new_tx
                sheet_updated += 1

        unmatched = set(crowdin_map.keys()) - seen_cids
        stats["missing_canon"] += len(unmatched)

        if sheet_updated:
            _write_tsv(dst_tsv, dst_header, dst_rows)

        stats["sheets"] += 1
        stats["updated"] += sheet_updated
        stats["unchanged"] += sheet_unchanged
        stats.setdefault("skipped_empty", 0)
        stats["skipped_empty"] += sheet_skipped_empty
        print(f"  [{locale}/{category}/{src_tsv.stem:25s}] "
              f"updated={sheet_updated:4d} unchanged={sheet_unchanged:4d} "
              f"skipped_empty={sheet_skipped_empty:4d}")

    return stats


def main(argv: list[str]) -> int:
    if len(argv) >= 2:
        locales = [argv[1]]
    else:
        locales = discover_locales()

    if not locales:
        print(f"[ERROR] No Crowdin pull data found under {MIRROR_ROOT / 'translations'}")
        print(f"        Run `crowdin download` first.")
        return 1

    print(f"Source : {MIRROR_ROOT / 'translations'}")
    print(f"Target : {TRANSLATIONS_ROOT}")
    print(f"Locales: {', '.join(locales)}")
    print()

    grand = {"sheets": 0, "updated": 0, "unchanged": 0,
             "skipped_empty": 0, "missing_canon": 0}
    for locale in locales:
        print(f"=== {locale} ===")
        for cat in CATEGORIES:
            s = apply_locale_category(locale, cat)
            for k in grand:
                grand[k] += s.get(k, 0)
        print()

    print("=== Done ===")
    print(f"  sheets processed     : {grand['sheets']}")
    print(f"  rows updated         : {grand['updated']}")
    print(f"  rows unchanged       : {grand['unchanged']}")
    print(f"  rows preserved (empty on Crowdin): {grand['skipped_empty']}")
    if grand["missing_canon"]:
        print(f"  [WARN] {grand['missing_canon']} Crowdin entries had no matching canonical row "
              f"(possibly stale source on Crowdin — re-push sources)")
    print()
    if grand["updated"]:
        print("Next: regenerate xlsx for affected locales:")
        for loc in locales:
            print(f"  python tools/rebuild_xlsx.py {loc}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
