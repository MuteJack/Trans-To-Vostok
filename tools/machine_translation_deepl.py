"""
Run the full DeepL translation pipeline for a target locale.

Sequentially calls the 3 utils scripts:
    1. tools/utils/export_unique_text.py <target_locale>
    2. tools/utils/translate_with_deepl.py <DEEPL_LANG> --source <target_locale>
    3. tools/utils/import_translations.py <target_locale>

Each step short-circuits on failure (stops the pipeline). Resume is built
into individual steps:
    - export overwrites unique.tsv
    - translate skips already-translated texts (text-keyed) and retries errors
    - import skips already-translated rows in xlsx

Usage:
    python tools/machine_translation_deepl.py <target_locale> [--deepl-lang <code>] [--limit N] [--dry-run]

Examples:
    python tools/machine_translation_deepl.py French
    python tools/machine_translation_deepl.py French --deepl-lang FR --limit 10
    python tools/machine_translation_deepl.py Japanese --dry-run

DeepL language codes: see https://developers.deepl.com/docs/getting-started/supported-languages
"""
import argparse
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


# locale folder name -> DeepL language code (kept in sync with import_translations.py).
# DeepL target language list: https://developers.deepl.com/docs/getting-started/supported-languages
# For variants (EN-GB/US, PT-BR/PT, ES/ES-419, ZH-HANS/HANT), both the
# camelCase name (e.g., BrazilianPortuguese, EnglishGB) and the
# underscore-suffixed alias (e.g., Portuguese_BR, English_GB) map to the
# same code so folder naming conventions can vary across contributors.
# Languages marked "(next-gen)" require DeepL's next-gen model — may fall
# back or error on the classic model.
DEFAULT_DEEPL_LANG = {
    # --- Western Europe (Latin) ---
    "Danish": "DA",
    "Dutch": "NL",
    "EnglishGB": "EN-GB",
    "English_GB": "EN-GB",
    "EnglishUS": "EN-US",
    "English_US": "EN-US",
    "Finnish": "FI",
    "French": "FR",
    "German": "DE",
    "Italian": "IT",
    "Norwegian": "NB",                    # Bokmål
    "Spanish": "ES",                      # Castilian (default)
    "Spanish_ES": "ES",
    "SpanishLatAm": "ES-419",
    "Spanish_419": "ES-419",
    "Swedish": "SV",
    "Portuguese": "PT-PT",
    "Portuguese_PT": "PT-PT",
    "BrazilianPortuguese": "PT-BR",
    "Portuguese_BR": "PT-BR",
    # --- Central / Eastern Europe (Latin) ---
    "Czech": "CS",
    "Estonian": "ET",
    "Hungarian": "HU",
    "Latvian": "LV",
    "Lithuanian": "LT",
    "Polish": "PL",
    "Romanian": "RO",
    "Slovak": "SK",
    "Slovenian": "SL",
    # --- Other Latin ---
    "Indonesian": "ID",
    "Turkish": "TR",
    "Vietnamese": "VI",                   # (next-gen)
    # --- Cyrillic / Greek ---
    "Bulgarian": "BG",
    "Greek": "EL",
    "Russian": "RU",
    "Ukrainian": "UK",
    # --- Asian / Other scripts ---
    "Arabic": "AR",
    "ChineseSimplified": "ZH-HANS",
    "Chinese_HANS": "ZH-HANS",
    "ChineseTraditional": "ZH-HANT",
    "Chinese_HANT": "ZH-HANT",
    "Hebrew": "HE",                       # (next-gen)
    "Japanese": "JA",
    "Korean": "KO",
    "Thai": "TH",                         # (next-gen)
}


def run_step(label: str, cmd: list[str], cwd: Path) -> bool:
    """Run a subprocess step. Returns True on success."""
    print("=" * 60)
    print(f"=== {label} ===")
    print("=" * 60)
    print(f"$ {' '.join(cmd)}")
    print()
    result = subprocess.run(cmd, cwd=cwd)
    print()
    if result.returncode != 0:
        print(f"[ERROR] {label} failed (exit code {result.returncode})", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the full DeepL translation pipeline for a target locale."
    )
    parser.add_argument("target_locale", help="Target locale folder name (e.g., French, Japanese)")
    parser.add_argument(
        "--deepl-lang", default=None,
        help="DeepL language code (default: auto-mapped from target_locale)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit DeepL translation to first N unique texts (testing)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run export + show plan; skip DeepL API call and import"
    )
    args = parser.parse_args()

    target_locale = args.target_locale
    deepl_lang = args.deepl_lang or DEFAULT_DEEPL_LANG.get(target_locale)
    if not deepl_lang:
        print(
            f"[ERROR] Cannot determine DeepL language code for '{target_locale}'.\n"
            f"  Specify it explicitly with --deepl-lang.",
            file=sys.stderr,
        )
        return 1

    script_dir = Path(__file__).resolve().parent  # mods/Trans To Vostok/tools

    print(f"Target locale  : {target_locale}")
    print(f"DeepL language : {deepl_lang}")
    if args.limit:
        print(f"Limit          : first {args.limit} unique texts")
    if args.dry_run:
        print(f"Mode           : DRY RUN (skip DeepL + import)")
    print()

    # Step 1: export unique text
    if not run_step(
        "[1/3] Export unique source texts",
        [sys.executable, "utils/export_unique_text.py", target_locale],
        cwd=script_dir,
    ):
        return 1

    # Step 2: DeepL translate
    translate_cmd = [
        sys.executable, "utils/translate_with_deepl.py", deepl_lang,
        "--source", target_locale,
    ]
    if args.limit:
        translate_cmd += ["--limit", str(args.limit)]
    if args.dry_run:
        translate_cmd.append("--dry-run")

    if not run_step("[2/3] DeepL translate", translate_cmd, cwd=script_dir):
        return 1

    # Step 3: import
    if args.dry_run:
        print("=" * 60)
        print("[3/3] Import — SKIPPED (dry-run)")
        print("=" * 60)
        print()
    else:
        if not run_step(
            "[3/3] Import translations into xlsx",
            [sys.executable, "utils/import_translations.py", target_locale,
             "--deepl-lang", deepl_lang],
            cwd=script_dir,
        ):
            return 1

    print("=" * 60)
    print(f"Pipeline complete: {target_locale}")
    if not args.dry_run:
        print(f"Next: review the xlsx, then run `python tools/build_mod_package.py` to build the mod zip.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
