"""
Extract unique source texts from a target locale's canonical TSV files.

Sources scanned (all under Translations/<target_locale>/):
    - tsv/Translation/*.tsv   (game text, with method/untranslatable filters)
    - tsv/Texture/*.tsv       (image labels — capitalized Text/Translation columns)

Filter logic per row (per TSV's column conventions):
    - text must be non-empty
    - translation must be empty (already-translated rows are excluded — saves
      DeepL quota on re-runs and preserves human/curated edits)
    - method != ignore  (operational exclusion, only for Translation TSVs)
    - method != pattern (regex source, only for Translation TSVs)
    - untranslatable != 1 (only when the TSV has that column)

Then dedupe by exact text (same English source across all TSVs -> single
unique entry, ensuring identical DeepL output everywhere).

Output (under <mod_root>/.tmp/unique_text/<target_locale>/):
    unique.tsv     unique_id, text, occurrences, char_count
    mapping.tsv    unique_id, source_file, sheet, row_in_sheet, text
    stats.txt      human-readable summary

Usage:
    python tools/translator/helper/export_unique_text.py <target_locale>

Example:
    python tools/translator/helper/export_unique_text.py French
    python tools/translator/helper/export_unique_text.py Japanese
"""
import csv
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


BOOL_TRUE = {"1", "true"}

# Per-TSV-directory column configuration. None == column not present.
TSV_DIRS = [
    {
        "name": "Translation",
        "tsv_dir_rel": Path("tsv") / "Translation",
        "text_col": "text",
        "trans_col": "translation",
        "method_col": "method",
        "untrans_col": "untranslatable",
    },
    {
        "name": "Texture",
        "tsv_dir_rel": Path("tsv") / "Texture",
        "text_col": "Text",
        "trans_col": "Translation",
        "method_col": None,
        "untrans_col": None,
    },
]


def _empty_stats() -> dict:
    return {
        "sheets": {},
        "total_data_rows": 0,
        "excluded_empty_text": 0,
        "excluded_already_translated": 0,
        "excluded_method_ignore": 0,
        "excluded_method_pattern": 0,
        "excluded_untranslatable": 0,
        "candidate_rows": 0,
    }


def collect_from_tsv_dir(tsv_dir: Path, cfg: dict) -> tuple[list[dict], dict]:
    """Read one TSV directory using its column config, return (rows, stats)."""
    rows: list[dict] = []
    stats = _empty_stats()
    if not tsv_dir.exists():
        return rows, stats

    for tsv_path in sorted(tsv_dir.glob("*.tsv")):
        sheet_name = tsv_path.stem
        try:
            with open(tsv_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                fieldnames = reader.fieldnames or []

                text_col = cfg["text_col"]
                trans_col = cfg["trans_col"]
                if text_col not in fieldnames or trans_col not in fieldnames:
                    continue  # not a translation sheet

                method_col = cfg["method_col"]
                untrans_col = cfg["untrans_col"]
                per_sheet = {"data_rows": 0, "candidates": 0, "candidate_chars": 0}

                for row_idx, row in enumerate(reader, start=1):
                    stats["total_data_rows"] += 1
                    per_sheet["data_rows"] += 1

                    text = row.get(text_col, "").strip()
                    if not text:
                        stats["excluded_empty_text"] += 1
                        continue

                    if row.get(trans_col, "").strip():
                        stats["excluded_already_translated"] += 1
                        continue

                    if untrans_col:
                        if row.get(untrans_col, "").strip().lower() in BOOL_TRUE:
                            stats["excluded_untranslatable"] += 1
                            continue

                    if method_col:
                        method_str = row.get(method_col, "").strip().lower()
                        if method_str == "ignore":
                            stats["excluded_method_ignore"] += 1
                            continue
                        if method_str == "pattern":
                            stats["excluded_method_pattern"] += 1
                            continue

                    rows.append({
                        "source_file": cfg["name"],
                        "sheet": sheet_name,
                        "row_in_sheet": row_idx,
                        "text": text,
                    })
                    stats["candidate_rows"] += 1
                    per_sheet["candidates"] += 1
                    per_sheet["candidate_chars"] += len(text)

                stats["sheets"][f"{cfg['name']}/{sheet_name}"] = per_sheet
        except Exception as e:
            print(f"  [WARN] Cannot read {tsv_path.name}: {e}", file=sys.stderr)

    return rows, stats


def collect_candidates(locale_dir: Path) -> tuple[list[dict], dict]:
    """Read all configured TSV directories and merge candidate rows + stats."""
    all_rows: list[dict] = []
    combined = _empty_stats()

    for cfg in TSV_DIRS:
        tsv_dir = locale_dir / cfg["tsv_dir_rel"]
        rows, stats = collect_from_tsv_dir(tsv_dir, cfg)
        all_rows.extend(rows)
        combined["sheets"].update(stats["sheets"])
        for k in ("total_data_rows", "excluded_empty_text", "excluded_already_translated",
                  "excluded_method_ignore", "excluded_method_pattern",
                  "excluded_untranslatable", "candidate_rows"):
            combined[k] += stats[k]

    return all_rows, combined


def deduplicate(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Group rows by exact text. Returns (unique, mapping)."""
    text_to_id: dict[str, int] = {}
    unique: list[dict] = []
    mapping: list[dict] = []

    for row in rows:
        text = row["text"]
        if text in text_to_id:
            uid = text_to_id[text]
            unique[uid - 1]["occurrences"] += 1
        else:
            uid = len(unique) + 1
            text_to_id[text] = uid
            unique.append({
                "unique_id": uid,
                "text": text,
                "occurrences": 1,
                "char_count": len(text),
            })
        mapping.append({
            "unique_id": uid,
            "source_file": row.get("source_file", ""),
            "sheet": row["sheet"],
            "row_in_sheet": row["row_in_sheet"],
            "text": text,
        })

    return unique, mapping


def write_tsv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([row.get(c, "") for c in columns])
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def write_stats(path: Path, stats: dict, unique: list[dict], mapping: list[dict],
                target_locale: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate_chars = sum(u["char_count"] * u["occurrences"] for u in unique)
    unique_chars = sum(u["char_count"] for u in unique)
    reduction_pct = (1 - unique_chars / candidate_chars) * 100 if candidate_chars else 0.0

    lines = []
    lines.append(f"Target locale: {target_locale}")
    lines.append("")
    lines.append(f"Total data rows scanned       : {stats['total_data_rows']:>8d}")
    lines.append(f"  excluded (empty text)       : {stats['excluded_empty_text']:>8d}")
    lines.append(f"  excluded (already translated): {stats['excluded_already_translated']:>8d}")
    lines.append(f"  excluded (method=ignore)    : {stats['excluded_method_ignore']:>8d}")
    lines.append(f"  excluded (method=pattern)   : {stats['excluded_method_pattern']:>8d}")
    lines.append(f"  excluded (untranslatable=1) : {stats['excluded_untranslatable']:>8d}")
    lines.append(f"  candidate rows              : {stats['candidate_rows']:>8d}")
    lines.append("")
    lines.append(f"Unique texts                  : {len(unique):>8d}")
    lines.append(f"Mapping entries               : {len(mapping):>8d}")
    lines.append("")
    lines.append(f"Total chars (all candidates)  : {candidate_chars:>8d}")
    lines.append(f"Total chars (unique only)     : {unique_chars:>8d}")
    lines.append(f"Dedup char reduction          : {reduction_pct:>7.2f} %")
    lines.append("")
    lines.append("Per-sheet breakdown:")
    lines.append(f"  {'sheet':<22s}  {'data':>6s}  {'cand':>6s}  {'chars':>8s}")
    for sheet_name, per in stats["sheets"].items():
        lines.append(
            f"  {sheet_name:<22s}  {per['data_rows']:>6d}  "
            f"{per['candidates']:>6d}  {per['candidate_chars']:>8d}"
        )

    summary = "\n".join(lines)
    path.write_text(summary + "\n", encoding="utf-8")
    return summary


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Usage: python tools/translator/helper/export_unique_text.py <target_locale>")
        print("Example: python tools/translator/helper/export_unique_text.py French")
        return 1

    target_locale = args[0]

    script_dir = Path(__file__).resolve().parent
    # script_dir = mods/Trans To Vostok/tools/translator/helper
    mod_root = script_dir.parent.parent.parent
    translations_root = mod_root / "Translations"
    locale_dir = translations_root / target_locale
    out_dir = mod_root / ".tmp" / "unique_text" / target_locale

    if not locale_dir.exists():
        print(f"[ERROR] Locale folder not found: {locale_dir}")
        print(f"  Create it first by copying from Template.")
        return 1

    # Report which TSV directories will be scanned
    print(f"Locale folder : {locale_dir}")
    print(f"Output folder : {out_dir}")
    print(f"Scanning TSV directories:")
    for cfg in TSV_DIRS:
        p = locale_dir / cfg["tsv_dir_rel"]
        marker = "yes" if p.exists() else "absent (skip)"
        print(f"  - {cfg['name']:<20s}  ({marker})")
    print()

    print("[1/3] Scanning TSVs...")
    try:
        rows, stats = collect_candidates(locale_dir)
    except PermissionError as e:
        print(f"[ERROR] Cannot read TSV (file locked?): {e}")
        return 1

    print(f"  -> {stats['candidate_rows']} candidate rows from {stats['total_data_rows']} total")
    print()

    print("[2/3] Deduplicating...")
    unique, mapping = deduplicate(rows)
    print(f"  -> {len(unique)} unique texts (from {len(mapping)} candidates)")
    print()

    print("[3/3] Writing output...")
    unique_path = out_dir / "unique.tsv"
    mapping_path = out_dir / "mapping.tsv"
    stats_path = out_dir / "stats.txt"

    write_tsv(unique_path, ["unique_id", "text", "occurrences", "char_count"], unique)
    write_tsv(mapping_path, ["unique_id", "source_file", "sheet", "row_in_sheet", "text"], mapping)
    summary = write_stats(stats_path, stats, unique, mapping, target_locale)

    print(f"  -> {unique_path.relative_to(mod_root)}")
    print(f"  -> {mapping_path.relative_to(mod_root)}")
    print(f"  -> {stats_path.relative_to(mod_root)}")
    print()
    print("=" * 60)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
