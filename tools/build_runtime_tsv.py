"""
Translation.xlsx → runtime TSV build script.

Behavior:
1. Validate <locale>/Translation.xlsx via validate_xlsx() (build fails on error)
2. Collect rows from all sheets except MetaData
3. Exclude rows with ignore=1
4. Exclude rows with empty translation
5. Classify by method + location into 5 runtime TSVs (output goes to <locale>/runtime_tsv/):
       translation_static.tsv           — method=static                      (5 fields + text + translation)
       translation_literal_scoped.tsv   — method=literal/"" + location        (5 fields + text + translation)
       translation_pattern_scoped.tsv   — method=pattern + location           (5 fields + text + translation)
       translation_literal.tsv          — method=literal/"" + no location     (text + translation)
       translation_pattern.tsv          — method=pattern + no location        (text + translation)
6. Atomic write (.tmp → rename)

Runtime matching priority (translator.gd attempts in this order):
    1. static exact          (exact 5-tuple, TSV-validated)
    2. scoped literal exact  (exact 5-tuple, dynamic text)
    3. scoped pattern exact  (full context match + regex)
    4. literal global        (text-only)
    5. pattern global        (global regex)
    6. static score          (partial context score matching, game-update fallback)
    7. scoped literal score  (dynamic text partial context match)
    8. scoped pattern score  (regex + partial context)

Usage:
    python build_runtime_tsv.py <locale>

Example:
    python build_runtime_tsv.py Korean
"""
import csv
import sys
from pathlib import Path

try:
    import openpyxl  # noqa: F401
except ImportError:
    print("ERROR: openpyxl is required. pip install openpyxl", file=sys.stderr)
    sys.exit(1)

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_translation import (
    validate_xlsx,
    load_all_translation_sheets,
    load_metadata,
    _effective_method,
)


# TSV with context (static / scoped literal / scoped pattern)
COLUMNS_SCOPED = ["location", "parent", "name", "type", "text", "translation"]
# Global TSV (literal / pattern)
COLUMNS_GLOBAL = ["text", "translation"]

BOOL_TRUE = {"1", "true"}


def classify_rows(rows: list[dict]) -> tuple[dict, dict]:
    """
    Classify rows into 5 runtime buckets.

    Exclusion conditions:
        - method=ignore               (operational exclusion)
        - untranslatable=1             (untranslatable text)
        - empty translation            (untranslated)

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
            # substr → also write to literal_global (fast hit at tier 4 on exact match)
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


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    soft = "--soft" in flags
    ignore_validation = "--ignore" in flags

    if not args:
        print("Usage: python build_runtime_tsv.py <locale> [--soft|--hard|--ignore]")
        print("  --hard (default): TSV match failure -> ERROR (block build)")
        print("  --soft:           TSV match failure -> WARNING (continue build)")
        print("  --ignore:         skip validation step (build immediately)")
        print("Example: python build_runtime_tsv.py Korean --soft")
        return 1

    locale = args[0]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    pkg_root = mod_root / "Trans To Vostok"
    locale_dir = pkg_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"
    tsv_dir = mod_root / ".tmp" / "parsed_text"

    if not locale_dir.exists():
        print(f"[ERROR] Locale folder not found: {locale_dir}")
        return 1
    if not xlsx_path.exists():
        print(f"[ERROR] xlsx file not found: {xlsx_path}")
        return 1

    # 1. validation
    if ignore_validation:
        print(f"[1/5] Validation skipped (--ignore)")
        print()
    else:
        mode = "soft" if soft else "hard"
        print(f"[1/5] Validating... ({locale}, {mode})")
        try:
            result = validate_xlsx(xlsx_path, tsv_dir, soft=soft)
        except (FileNotFoundError, ValueError) as e:
            print(f"[ERROR] Validation failed: {e}")
            return 1

        print(f"  -> log: {result.log_path}")
        if not result.ok:
            print(
                f"[ERROR] Validation failed: {result.error_count} errors "
                f"(TSV {result.error_tsv}, flags {result.error_flags}, "
                f"duplicates {result.error_dup}, method {result.error_method})"
            )
            print("Aborting build. Check the log above.")
            raise SystemExit(1)

        if result.warning_count > 0:
            print(f"  {result.warning_count} warnings (continuing)")
        print()

    # 2. load xlsx (merge all translation sheets)
    print("[2/4] Loading xlsx...")
    sheets = load_all_translation_sheets(xlsx_path)
    all_rows: list[dict] = []
    for _sheet_name, _header, rows in sheets:
        all_rows.extend(rows)
    print(f"  -> {len(sheets)} sheets, {len(all_rows)} rows loaded")
    print()

    # 3. classify
    print("[3/4] Classifying rows...")
    buckets, stats = classify_rows(all_rows)
    print(f"  static                 {stats['static']:4d} rows")
    print(f"  literal_scoped         {stats['literal_scoped']:4d} rows")
    print(f"  pattern_scoped         {stats['pattern_scoped']:4d} rows")
    print(f"  literal (global)       {stats['literal_global']:4d} rows")
    print(f"  pattern (global)       {stats['pattern_global']:4d} rows")
    print(f"  substr                 {stats['substr']:4d} rows")
    print(f"  excluded (ignore)      {stats['excluded_ignore']:4d} rows")
    print(f"  excluded (untranslatable) {stats['excluded_untranslatable']:4d} rows")
    print(f"  excluded (untranslated)   {stats['excluded_untranslated']:4d} rows")
    print()

    runtime_dir = locale_dir / "runtime_tsv"

    # 4. generate metadata.tsv
    print("[4/5] Generating metadata.tsv...")
    meta = load_metadata(xlsx_path)
    meta_path = runtime_dir / "metadata.tsv"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["field", "value"])
        for k, v in meta.items():
            writer.writerow([k, v])
    print(f"  -> {meta_path.relative_to(mod_root)} ({len(meta)} fields)")
    print()

    # 5. write TSV
    print("[5/5] Writing TSV...")

    outputs = [
        (runtime_dir / "translation_static.tsv",         COLUMNS_SCOPED, buckets["static"]),
        (runtime_dir / "translation_literal_scoped.tsv", COLUMNS_SCOPED, buckets["literal_scoped"]),
        (runtime_dir / "translation_pattern_scoped.tsv", COLUMNS_SCOPED, buckets["pattern_scoped"]),
        (runtime_dir / "translation_literal.tsv",        COLUMNS_GLOBAL, buckets["literal_global"]),
        (runtime_dir / "translation_pattern.tsv",        COLUMNS_GLOBAL, buckets["pattern_global"]),
        (runtime_dir / "translation_substr.tsv",         COLUMNS_GLOBAL, buckets["substr"]),
    ]

    for out_path, columns, rows in outputs:
        write_tsv(out_path, columns, rows)
        print(f"  -> {out_path.relative_to(mod_root)} ({len(rows)} rows)")

    # cleanup legacy files at locale root (moved to runtime_tsv/ subfolder, plus older formats)
    legacy_names = (
        "translation.tsv",
        "translation_expression.tsv",
        "translation_static.tsv",
        "translation_literal_scoped.tsv",
        "translation_pattern_scoped.tsv",
        "translation_literal.tsv",
        "translation_pattern.tsv",
        "translation_substr.tsv",
        "metadata.tsv",
    )
    for legacy_name in legacy_names:
        legacy_path = locale_dir / legacy_name
        if legacy_path.exists():
            try:
                legacy_path.unlink()
                print(f"  x {legacy_path.relative_to(mod_root)} (moved to runtime_tsv/)")
            except OSError as e:
                print(f"  [WARN] Failed to remove legacy file: {legacy_path} ({e})")

    print()
    print("=" * 60)
    print(f"Build complete: {locale}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
