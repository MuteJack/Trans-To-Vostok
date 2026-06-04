"""Phase 3 helper — clear .tmp/temp_build/ (dry-run staging directory).

Removes the entire .tmp/temp_build/ tree so the next dry-run build
starts from a clean state. No-op if the directory does not exist.

Used by build_mod_package.py as the first step of the dry-run
build pipeline.

Usage:
  python tools/build/clear_temp_build.py
"""
import argparse
import shutil
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
TEMP_BUILD = REPO / ".tmp" / "temp_build"


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.parse_args(argv[1:])  # reject extras

    _say("=== clear_temp_build ===")
    if not TEMP_BUILD.exists():
        _say(f"  [OK] {TEMP_BUILD.relative_to(REPO)} does not exist (nothing to clear)")
        return 0

    _say(f"  Removing: {TEMP_BUILD.relative_to(REPO)}")
    try:
        shutil.rmtree(TEMP_BUILD)
    except OSError as e:
        _say(f"[ERROR] Failed to remove: {e}")
        return 1
    _say("  -> cleared")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
