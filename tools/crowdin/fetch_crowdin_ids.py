"""Replace tmp: identifiers on Crowdin with permanent numeric_id, and rewrite
the canonical TSV's identifier column to match.

Workflow position:
  rebuild_xlsx → build_translation_tsv → register_new_strings → push_source
  → fetch_crowdin_ids (this tool) → git commit

For each Crowdin string whose `identifier` still starts with `tmp:`, this
tool:
  1. PATCHes the identifier to `str(numeric_id)` (the canonical scheme)
  2. Records the mapping {tmp: identifier -> numeric_id_str}

Then it walks the canonical TSVs and replaces every matching tmp: value in
the identifier column with the corresponding numeric_id_str.

After this tool runs, the canonical TSV identifier column has only numeric
identifiers, and Crowdin agrees.

Usage:
    python tools/crowdin/fetch_crowdin_ids.py            # execute
    python tools/crowdin/fetch_crowdin_ids.py --dry-run  # list what would change
"""
import argparse
import csv
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
REPO = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
from crowdin.api_client import make_client, list_source_files

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


TRANSLATIONS = REPO / "Translations"
SLEEP_SEC = 0.2  # 5 PATCH/sec (well under Crowdin's 20/sec limit)


def fetch_tmp_strings(client, project_id: int) -> list[dict]:
    """Return [{file, string_id, identifier}, ...] for every string whose
    identifier still uses the `tmp:` bootstrap form."""
    out: list[dict] = []
    files = list_source_files(client, project_id)
    for full_path, file_id in sorted(files.items()):
        offset = 0
        while True:
            resp = client.source_strings.list_strings(
                projectId=project_id, fileId=file_id, limit=500, offset=offset)
            items = resp.get("data", [])
            if not items:
                break
            for it in items:
                d = it["data"]
                if d["identifier"].startswith("tmp:"):
                    out.append({
                        "file": full_path,
                        "string_id": d["id"],
                        "identifier": d["identifier"],
                    })
            if len(items) < 500:
                break
            offset += len(items)
    return out


def patch_to_numeric(client, project_id: int, entries: list[dict]) -> dict[str, str]:
    """PATCH each tmp identifier to str(string_id). Returns
    {old_tmp_identifier: new_numeric_str_identifier}."""
    mapping: dict[str, str] = {}
    for i, e in enumerate(entries, 1):
        new_id = str(e["string_id"])
        patch = [{"op": "replace", "path": "/identifier", "value": new_id}]
        try:
            client.source_strings.edit_string(
                projectId=project_id, stringId=e["string_id"], data=patch)
            mapping[e["identifier"]] = new_id
        except Exception as ex:
            print(f"  [FAIL] id={e['string_id']}: {ex}")
        if i % 50 == 0:
            print(f"  {i}/{len(entries)} PATCHed")
        time.sleep(SLEEP_SEC)
    return mapping


def rewrite_tsv_identifiers(mapping: dict[str, str], *, dry_run: bool) -> dict:
    """Walk every canonical TSV; replace tmp: identifiers using `mapping`."""
    stats = {"files_touched": 0, "rows_replaced": 0, "tmp_not_in_map": 0}
    for locale_dir in sorted(TRANSLATIONS.iterdir()):
        if not locale_dir.is_dir():
            continue
        for category in ("Translation", "Texture"):
            cat_dir = locale_dir / "tsv" / category
            if not cat_dir.exists():
                continue
            for tsv in sorted(cat_dir.glob("*.tsv")):
                if tsv.name.startswith("_"):
                    continue
                with open(tsv, encoding="utf-8", newline="") as f:
                    rows = list(csv.reader(f, delimiter="\t"))
                if not rows or "identifier" not in rows[0]:
                    continue
                id_idx = rows[0].index("identifier")
                changed = 0
                for r in rows[1:]:
                    while len(r) < len(rows[0]):
                        r.append("")
                    cid = (r[id_idx] or "").strip()
                    if not cid.startswith("tmp:"):
                        continue
                    new_id = mapping.get(cid)
                    if new_id is None:
                        stats["tmp_not_in_map"] += 1
                        continue
                    r[id_idx] = new_id
                    changed += 1
                if changed:
                    stats["files_touched"] += 1
                    stats["rows_replaced"] += changed
                    if not dry_run:
                        tmp_path = tsv.with_suffix(tsv.suffix + ".tmp")
                        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
                            w = csv.writer(f, delimiter="\t", lineterminator="\n",
                                           quoting=csv.QUOTE_MINIMAL)
                            for r in rows:
                                w.writerow(r)
                        tmp_path.replace(tsv)
    return stats


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Discover what would change; PATCH and write nothing")
    args = parser.parse_args(argv[1:])

    client, project_id, _ = make_client()
    print(f"Project: {project_id}")
    print(f"Mode   : {'DRY-RUN' if args.dry_run else 'EXECUTE'}")
    print()

    print("Scanning Crowdin for tmp: identifiers...")
    entries = fetch_tmp_strings(client, project_id)
    print(f"  found: {len(entries)}")
    for e in entries[:10]:
        print(f"    {e['file']}  id={e['string_id']}  identifier={e['identifier']!r}")
    if len(entries) > 10:
        print(f"    ... and {len(entries) - 10} more")
    print()

    if not entries:
        print("Nothing to do. (No tmp: identifiers on Crowdin.)")
        return 0

    if args.dry_run:
        print("DRY-RUN — skipping PATCH. Would write back to canonical TSV after PATCH.")
        return 0

    print("PATCHing identifiers -> numeric...")
    mapping = patch_to_numeric(client, project_id, entries)
    print(f"  PATCHed: {len(mapping)}")
    print()

    print("Rewriting canonical TSV identifier columns...")
    stats = rewrite_tsv_identifiers(mapping, dry_run=False)
    print(f"  files touched : {stats['files_touched']}")
    print(f"  rows replaced : {stats['rows_replaced']}")
    if stats["tmp_not_in_map"]:
        print(f"  [WARN] {stats['tmp_not_in_map']} tmp rows in TSV not in Crowdin "
              f"(may be unpushed local additions)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
