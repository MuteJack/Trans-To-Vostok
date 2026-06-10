"""Produce a locale's runtime TSV bundle for the mod build.

This is the locale-side build step that takes the canonical translation
data and emits the runtime TSV bundle the in-game translator consumes:

    translation_static.tsv
    translation_literal_scoped.tsv
    translation_pattern_scoped.tsv
    translation_literal.tsv
    translation_pattern.tsv
    translation_substr.tsv

Source: Translations/<locale>/tsv/Translation/*.tsv  (canonical TSV files)

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

Usage:
  python tools/build/build_runtime_tsv.py Korean
  python tools/build/build_runtime_tsv.py Korean --dry-run
  python tools/build/build_runtime_tsv.py all --dry-run
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

from helper.helper_translation_common import _effective_method
from helper.helper_locale_config import load_locales  # noqa: E402
from helper.helper_log import setup_logpath  # noqa: E402


# TSV with context (static / scoped literal / scoped pattern)
COLUMNS_SCOPED = ["location", "parent", "name", "type", "text", "translation"]
# Global TSV (literal / pattern)
COLUMNS_GLOBAL = ["text", "translation"]
BOOL_TRUE = {"1", "true"}


def classify_rows(rows: list[dict]) -> tuple[dict, dict]:
    """Classify rows into runtime buckets.

    Exclusion conditions:
        - method=ignore               (operational exclusion)
        - untranslatable=1            (untranslatable text)
        - empty translation           (untranslated)

    Returns:
        buckets: { bucket_name: [row, ...], ... }
        stats:   { bucket_name: count, ..., "excluded_ignore": N, ... }
    """
    buckets: dict[str, list] = {
        "static": [],
        "literal_scoped": [],
        "pattern_scoped": [],
        "literal_global": [],
        "pattern_global": [],
        "substr": [],
    }
    stats = {
        "total": len(rows),
        "excluded_ignore": 0,
        "excluded_untranslatable": 0,
        "excluded_untranslated": 0,
    }
    for name in buckets.keys():
        stats[name] = 0

    for row in rows:
        effective = _effective_method(row)
        if effective == "ignore":
            stats["excluded_ignore"] += 1
            continue

        if row.get("untranslatable", "").strip().lower() in BOOL_TRUE:
            stats["excluded_untranslatable"] += 1
            continue

        if row.get("translation", "") == "":
            stats["excluded_untranslated"] += 1
            continue
        location = row.get("location", "").strip()

        if effective == "static":
            buckets["static"].append(row)
            stats["static"] += 1
        elif effective == "literal":
            if location:
                buckets["literal_scoped"].append(row)
                stats["literal_scoped"] += 1
            else:
                buckets["literal_global"].append(row)
                stats["literal_global"] += 1
        elif effective == "pattern":
            if location:
                buckets["pattern_scoped"].append(row)
                stats["pattern_scoped"] += 1
            else:
                buckets["pattern_global"].append(row)
                stats["pattern_global"] += 1
        elif effective == "substr":
            buckets["substr"].append(row)
            # substr -> also write to literal_global (fast hit at tier 4 on exact match)
            text = row.get("text", "")
            translation = row.get("translation", "")
            conflict = False
            for existing in buckets["literal_global"]:
                if existing.get("text", "") == text and existing.get("translation", "") != translation:
                    conflict = True
                    print(
                        f"[WARN] substr/literal translation conflict: text={text!r} "
                        f"(substr={translation!r} vs literal={existing.get('translation', '')!r})",
                        file=sys.stderr,
                    )
                    break
            if not conflict:
                buckets["literal_global"].append(row)
            stats["substr"] += 1

    return buckets, stats


def write_tsv(out_path: Path, columns: list[str], rows: list[dict]) -> None:
    """Write TSV atomically."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([row.get(c, "") for c in columns])
        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


TRANSLATIONS = REPO / "Translations"
PKG_ROOT = REPO / "Trans To Vostok"
DRY_RUN_ROOT = REPO / ".tmp" / "temp_build" / "Trans To Vostok"
PARSED_TEXT = REPO / ".tmp" / "parsed_text"
TEMPLATE_LOCALE = "Template"
SOURCE_LOCALE = "English"


def _discover_enabled_locales() -> list[str]:
    out: list[str] = []
    for loc in load_locales():
        name = loc.get("dir")
        if loc.get("enabled") and name and name not in (SOURCE_LOCALE, TEMPLATE_LOCALE):
            out.append(name)
    return out


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


def _load_tsv_dir(tsv_dir: Path) -> tuple[int, list[dict]]:
    """Load all *.tsv files from directory. Returns (file_count, merged_rows)."""
    rows: list[dict] = []
    file_count = 0
    for tsv_path in sorted(tsv_dir.glob("*.tsv")):
        file_count += 1
        with open(tsv_path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                rows.append(row)
    return file_count, rows


def build(locale: str, *, dry_run: bool) -> int:
    tsv_dir = TRANSLATIONS / locale / "tsv" / "Translation"
    if not tsv_dir.exists():
        print(f"[ERROR] TSV directory not found: {tsv_dir}")
        return 1

    is_template = (locale == TEMPLATE_LOCALE)
    if is_template and not dry_run:
        print("[WARN] Template auto-routes to --dry-run "
              "(Template is the schema source, never deployed).")
        dry_run = True

    print(f"=== Build runtime TSV: {locale} {'(dry-run)' if dry_run else ''} ===")

    # 1. load canonical TSVs
    print("[1/3] Loading canonical TSVs...")
    file_count, all_rows = _load_tsv_dir(tsv_dir)
    if file_count == 0:
        print(f"[ERROR] No TSV files found in {tsv_dir}")
        return 1
    print(f"  -> {file_count} files, {len(all_rows)} rows loaded")

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

    # 2. classify
    print("[2/3] Classifying rows...")
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

    # 3. write TSV buckets
    print(f"[3/3] Writing runtime TSVs -> {runtime_dir.relative_to(REPO)}")
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
    print(f"Done. ({len(outputs)} files in {runtime_dir.relative_to(REPO)})")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("locale", help="Locale name (e.g. Korean)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Output to .tmp/temp_build/Trans To Vostok/<locale>/ instead of deploy path")
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file "
                             "(used by orchestrator)")
    args = parser.parse_args(argv[1:])
    setup_logpath(args.logpath, label=Path(__file__).stem)

    if args.locale == "all":
        locales = _discover_enabled_locales()
        if not locales:
            print("[ERROR] no enabled locales found in src/locale.json", file=sys.stderr)
            return 1
        overall = 0
        for loc in locales:
            rc = build(loc, dry_run=args.dry_run)
            if rc != 0:
                overall = rc
        return overall

    return build(args.locale, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
