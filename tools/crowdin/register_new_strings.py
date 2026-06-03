"""Populate the `identifier` column of canonical TSVs for rows that lack one.

When a fresh row is added (e.g. a new Texture in Texture.xlsx or a new
Translation row in Translation.xlsx), the identifier column ends up empty
after rebuild_xlsx → build_translation_tsv. This tool walks the canonical
TSVs and fills each empty identifier with a temporary `tmp:` value so the
next push_source can send a deterministic identifier to Crowdin.

After push, fetch_crowdin_ids.py replaces the `tmp:` values with each
string's permanent numeric_id (as assigned by Crowdin).

Default scope:
  Translations/Template/tsv/{Texture,Translation}/*.tsv

Pass `--all-locales` to also fill identifiers for orphan rows in every
locale (rows that exist in a locale TSV but not in Template — e.g.
locale-specific additions that haven't been migrated upstream).

Idempotent: re-running after success is a no-op.

Usage:
    python tools/crowdin/register_new_strings.py
    python tools/crowdin/register_new_strings.py --all-locales
    python tools/crowdin/register_new_strings.py --dry-run
"""
import argparse
import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
REPO = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
from crowdin.identifier import temp_id_for_translation, temp_id_for_texture

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


TRANSLATIONS = REPO / "Translations"
TEMPLATE_LOCALE = "Template"

CATEGORY_CONFIG = {
    "Texture":     temp_id_for_texture,
    "Translation": temp_id_for_translation,
}


def _read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if not rows:
        return [], []
    header = rows[0]
    body = []
    for r in rows[1:]:
        while len(r) < len(header):
            r.append("")
        body.append(r)
    return header, body


def _write_tsv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n",
                       quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    tmp.replace(path)


def patch_tsv(path: Path, temp_id_fn, *, dry_run: bool) -> int:
    """Fill empty `identifier` cells in this TSV. Returns the number filled."""
    header, rows = _read_tsv(path)
    if not rows or "identifier" not in header:
        return 0
    id_idx = header.index("identifier")
    filled = 0
    for r in rows:
        if (r[id_idx] or "").strip():
            continue
        row_dict = dict(zip(header, r))
        new_id = temp_id_fn(row_dict)
        if not new_id:
            continue  # row is excluded from Crowdin (ignore/untranslatable/empty text)
        r[id_idx] = new_id
        filled += 1
    if filled and not dry_run:
        _write_tsv(path, header, rows)
    return filled


def discover_locales() -> list[str]:
    return sorted(
        d.name for d in TRANSLATIONS.iterdir()
        if d.is_dir() and d.name != TEMPLATE_LOCALE
    )


def process_locale(locale: str, *, dry_run: bool) -> dict[str, int]:
    out: dict[str, int] = {}
    for category, temp_id_fn in CATEGORY_CONFIG.items():
        cat_dir = TRANSLATIONS / locale / "tsv" / category
        if not cat_dir.exists():
            continue
        total = 0
        for tsv in sorted(cat_dir.glob("*.tsv")):
            if tsv.name.startswith("_"):
                continue
            total += patch_tsv(tsv, temp_id_fn, dry_run=dry_run)
        out[category] = total
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--all-locales", action="store_true",
                        help="Also process every locale (not just Template)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change; write nothing")
    args = parser.parse_args(argv[1:])

    print(f"Mode: {'DRY-RUN' if args.dry_run else 'EXECUTE'}")
    print(f"Scope: {'Template + all locales' if args.all_locales else 'Template only'}")
    print()

    grand = 0
    locales = [TEMPLATE_LOCALE]
    if args.all_locales:
        locales += discover_locales()

    for locale in locales:
        stats = process_locale(locale, dry_run=args.dry_run)
        if not any(stats.values()):
            continue
        print(f"=== {locale} ===")
        for cat, n in stats.items():
            if n:
                print(f"  {cat:12s} filled: {n}")
                grand += n
        print()

    print(f"=== Total identifiers filled: {grand} ===")
    if args.dry_run and grand:
        print("(dry-run — no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
