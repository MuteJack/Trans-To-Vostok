"""
Run all translatable-text parsers sequentially.

Wraps the three parsers under tools/utils/:
    1. parse_tscn_text.py  - extract text from .tscn scene files
    2. parse_tres_text.py  - extract text from .tres resource files
    3. parse_gd_text.py    - extract UI strings from .gd scripts

Each parser uses its own default input/output paths
(<mod_root>/.tmp/pck_recovered/ -> <mod_root>/.tmp/parsed_text/).
For custom paths, run a parser directly:
    python tools/utils/parse_tscn_text.py <src> <out>

Usage:
    python tools/parse_translatables.py
"""
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


PARSERS = [
    ("parse_tscn_text.py", ".tscn scene files"),
    ("parse_tres_text.py", ".tres resource files"),
    ("parse_gd_text.py",   ".gd scripts"),
]


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    utils_dir = script_dir / "utils"

    if not utils_dir.exists():
        print(f"[ERROR] utils directory not found: {utils_dir}")
        return 1

    failed: list[str] = []

    for idx, (script_name, description) in enumerate(PARSERS, start=1):
        script_path = utils_dir / script_name
        if not script_path.exists():
            print(f"[ERROR] Parser not found: {script_path}")
            failed.append(script_name)
            continue

        print(f"=== [{idx}/{len(PARSERS)}] {script_name}  ({description}) ===")
        result = subprocess.run([sys.executable, str(script_path)])
        if result.returncode != 0:
            print(f"[ERROR] {script_name} exited with code {result.returncode}")
            failed.append(script_name)
        print()

    print("=" * 60)
    if failed:
        print(f"Done with {len(failed)} failure(s): {', '.join(failed)}")
        return 1
    print(f"Done: all {len(PARSERS)} parsers succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
