"""Build canonical TSVs for a locale from its xlsx files.

Top-level convenience wrapper that mirrors tools/rebuild_xlsx.py for the
reverse direction of the editing pipeline:

    tools/rebuild_xlsx.py            TSV  -> xlsx
    tools/build_translation_tsv.py   xlsx -> TSV  (this file)

The underlying utility iterates every xlsx in Translations/<locale>/
(Translation.xlsx + Texture.xlsx + ...) and exports every sheet into
Translations/<locale>/tsv/<file>/<sheet>.tsv.

A duplicate of this entry point currently lives at
tools/utils/build_translation_tsv.py — that one carries the actual
implementation and is the script invoked here via subprocess. The two
will be reconciled in a follow-up cleanup.

Usage:
    python tools/build_translation_tsv.py              # all locales
    python tools/build_translation_tsv.py <locale>     # one locale only
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
IMPL = SCRIPT_DIR / "utils" / "build_translation_tsv.py"


def main(argv: list[str]) -> int:
    if not IMPL.exists():
        print(f"[ERROR] implementation missing: {IMPL.relative_to(SCRIPT_DIR.parent)}",
              file=sys.stderr)
        return 1
    return subprocess.run([sys.executable, str(IMPL)] + argv[1:]).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
