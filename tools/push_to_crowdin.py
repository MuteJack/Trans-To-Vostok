"""Power-user wrapper: push xlsx translations → Crowdin.

Combines three steps:
  1. utils/build_translation_tsv.py <locale>   xlsx → canonical TSV
  2. crowdin/build_translations.py <locale>    canonical TSV → Crowdin_Mirror
  3. crowdin upload translations -l <code>     Crowdin_Mirror → Crowdin

Use this when you edit xlsx locally (Method B — power user) and want to
publish your translations to Crowdin in a single command.

Required setup (one-time):
  - Python deps:           pip install -r tools/requirements.txt
  - Crowdin CLI installed: https://crowdin.github.io/crowdin-cli/installation
  - API token env var:     setx CROWDIN_PERSONAL_TOKEN "<your-token>"

Usage:
    python tools/push_to_crowdin.py Korean
    python tools/push_to_crowdin.py French --skip-tsv
    python tools/push_to_crowdin.py Korean --auto-approve
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.locale_config import load_crowdin_locale_map


def run(cmd: list, cwd: Path) -> bool:
    print(f"\n>>> {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def main() -> int:
    locale_map = load_crowdin_locale_map()

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale",
        help=f"Locale folder name. Supported: {', '.join(locale_map)}",
    )
    parser.add_argument(
        "--skip-tsv",
        action="store_true",
        help="Skip xlsx → canonical TSV step (assume Translations/<locale>/<cat>/*.tsv is current)",
    )
    parser.add_argument(
        "--skip-mirror",
        action="store_true",
        help="Skip canonical TSV → Crowdin_Mirror step",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Mark imported translations as approved (use only for self-reviewed work)",
    )
    args = parser.parse_args()

    if args.locale not in locale_map:
        print(f"[ERROR] Unknown locale: {args.locale}", file=sys.stderr)
        print(f"        Supported: {', '.join(locale_map)}", file=sys.stderr)
        print(f"        (active locale in Trans To Vostok/locale.json AND crowdin_id present in tools/languages.json)",
              file=sys.stderr)
        return 1

    crowdin_id = locale_map[args.locale]

    tools_dir = Path(__file__).resolve().parent
    repo_root = tools_dir.parent

    # 1. xlsx → canonical TSV
    if not args.skip_tsv:
        if not run(
            [sys.executable, "utils/build_translation_tsv.py", args.locale],
            cwd=tools_dir,
        ):
            print("\n[ERROR] xlsx → TSV step failed", file=sys.stderr)
            return 1

    # 2. canonical TSV → Crowdin_Mirror
    if not args.skip_mirror:
        if not run(
            [sys.executable, "crowdin/build_translations.py", args.locale],
            cwd=tools_dir,
        ):
            print("\n[ERROR] TSV → Crowdin_Mirror step failed", file=sys.stderr)
            return 1

    # 3. crowdin upload translations -l <code>
    upload_cmd = ["crowdin", "upload", "translations", "-l", crowdin_id]
    if args.auto_approve:
        upload_cmd.append("--auto-approve-imported")
    if not run(upload_cmd, cwd=repo_root):
        print("\n[ERROR] Crowdin upload failed", file=sys.stderr)
        print("        Check Crowdin CLI install + CROWDIN_PERSONAL_TOKEN env var", file=sys.stderr)
        return 1

    print(f"\n[OK] {args.locale} translations pushed to Crowdin (-l {crowdin_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
