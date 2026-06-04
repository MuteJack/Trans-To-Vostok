"""Phase 2 orchestrator — full validation for a locale's source, runtime, and quality.

Runs the locale-side validation checks in three groups, mirroring the
WorkFlow document:

  2.1 source checks
       check_required_cols          Critical
       check_duplicates             Critical
       check_whitespace_text        Critical
       check_diff_with_Template     Critical (mixed; orchestrator treats
                                              any tool failure as Critical)
       check_deprecated             Warn
       check_missing                Info
  2.2 runtime
       build_runtime_tsv  --dry-run Critical (writes to .tmp/temp_build/Trans To Vostok/)
       check_runtime_tsv_conflict   Critical (reads .tmp/temp_build/Trans To Vostok/)
       --dry-run for both so the locale's deployed runtime_tsv/ is never
       touched.
  2.3 translation quality
       check_whitespace_translated  Warn
       check_conflict               Info

Input:
  - <locale>   single locale (e.g. Korean)
  - all        every locale with enabled=true in src/locale.json
               (English and Template are skipped)
  - 'Template' is rejected — this tool compares against Template; use
    tools/validate_Template.py for Template's own validation.

Exit code (aggregated across all locales and all steps):
  0  no triggered severity OR only Info-level findings
  2  Warn-level findings, no Critical
  1  one or more Critical-level findings

Usage:
  python tools/validate_translation_new.py Korean
  python tools/validate_translation_new.py all
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATION_DIR = SCRIPT_DIR / "validation"
BUILD_DIR = SCRIPT_DIR / "build"
REPO = SCRIPT_DIR.parent
LOCALE_JSON = REPO / "src" / "locale.json"
TEMPLATE_LOCALE = "Template"

# (label, script_path, extra_args, workflow_severity)
CHECKS: list[tuple[str, Path, list[str], str]] = [
    # 2.1 source checks
    ("check_required_cols",         VALIDATION_DIR / "check_required_cols.py",         [],                          "Critical"),
    ("check_duplicates",            VALIDATION_DIR / "check_duplicates.py",            [],                          "Critical"),
    ("check_whitespace_text",       VALIDATION_DIR / "check_whitespace_text.py",       [],                          "Critical"),
    ("check_diff_with_Template",    VALIDATION_DIR / "check_diff_with_Template.py",    [],                          "Critical"),
    ("check_deprecated",            VALIDATION_DIR / "check_deprecated.py",            [],                          "Warn"),
    ("check_missing",               VALIDATION_DIR / "check_missing.py",               [],                          "Info"),
    # 2.2 runtime
    ("build_runtime_tsv",           BUILD_DIR / "build_runtime_tsv.py",                ["--dry-run", "--ignore"],   "Critical"),
    ("check_runtime_tsv_conflict",  BUILD_DIR / "check_runtime_tsv_conflict.py",       ["--dry-run"],               "Critical"),
    # 2.3 quality
    ("check_whitespace_translated", VALIDATION_DIR / "check_whitespace_translated.py", [],                          "Warn"),
    ("check_conflict",              VALIDATION_DIR / "check_conflict.py",              [],                          "Info"),
]

SEVERITY_RANK = {"OK": 0, "Info": 1, "Warn": 2, "Critical": 3}
EXIT_FOR_SEVERITY = {"OK": 0, "Info": 0, "Warn": 2, "Critical": 1}


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _discover_enabled_locales() -> list[str]:
    """Locales with enabled=true in locale.json, excluding English + Template."""
    if not LOCALE_JSON.exists():
        return []
    try:
        data = json.loads(LOCALE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out: list[str] = []
    for loc in data.get("locales", []):
        name = loc.get("dir")
        if loc.get("enabled") and name and name not in ("English", TEMPLATE_LOCALE):
            out.append(name)
    return out


def _run_locale(locale: str) -> tuple[str, list[tuple[str, str, int]]]:
    """Run all checks for one locale. Return (triggered_severity, results)."""
    _say(f"=== Locale: {locale} ({len(CHECKS)} steps) ===")
    _say()

    results: list[tuple[str, str, int]] = []
    triggered = "OK"
    for idx, (label, script, extra_args, severity) in enumerate(CHECKS, start=1):
        if not script.exists():
            _say(f"[ERROR] step script missing: {script.relative_to(REPO)}")
            results.append((label, severity, -1))
            triggered = "Critical"
            continue

        _say(f"--- [{idx}/{len(CHECKS)}] {label} ({severity}) ---")
        cmd = [sys.executable, str(script), locale] + extra_args
        completed = subprocess.run(cmd)
        _say()
        results.append((label, severity, completed.returncode))

        if completed.returncode != 0 and SEVERITY_RANK[severity] > SEVERITY_RANK[triggered]:
            triggered = severity

    return triggered, results


def _print_locale_summary(locale: str, results: list[tuple[str, str, int]],
                           triggered: str) -> None:
    _say(f"--- Summary: {locale} ---")
    for label, severity, rc in results:
        status = "OK" if rc == 0 else severity
        _say(f"  {label:30s}  [{severity:8s}]  {status:8s}  (exit={rc})")
    _say(f"  -> {locale}: {triggered}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale",
        help="Locale name (e.g. Korean) or 'all'",
    )
    args = parser.parse_args(argv[1:])

    if args.locale == TEMPLATE_LOCALE:
        _say("[ERROR] Template is not a valid argument for this orchestrator.")
        _say("        Phase 2 validates locales against Template.")
        _say("        Use tools/validate_Template.py for Template's own validation.")
        return 1

    if args.locale == "all":
        locales = _discover_enabled_locales()
        if not locales:
            _say("[ERROR] no enabled locales found in src/locale.json")
            return 1
    else:
        translations_dir = REPO / "Translations" / args.locale
        if not translations_dir.exists():
            _say(f"[ERROR] locale directory not found: {translations_dir}")
            return 1
        locales = [args.locale]

    _say(f"=== Phase 2: Locale Validation ({len(locales)} locale(s)) ===")
    _say(f"  Locales: {', '.join(locales)}")
    _say()

    per_locale_results: list[tuple[str, str, list[tuple[str, str, int]]]] = []
    overall = "OK"
    for locale in locales:
        triggered, results = _run_locale(locale)
        _print_locale_summary(locale, results, triggered)
        _say()
        per_locale_results.append((locale, triggered, results))
        if SEVERITY_RANK[triggered] > SEVERITY_RANK[overall]:
            overall = triggered

    _say("=== Grand Total ===")
    for locale, triggered, _ in per_locale_results:
        _say(f"  {locale:25s}  {triggered}")
    _say()
    _say(f"Overall: {overall}")
    return EXIT_FOR_SEVERITY[overall]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
