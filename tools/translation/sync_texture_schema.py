"""Sync Template's Texture TSV structure to all active locales.

For each active locale (per locale.json `enabled: true`), updates
Translations/<locale>/Texture/* to mirror Template's structure:

  - Add new sheets (e.g. Signs / Structures) that exist in Template
  - Add new rows (per Template) — Translation column left empty
  - Preserve locale's existing Translation, Reworked by, Contributors,
    Attribution for rows that already match (key = File Dir + File Name)
  - Update structural columns (Where, Sub, Type, method, Text,
    File Directory, File Name, Comments, max_length) from Template
  - Sync _sheet_order.txt to match Template

Rows present in locale but missing from Template are KEPT by default
(with a warning) — use --prune to remove them. Same for stale sheets.

Locale-specific columns whose values come from the locale (preserved):
    Translation, Reworked by, Contributors, Attribution

All other columns are sourced from Template (single source of truth).

Usage:
    python tools/translation/sync_texture_schema.py              # all active locales (locale.json)
    python tools/translation/sync_texture_schema.py Korean French  # specific locales
    python tools/translation/sync_texture_schema.py --prune     # also delete orphans
"""
import argparse
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
REPO = SCRIPT_DIR.parent.parent
TRANSLATIONS = REPO / "Translations"
LOCALE_JSON = REPO / "src" / "locale.json"

CATEGORY = "Texture"
TEMPLATE_LOCALE = "Template"

# These columns' values are owned by each locale (per-translator credits +
# per-language translation). Everything else is sourced from Template.
LOCALE_SPECIFIC_COLUMNS = {
    "Translation",
    "Reworked by",
    "Contributors",
    "Attribution",
}


def _row_key(row: dict) -> tuple[str, str]:
    """Uniquely identifies a Texture row across Template and locales."""
    fd = (row.get("File Directory") or "").strip()
    fn = (row.get("File Name") or "").strip()
    return (fd, fn)


def _load_active_locales() -> list[str]:
    """Return list of `dir` names for locales with enabled=true,
    excluding English (source language, no translation files needed)."""
    if not LOCALE_JSON.exists():
        raise SystemExit(f"locale.json not found at {LOCALE_JSON}")
    data = json.loads(LOCALE_JSON.read_text(encoding="utf-8"))
    return [
        loc["dir"]
        for loc in data.get("locales", [])
        if loc.get("enabled") and loc.get("dir") not in ("English", "")
    ]


def _read_tsv(path: Path) -> tuple[list[str], list[dict]]:
    if not path.exists():
        return [], []
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))
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
        w = csv.writer(f, delimiter="\t", lineterminator="\n",
                       quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(c, "") for c in header])


def sync_locale(locale: str, *, prune: bool = False) -> dict:
    """Sync one locale's Texture/* TSVs to Template's structure.
    Returns stats dict for reporting."""
    tpl_dir = TRANSLATIONS / TEMPLATE_LOCALE / "tsv" / CATEGORY
    loc_dir = TRANSLATIONS / locale / "tsv" / CATEGORY

    if not tpl_dir.exists():
        return {"error": f"Template/{CATEGORY} missing"}

    stats: dict = {
        "sheets_synced":  0,
        "rows_added":     0,
        "rows_preserved": 0,
        "rows_orphaned":  0,
        "rows_pruned":    0,
        "warnings":       [],
    }

    # Sheet order from Template
    order_file = tpl_dir / "_sheet_order.txt"
    if order_file.exists():
        order = [ln.strip() for ln in
                 order_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        order = sorted(p.stem for p in tpl_dir.glob("*.tsv"))

    for sheet in order:
        tpl_path = tpl_dir / f"{sheet}.tsv"
        loc_path = loc_dir / f"{sheet}.tsv"

        if not tpl_path.exists():
            stats["warnings"].append(f"Template missing {sheet}.tsv")
            continue

        tpl_header, tpl_rows = _read_tsv(tpl_path)
        _, loc_rows = _read_tsv(loc_path)

        # Lookup locale rows by (File Dir, File Name) key
        loc_by_key = {_row_key(r): r for r in loc_rows}

        new_rows: list[dict] = []
        for tpl_row in tpl_rows:
            key = _row_key(tpl_row)
            loc_row = loc_by_key.pop(key, None)

            if loc_row is None:
                # Fresh row from Template — empty translation/credits
                merged = dict(tpl_row)
                for col in LOCALE_SPECIFIC_COLUMNS:
                    merged[col] = ""
                new_rows.append(merged)
                stats["rows_added"] += 1
            else:
                # Merge: Template = structural, locale = translation/credits
                merged = dict(tpl_row)
                for col in LOCALE_SPECIFIC_COLUMNS:
                    merged[col] = loc_row.get(col, "")
                new_rows.append(merged)
                stats["rows_preserved"] += 1

        # Orphans: rows in locale but not in Template
        orphans = list(loc_by_key.values())
        if orphans:
            stats["rows_orphaned"] += len(orphans)
            if prune:
                stats["rows_pruned"] += len(orphans)
            else:
                for orphan in orphans:
                    new_rows.append(orphan)
                stats["warnings"].append(
                    f"{sheet}: {len(orphans)} orphan row(s) kept "
                    f"(use --prune to remove)"
                )

        _write_tsv(loc_path, tpl_header, new_rows)
        stats["sheets_synced"] += 1

    # _sheet_order.txt
    loc_dir.mkdir(parents=True, exist_ok=True)
    (loc_dir / "_sheet_order.txt").write_text(
        "\n".join(order) + "\n", encoding="utf-8"
    )

    # Stale sheets (in locale but not in Template's order)
    template_sheets = set(order)
    for tsv in loc_dir.glob("*.tsv"):
        if tsv.stem not in template_sheets:
            if prune:
                tsv.unlink()
                stats["warnings"].append(f"Pruned stale sheet: {tsv.name}")
            else:
                stats["warnings"].append(
                    f"Stale sheet kept: {tsv.name} (use --prune to remove)"
                )

    return stats


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locales", nargs="*",
        help="Locales to sync (default: all enabled in locale.json)",
    )
    parser.add_argument(
        "--prune", action="store_true",
        help="Remove rows/sheets present in locale but not in Template",
    )
    args = parser.parse_args(argv[1:])

    locales = args.locales if args.locales else _load_active_locales()

    print(f"Syncing {CATEGORY} schema  Template -> {len(locales)} locale(s)")
    print(f"  Locales    : {', '.join(locales)}")
    print(f"  Prune mode : {'ON' if args.prune else 'OFF (orphans kept)'}")
    print()

    grand = {"added": 0, "preserved": 0, "orphaned": 0, "pruned": 0}
    failures: list[str] = []

    for locale in locales:
        print(f"=== {locale} ===")
        stats = sync_locale(locale, prune=args.prune)
        if "error" in stats:
            print(f"  [ERROR] {stats['error']}")
            failures.append(locale)
            print()
            continue
        print(f"  Sheets synced     : {stats['sheets_synced']}")
        print(f"  Rows added (new)  : {stats['rows_added']}")
        print(f"  Rows preserved    : {stats['rows_preserved']}")
        if stats["rows_orphaned"]:
            note = " (pruned)" if args.prune else ""
            print(f"  Rows orphaned     : {stats['rows_orphaned']}{note}")
        for w in stats["warnings"]:
            print(f"  [WARN] {w}")
        grand["added"]     += stats["rows_added"]
        grand["preserved"] += stats["rows_preserved"]
        grand["orphaned"]  += stats["rows_orphaned"]
        grand["pruned"]    += stats["rows_pruned"]
        print()

    print("=== Total ===")
    print(f"  Rows added     : {grand['added']}")
    print(f"  Rows preserved : {grand['preserved']}")
    if grand["orphaned"]:
        note = " (pruned)" if args.prune else ""
        print(f"  Rows orphaned  : {grand['orphaned']}{note}")
    if failures:
        print(f"  Failed locales : {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
