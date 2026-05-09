"""Power-user wrapper: push xlsx translations -> Crowdin (Python-only, no CLI).

Combines four steps:
  1. utils/build_translation_tsv.py --output-root .tmp/...   xlsx -> ephemeral TSV
  2. crowdin/build_translations.py --tsv-root .tmp/...       ephemeral TSV -> Crowdin_Mirror
  3. Diff vs HEAD                                            (smart push: only changed rows)
  4. Crowdin SDK upload (minimal TSV per file)               Crowdin_Mirror -> Crowdin server

The working tree's Translations/<locale>/<cat>/*.tsv is NOT modified by this
command — canonical TSV in working tree always reflects the last commit (HEAD),
giving a stable diff baseline shared by all contributors.

Smart push (default):
  Diff is computed against the last GIT-COMMITTED canonical TSV
  (Translations/<locale>/<cat>/*.tsv at HEAD). Only rows whose translation
  changed since last commit are uploaded — rows you didn't touch stay
  untouched on Crowdin, so other contributors' edits aren't overwritten.

  Self-correcting: after a successful push, commit the working tree's
  Translations/<locale>/ to refresh the baseline for future pushes.

  --force-all: bypass diff and push everything (use rarely; risk of overwrite).

Required setup (one-time):
  - Python deps: pip install -r tools/requirements.txt   (includes crowdin-api-client)
  - Crowdin token: copy secrets.example.json to secrets.json (repo root)
                   and fill in `crowdin_personal_token`.

No Crowdin CLI / Java install required.

Usage:
    python tools/push_to_crowdin.py Korean
    python tools/push_to_crowdin.py French --skip-tsv
    python tools/push_to_crowdin.py Korean --auto-approve
    python tools/push_to_crowdin.py Korean --force-all
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
        help="Skip xlsx -> canonical TSV step (assume Translations/<locale>/<cat>/*.tsv is current)",
    )
    parser.add_argument(
        "--skip-mirror",
        action="store_true",
        help="Skip canonical TSV -> Crowdin_Mirror step",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Mark imported translations as approved (use only for self-reviewed work)",
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Push ALL non-empty rows (bypass HEAD diff). Risk: may overwrite "
             "another contributor's recent edits to rows you didn't intend to change.",
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

    # Ephemeral canonical TSV location — keeps working tree clean.
    ephemeral_tsv_root = repo_root / ".tmp" / "canonical_for_crowdin"

    # 1. xlsx -> ephemeral canonical TSV (NOT working tree)
    if not args.skip_tsv:
        if not run(
            [sys.executable, "utils/build_translation_tsv.py", args.locale,
             "--output-root", str(ephemeral_tsv_root)],
            cwd=tools_dir,
        ):
            print("\n[ERROR] xlsx -> TSV step failed", file=sys.stderr)
            return 1

    # 2. ephemeral canonical TSV -> Crowdin_Mirror
    if not args.skip_mirror:
        if not run(
            [sys.executable, "crowdin/build_translations.py", args.locale,
             "--tsv-root", str(ephemeral_tsv_root)],
            cwd=tools_dir,
        ):
            print("\n[ERROR] TSV -> Crowdin_Mirror step failed", file=sys.stderr)
            return 1

    locale_dir = repo_root / "Crowdin_Mirror" / "translations" / args.locale
    if not locale_dir.exists():
        print(f"\n[ERROR] Crowdin_Mirror dir missing: {locale_dir}", file=sys.stderr)
        print("        Run without --skip-mirror to regenerate.", file=sys.stderr)
        return 1

    # 3. Compute diff vs HEAD's canonical TSV
    try:
        from crowdin.api_client import upload_translations_diff, upload_translations_for_locale
        from crowdin.push_diff import diff_against_head, total_rows
    except ImportError as e:
        print(f"\n[ERROR] Could not import Crowdin SDK / diff helper: {e}", file=sys.stderr)
        print("        Run: pip install -r tools/requirements.txt", file=sys.stderr)
        return 1

    if args.force_all:
        print(f"\n>>> --force-all: uploading every non-empty row (bypassing HEAD diff)")
        try:
            stats = upload_translations_for_locale(
                locale_dir=locale_dir, language_id=crowdin_id, auto_approve=args.auto_approve)
        except RuntimeError as e:
            print(f"\n[ERROR] {e}", file=sys.stderr)
            return 1

        print()
        print(f"=== Upload summary ({args.locale} -> {crowdin_id}) ===")
        print(f"  files uploaded      : {stats['uploaded']}")
        print(f"  skipped (no source) : {stats['skipped_no_source']}")
        print(f"  errors              : {len(stats['errors'])}")
        if stats["errors"]:
            for path, msg in stats["errors"][:10]:
                print(f"    {path}: {msg}")
            return 1
    else:
        print(f"\n>>> Computing diff against HEAD")
        canonical_locale_dir = repo_root / "Translations" / args.locale
        try:
            to_push = diff_against_head(
                repo_root=repo_root,
                locale=args.locale,
                mirror_locale_dir=locale_dir,
                canonical_locale_dir=canonical_locale_dir,
            )
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] git invocation failed: {e}", file=sys.stderr)
            return 1

        n_to_push = total_rows(to_push)
        n_files = len(to_push)
        print(f"  Rows to push: {n_to_push} (across {n_files} files)")

        if n_to_push == 0:
            print(f"\n[OK] Nothing to push - working tree matches HEAD's canonical TSV.")
            return 0

        # 4. Upload diff via SDK
        print(f"\n>>> Crowdin SDK upload (diff): {args.locale} -> {crowdin_id}")
        try:
            stats = upload_translations_diff(
                diff_rows=to_push, language_id=crowdin_id, auto_approve=args.auto_approve)
        except RuntimeError as e:
            print(f"\n[ERROR] {e}", file=sys.stderr)
            return 1

        print()
        print(f"=== Upload summary ({args.locale} -> {crowdin_id}) ===")
        print(f"  rows uploaded       : {stats['uploaded_rows']}")
        print(f"  files updated       : {stats['uploaded_files']}")
        print(f"  skipped (no source) : {stats['skipped_no_source']}")
        print(f"  errors              : {len(stats['errors'])}")
        if stats["errors"]:
            for path, msg in stats["errors"][:10]:
                print(f"    {path}: {msg}")
            return 1

        print(f"\n  Note: working tree Translations/{args.locale}/ untouched.")
        print(f"        To share via PR, run:")
        print(f"          python tools/utils/build_translation_tsv.py {args.locale}")
        print(f"          git add Translations/{args.locale}/ && git commit -m \"<msg>\"")

    print(f"\n[OK] {args.locale} translations pushed to Crowdin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
