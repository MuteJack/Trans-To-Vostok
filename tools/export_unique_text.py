"""
Extract a deduplicated unique-text list from <locale>/Translation.xlsx for
machine-translation preparation (DeepL / LLM bulk translation).

Many UI labels and item terms repeat across sheets (e.g. "Common", "Cancel"),
so translating only unique source texts cuts the character budget significantly.
This tool walks every translation sheet, filters rows that should be machine-
translated, deduplicates by exact text, and writes the result for the next
pipeline stage (docx build / direct LLM call).

Filtering rules (a row is included only if all hold):
    - text != ""
    - method != "ignore"
    - method != "pattern"        (regex source — unsuitable for MT)
    - untranslatable != 1

Output (under <mod_root>/.tmp/unique_text/<locale>/):
    unique.tsv     unique_id, text, occurrences, char_count
    mapping.tsv    unique_id, sheet, row_in_sheet, text
    stats.txt      human-readable summary (totals, dedup ratio, per-sheet)

Usage:
    python tools/export_unique_text.py [<locale>]

Default locale: Korean (the most maintained source — text column is identical
across all locales since it holds the English source).
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
    load_all_translation_sheets,
    _effective_method,
)


BOOL_TRUE = {"1", "true"}

# methods that should NOT be sent to a translator
EXCLUDED_METHODS = {"ignore", "pattern"}


def collect_candidates(xlsx_path: Path) -> tuple[list[dict], dict]:
    """
    Walk every non-MetaData sheet and collect rows eligible for machine translation.
    Returns (rows, stats) where rows is a list of {sheet, row_in_sheet, text} dicts.
    row_in_sheet is 1-based over data rows only (header excluded).
    """
    sheets = load_all_translation_sheets(xlsx_path)
    rows: list[dict] = []
    stats: dict = {
        "sheets": {},
        "total_data_rows": 0,
        "excluded_empty_text": 0,
        "excluded_method_ignore": 0,
        "excluded_method_pattern": 0,
        "excluded_untranslatable": 0,
        "candidate_rows": 0,
    }

    for sheet_name, _header, sheet_rows in sheets:
        per_sheet = {
            "data_rows": 0,
            "candidates": 0,
            "candidate_chars": 0,
        }
        for idx, row in enumerate(sheet_rows, start=1):
            stats["total_data_rows"] += 1
            per_sheet["data_rows"] += 1

            text = row.get("text", "")
            if text == "":
                stats["excluded_empty_text"] += 1
                continue

            method = _effective_method(row)
            if method == "ignore":
                stats["excluded_method_ignore"] += 1
                continue
            if method == "pattern":
                stats["excluded_method_pattern"] += 1
                continue

            if row.get("untranslatable", "").strip().lower() in BOOL_TRUE:
                stats["excluded_untranslatable"] += 1
                continue

            rows.append({
                "sheet": sheet_name,
                "row_in_sheet": idx,
                "text": text,
            })
            stats["candidate_rows"] += 1
            per_sheet["candidates"] += 1
            per_sheet["candidate_chars"] += len(text)

        stats["sheets"][sheet_name] = per_sheet

    return rows, stats


def deduplicate(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Group rows by exact text. Returns (unique, mapping).
    unique:  [{unique_id, text, occurrences, char_count}, ...]  (insertion-order stable)
    mapping: [{unique_id, sheet, row_in_sheet, text}, ...]      (one entry per source row)
    """
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


def write_stats(path: Path, stats: dict, unique: list[dict], mapping: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate_chars = sum(u["char_count"] * u["occurrences"] for u in unique)
    unique_chars = sum(u["char_count"] for u in unique)
    reduction_pct = (1 - unique_chars / candidate_chars) * 100 if candidate_chars else 0.0

    lines = []
    lines.append(f"Total data rows scanned       : {stats['total_data_rows']:>8d}")
    lines.append(f"  excluded (empty text)       : {stats['excluded_empty_text']:>8d}")
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

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    locale = args[0] if args else "Korean"

    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    pkg_root = mod_root / "Trans To Vostok"
    locale_dir = pkg_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"
    out_dir = mod_root / ".tmp" / "unique_text" / locale

    if not locale_dir.exists():
        print(f"[ERROR] Locale folder not found: {locale_dir}")
        return 1
    if not xlsx_path.exists():
        print(f"[ERROR] Translation.xlsx not found: {xlsx_path}")
        return 1

    print(f"Source : {xlsx_path}")
    print(f"Output : {out_dir}")
    print()

    print("[1/3] Scanning sheets...")
    try:
        rows, stats = collect_candidates(xlsx_path)
    except PermissionError:
        print(f"[ERROR] Cannot read xlsx (file locked? close Excel and retry): {xlsx_path}")
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
    write_tsv(mapping_path, ["unique_id", "sheet", "row_in_sheet", "text"], mapping)
    summary = write_stats(stats_path, stats, unique, mapping)

    print(f"  -> {unique_path.relative_to(mod_root)}")
    print(f"  -> {mapping_path.relative_to(mod_root)}")
    print(f"  -> {stats_path.relative_to(mod_root)}")
    print()
    print("=" * 60)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
