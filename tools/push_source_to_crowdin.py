"""Sync Crowdin source files from Translations/Template/.

Two-step pipeline:
  1. crowdin/build_source.py        Template TSVs → Crowdin_Mirror/source/<cat>/<sheet>.tsv
  2. Crowdin SDK upload             Crowdin_Mirror/source/* → Crowdin project
                                    - Missing files     → add (new strings appear on Crowdin)
                                    - Existing files    → update (preserves translations
                                                                  for unchanged ids)
                                    - Missing dirs      → auto-created

What this does:
  - Adds NEW source strings (new sign / billboard / sheet) to Crowdin.
  - Updates existing source strings if their text changed.
  - Existing translations for unchanged identifiers stay intact.
  - Directories on Crowdin auto-created to mirror the Template tree.

What this does NOT do:
  - Does NOT push per-locale translations. Use tools/push_to_crowdin.py for that.
  - Does NOT delete files removed from Template (they're hidden on Crowdin
    via restore semantics — recoverable; clean them up manually if needed).

Required setup:
  - Python deps:    pip install -r tools/requirements.txt
  - Crowdin token:  tools/configs/secrets.json:crowdin_personal_token
                    (token must have Source Files + Storage scope)

Usage:
    python tools/push_source_to_crowdin.py             # build + push
    python tools/push_source_to_crowdin.py --skip-build  # push only (assumes Crowdin_Mirror/source/ already fresh)
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crowdin.api_client import upload_source_files

REPO = Path(__file__).resolve().parent.parent
MIRROR_SOURCE_DIR = REPO / "Crowdin_Mirror" / "source"


def run_build_source() -> bool:
    """Refresh Crowdin_Mirror/source/ from Template TSVs."""
    print("=== Refreshing source TSVs from Template ===")
    cmd = [sys.executable, "tools/crowdin/build_source.py"]
    result = subprocess.run(cmd, cwd=REPO)
    if result.returncode != 0:
        print("[ERROR] build_source.py failed", file=sys.stderr)
        return False
    print()
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-build", action="store_true",
        help="Skip build_source.py; upload Crowdin_Mirror/source/ as-is")
    args = parser.parse_args(argv[1:])

    if not args.skip_build:
        if not run_build_source():
            return 1

    if not MIRROR_SOURCE_DIR.exists():
        print(f"[ERROR] {MIRROR_SOURCE_DIR} missing — run without --skip-build first",
              file=sys.stderr)
        return 1

    print("=== Uploading source files to Crowdin ===")
    stats = upload_source_files(MIRROR_SOURCE_DIR)

    print()
    print("=== Summary ===")
    print(f"  Added   : {stats['added']}")
    print(f"  Updated : {stats['updated']}")
    print(f"  Errors  : {len(stats['errors'])}")
    if stats["errors"]:
        for rel, msg in stats["errors"]:
            print(f"    - {rel}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
