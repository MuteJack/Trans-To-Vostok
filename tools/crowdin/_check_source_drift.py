"""Detect drift between Crowdin's live source strings and local Crowdin_Mirror/source/.

For each source file on Crowdin, downloads its current strings via API and
compares `source_phrase` with the locally-committed Crowdin_Mirror/source/ TSV.

Differences indicate that:
  - Crowdin: source was edited directly on Crowdin's web UI (needs pull)
  - Local:   Template was updated but not yet pushed (needs push)

Usage:
    python tools/crowdin/check_source_drift.py
    python tools/crowdin/check_source_drift.py --rebuild-mirror
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
REPO = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
from crowdin.api_client import make_client, list_source_files  # noqa: E402

MIRROR_SOURCE_DIR = REPO / "Crowdin_Mirror" / "source"
SOURCE_PREFIX = "/Crowdin_Mirror/source"


def _load_mirror_tsv(path: Path) -> dict[str, str]:
    """Returns {identifier: source_phrase} from a Crowdin_Mirror/source TSV."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return {
            row["identifier"]: row.get("source_phrase", "")
            for row in reader
            if row.get("identifier", "").strip()
        }


def _fetch_crowdin_strings(client, project_id: int, file_id: int) -> dict[str, str]:
    """Returns {identifier: text} for all source strings in a Crowdin file."""
    out: dict[str, str] = {}
    offset = 0
    limit = 500
    while True:
        resp = client.source_strings.list_strings(
            projectId=project_id, fileId=file_id, limit=limit, offset=offset
        )
        items = resp.get("data", [])
        if not items:
            break
        for entry in items:
            d = entry["data"]
            ident = d.get("identifier", "")
            text = d.get("text", "")
            if ident:
                out[ident] = text
        if len(items) < limit:
            break
        offset += len(items)
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--rebuild-mirror", action="store_true",
        help="Run build_source.py first to refresh Crowdin_Mirror/source/ from Template.",
    )
    args = parser.parse_args(argv[1:])

    if args.rebuild_mirror:
        print("=== Rebuilding Crowdin_Mirror/source/ from Template ===")
        rc = subprocess.run(
            [sys.executable, "tools/crowdin/build_source.py"], cwd=REPO
        ).returncode
        if rc != 0:
            print("[ERROR] build_source.py failed", file=sys.stderr)
            return 1
        print()

    print("Connecting to Crowdin...")
    client, project_id, _ = make_client()
    all_files = list_source_files(client, project_id)
    print(f"  {len(all_files)} source files on Crowdin")
    print()

    # Filter to files under our source prefix
    our_files = {
        path: fid for path, fid in all_files.items()
        if path.startswith(SOURCE_PREFIX + "/")
    }
    print(f"  {len(our_files)} files under {SOURCE_PREFIX}")
    print()

    total_crowdin_only = 0
    total_local_only = 0
    total_changed = 0
    drifted_files: list[str] = []

    for crowdin_path, file_id in sorted(our_files.items()):
        # Map to local path: /Crowdin_Mirror/source/Translation/Main.tsv → Translation/Main.tsv
        rel = crowdin_path[len(SOURCE_PREFIX) + 1:]
        local_path = MIRROR_SOURCE_DIR / rel

        local_strings = _load_mirror_tsv(local_path)
        crowdin_strings = _fetch_crowdin_strings(client, project_id, file_id)

        crowdin_only = {k: v for k, v in crowdin_strings.items() if k not in local_strings}
        local_only = {k: v for k, v in local_strings.items() if k not in crowdin_strings}
        changed = {
            k: (local_strings[k], crowdin_strings[k])
            for k in crowdin_strings
            if k in local_strings and crowdin_strings[k] != local_strings[k]
        }

        if not crowdin_only and not local_only and not changed:
            print(f"[OK]    {rel}  ({len(crowdin_strings)} strings)")
            continue

        print(f"[DRIFT] {rel}  ({len(crowdin_strings)} Crowdin / {len(local_strings)} local)")
        drifted_files.append(rel)
        total_crowdin_only += len(crowdin_only)
        total_local_only += len(local_only)
        total_changed += len(changed)

        for ident, (local_text, crowdin_text) in sorted(changed.items()):
            print(f"  CHANGED   {ident!r}")
            print(f"    local  : {local_text[:80]!r}")
            print(f"    crowdin: {crowdin_text[:80]!r}")
        for ident in sorted(crowdin_only):
            print(f"  CROWDIN+  {ident!r}  (not in local mirror)")
        for ident in sorted(local_only):
            print(f"  LOCAL+    {ident!r}  (not on Crowdin)")

    print()
    print("=" * 60)
    if not drifted_files:
        print("No drift found — local mirror matches Crowdin source exactly.")
    else:
        print(f"Drift in {len(drifted_files)} file(s):")
        for f in drifted_files:
            print(f"  {f}")
        print()
        if total_changed:
            print(f"  source_phrase changed : {total_changed}")
        if total_crowdin_only:
            print(f"  strings only on Crowdin: {total_crowdin_only}  (→ push needed or Crowdin was edited)")
        if total_local_only:
            print(f"  strings only in local : {total_local_only}  (→ push needed)")
        print()
        print("If 'CROWDIN+' or 'CHANGED' entries exist -> Crowdin source was edited directly.")
        print("Run push_source_to_crowdin.py to overwrite Crowdin with local Template,")
        print("or manually apply Crowdin's edits to Template TSVs first.")
    return 0 if not drifted_files else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
