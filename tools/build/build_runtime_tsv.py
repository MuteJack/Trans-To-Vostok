"""Produce a locale's runtime TSV bundle for the mod build.

This is the locale-side build step that takes the canonical translation
data and emits the runtime TSV bundle the in-game translator consumes:

    metadata.tsv
    translation_static.tsv
    translation_literal_scoped.tsv
    translation_pattern_scoped.tsv
    translation_literal.tsv
    translation_pattern.tsv
    translation_substr.tsv

Output modes:
  default    Trans To Vostok/<locale>/runtime_tsv/   (deploy path)
  --dry-run  .tmp/temp_build/Trans To Vostok/<locale>/runtime_tsv/
             Non-destructive build for downstream validation
             (e.g. check_runtime_tsv_conflict.py reads from there).

Template handling:
  `Template` is the schema source — its `translation` column is empty by
  design (locales sync from it). To still let runtime-conflict checks
  run on the Template tree, this script special-cases locale=Template:
    - --dry-run is auto-enabled (a Warn is printed if it wasn't passed).
    - For every row whose `translation` cell is empty, `text` is copied
      into `translation` in-memory before classification. Empty-text rows
      stay excluded as usual.
  Template runtime output therefore lands in .tmp/temp_build/Trans To Vostok/Template/
  and is never deployed.

Validation flags forwarded to validate_xlsx:
  --soft     TSV-match failure -> WARNING (continue) instead of ERROR
  --ignore   Skip the validate_xlsx pre-check entirely

The new tools/build/build_runtime_tsv.py replaces the legacy entry point
at tools/utils/build_runtime_tsv.py; both currently share helper
functions (classify_rows, write_tsv, ...) imported from the legacy
module until the cleanup commit moves them here.

Usage:
  python tools/build/build_runtime_tsv.py Korean
  python tools/build/build_runtime_tsv.py Korean --dry-run
  python tools/build/build_runtime_tsv.py Korean --soft
  python tools/build/build_runtime_tsv.py Korean --ignore
"""
import argparse
import csv
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
REPO = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(TOOLS_DIR / "utils"))

# Shared helpers (live in the legacy module for now)
from build_runtime_tsv import (
    classify_rows,
    write_tsv,
    COLUMNS_SCOPED,
    COLUMNS_GLOBAL,
)
from validate_translation import (
    validate_xlsx,
    load_all_translation_sheets,
    load_metadata,
    _effective_method,
)


TRANSLATIONS = REPO / "Translations"
PKG_ROOT = REPO / "Trans To Vostok"
DRY_RUN_ROOT = REPO / ".tmp" / "temp_build" / "Trans To Vostok"
PARSED_TEXT = REPO / ".tmp" / "parsed_text"
TEMPLATE_LOCALE = "Template"


def _resolve_output_dir(locale: str, dry_run: bool) -> Path:
    """Return <root>/<locale>/runtime_tsv where the bundle lands."""
    root = DRY_RUN_ROOT if dry_run else PKG_ROOT
    return root / locale / "runtime_tsv"


def _dedupe_literal_global(buckets: dict, stats: dict) -> None:
    """Collapse duplicate `text` entries in literal_global.

    classify_rows in the legacy util appends both real `literal` (global)
    rows and the fast-hit copies queued from `substr` rows into the same
    bucket; when both share a text the runtime literal lookup would land
    on duplicate keys. Priority: real `literal` > `substr` fast-hit copy.
    Translation mismatches inside the bucket emit a [WARN].

    Updates buckets["literal_global"] in place and writes a
    `literal_global_dedup_dropped` counter into `stats`. The
    `literal_global` count in stats is also re-synced to the final
    bucket size (which now reflects what's actually written to disk).
    """
    by_text: dict[str, dict] = {}
    dropped = 0
    for row in buckets["literal_global"]:
        text = row.get("text", "")
        translation = row.get("translation", "")
        method = _effective_method(row)
        priority = 0 if method == "literal" else 1  # literal=0 (high), substr=1

        existing = by_text.get(text)
        if existing is None:
            by_text[text] = {"priority": priority, "row": row,
                             "method": method, "translation": translation}
            continue

        ex_method = existing["method"]
        ex_tx = existing["translation"]

        if priority < existing["priority"]:
            # New row higher priority (literal beats substr) → replace.
            if translation != ex_tx:
                print(
                    f"[WARN] literal_global text={text!r}: {method} replaces {ex_method} "
                    f"(translations differ: {ex_tx!r} -> {translation!r})",
                    file=sys.stderr,
                )
            by_text[text] = {"priority": priority, "row": row,
                             "method": method, "translation": translation}
            dropped += 1
        else:
            # Same or lower priority — keep existing.
            if translation != ex_tx:
                print(
                    f"[WARN] literal_global text={text!r}: {method} discarded "
                    f"({ex_method} wins; translations differ {ex_tx!r}/{translation!r})",
                    file=sys.stderr,
                )
            dropped += 1

    buckets["literal_global"] = [entry["row"] for entry in by_text.values()]
    stats["literal_global_dedup_dropped"] = dropped
    stats["literal_global"] = len(buckets["literal_global"])


def build(locale: str, *, dry_run: bool, soft: bool, ignore_validation: bool) -> int:
    xlsx_dir = TRANSLATIONS / locale
    xlsx_path = xlsx_dir / "Translation.xlsx"
    if not xlsx_dir.exists():
        print(f"[ERROR] Translations locale folder not found: {xlsx_dir}")
        return 1
    if not xlsx_path.exists():
        print(f"[ERROR] xlsx file not found: {xlsx_path}")
        return 1

    is_template = (locale == TEMPLATE_LOCALE)
    if is_template and not dry_run:
        print("[WARN] Template auto-routes to --dry-run "
              "(Template is the schema source, never deployed).")
        dry_run = True

    print(f"=== Build runtime TSV: {locale} {'(dry-run)' if dry_run else ''} ===")

    # 1. validation
    if ignore_validation:
        print("[1/5] Validation skipped (--ignore)")
    else:
        validate_tsv_dir = PARSED_TEXT if PARSED_TEXT.exists() else None
        mode = "soft" if soft else "hard"
        if validate_tsv_dir is None:
            print(f"[1/5] Validating (partial: parsed_text not found)... ({locale}, {mode})")
        else:
            print(f"[1/5] Validating... ({locale}, {mode})")
        try:
            result = validate_xlsx(xlsx_path, validate_tsv_dir, soft=soft)
        except (FileNotFoundError, ValueError) as e:
            print(f"[ERROR] Validation failed: {e}")
            return 1
        print(f"  -> log: {result.log_path}")
        if not result.ok:
            print(f"[ERROR] Validation failed: {result.error_count} errors")
            print("Aborting build.")
            return 1
        if result.warning_count > 0:
            print(f"  {result.warning_count} warnings (continuing)")
    print()

    # 2. load xlsx
    print("[2/5] Loading xlsx...")
    sheets = load_all_translation_sheets(xlsx_path)
    all_rows: list[dict] = []
    for _, _, rows in sheets:
        all_rows.extend(rows)
    print(f"  -> {len(sheets)} sheets, {len(all_rows)} rows loaded")

    # Template synthesis: make every empty translation echo `text` so the
    # downstream classifier doesn't drop the row as "untranslated".
    if is_template:
        synth = 0
        for row in all_rows:
            if not (row.get("translation") or "").strip():
                row["translation"] = row.get("text", "")
                synth += 1
        print(f"  Template synthesis: copied text→translation for {synth} rows")
    print()

    # 3. classify
    print("[3/5] Classifying rows...")
    buckets, stats = classify_rows(all_rows)
    _dedupe_literal_global(buckets, stats)
    for label in ("static", "literal_scoped", "pattern_scoped",
                  "literal_global", "pattern_global", "substr"):
        print(f"  {label:22s} {stats[label]:5d} rows")
    if stats.get("literal_global_dedup_dropped"):
        print(f"  literal_global dedup dropped: {stats['literal_global_dedup_dropped']}")
    print(f"  excluded (ignore)        {stats['excluded_ignore']:5d}")
    print(f"  excluded (untranslatable){stats['excluded_untranslatable']:5d}")
    print(f"  excluded (untranslated)  {stats['excluded_untranslated']:5d}")
    print()

    runtime_dir = _resolve_output_dir(locale, dry_run)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    # 4. metadata.tsv
    print(f"[4/5] Writing metadata.tsv -> {runtime_dir.relative_to(REPO)}")
    meta = load_metadata(xlsx_path)
    meta_path = runtime_dir / "metadata.tsv"
    with open(meta_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["field", "value"])
        for k, v in meta.items():
            writer.writerow([k, v])
    print(f"  -> {meta_path.relative_to(REPO)} ({len(meta)} fields)")
    print()

    # 5. write TSV buckets
    print(f"[5/5] Writing runtime TSVs -> {runtime_dir.relative_to(REPO)}")
    outputs = [
        ("translation_static.tsv",         COLUMNS_SCOPED, buckets["static"]),
        ("translation_literal_scoped.tsv", COLUMNS_SCOPED, buckets["literal_scoped"]),
        ("translation_pattern_scoped.tsv", COLUMNS_SCOPED, buckets["pattern_scoped"]),
        ("translation_literal.tsv",        COLUMNS_GLOBAL, buckets["literal_global"]),
        ("translation_pattern.tsv",        COLUMNS_GLOBAL, buckets["pattern_global"]),
        ("translation_substr.tsv",         COLUMNS_GLOBAL, buckets["substr"]),
    ]
    for name, columns, rows in outputs:
        path = runtime_dir / name
        write_tsv(path, columns, rows)
        print(f"  -> {path.relative_to(REPO)} ({len(rows)} rows)")
    print()
    print(f"Done. ({len(outputs) + 1} files in {runtime_dir.relative_to(REPO)})")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("locale", help="Locale name (e.g. Korean)")
    parser.add_argument("--dry-run", action="store_true",
                        help=f"Output to .tmp/temp_build/Trans To Vostok/<locale>/ instead of deploy path")
    parser.add_argument("--soft", action="store_true",
                        help="TSV match failure -> WARNING (continue) instead of ERROR")
    parser.add_argument("--ignore", action="store_true",
                        help="Skip validate_xlsx pre-check")
    args = parser.parse_args(argv[1:])

    return build(args.locale, dry_run=args.dry_run, soft=args.soft,
                 ignore_validation=args.ignore)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
