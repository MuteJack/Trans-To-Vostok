"""Phase 3 orchestrator — build the mod entirely in .tmp/temp_build/, then promote runtime_tsv.

Pipeline (all build steps run with --dry-run so deploy stays untouched
until the final promote step):

  1. clear_temp_build.py                        (wipe staging dir)
  2. per-locale, in order:
        build_runtime_tsv.py <locale> --dry-run --ignore
        check_runtime_tsv_conflict.py <locale> --dry-run
        get_texture_credits.py <locale> --dry-run
        build_attributions.py <locale> --dry-run
        build_translation_credit.py <locale> --dry-run
        build_texture_meta.py <locale> --dry-run
  3. global (once):
        build_authors.py --dry-run
        build_mod_info.py --dry-run
  4. pack_mod_zip.py <locale> --dry-run          (reads staging, writes
                                                  .tmp/temp_build/Trans To Vostok.zip)
  5. copy_runtime_tsv_from_temp.py <locale>      (promote runtime_tsv -> deploy)

Step 2 is invoked once with the orchestrator's locale arg (the sub-tools
handle the locale/'all' convention internally). Step 5 is the only step
that touches the deploy tree.

Input convention (Phase 3):
  <locale>   single locale
  all        every locale with enabled=true (English/Template excluded)
  Template   rejected — Template is never built.

Usage:
  python tools/build_mod_package.py Korean
  python tools/build_mod_package.py all
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


SCRIPT_DIR = Path(__file__).resolve().parent  # tools/
BUILD_DIR = SCRIPT_DIR / "build"
REPO = SCRIPT_DIR.parent
TRANSLATIONS_ROOT = REPO / "Translations"
TEMPLATE_LOCALE = "Template"

sys.path.insert(0, str(SCRIPT_DIR))
from helper.helper_log import setup_logpath, make_log_path  # noqa: E402

# (label, script_path, locale-aware?, extra_args)
PER_LOCALE_STEPS: list[tuple[str, Path, list[str]]] = [
    ("build_runtime_tsv",            BUILD_DIR / "build_runtime_tsv.py",            ["--dry-run", "--ignore"]),
    ("check_runtime_tsv_conflict",   BUILD_DIR / "check_runtime_tsv_conflict.py",   ["--dry-run"]),
    ("get_texture_credits",          BUILD_DIR / "get_texture_credits.py",          ["--dry-run"]),
    ("build_attributions",           BUILD_DIR / "build_attributions.py",           ["--dry-run"]),
    ("build_translation_credit",     BUILD_DIR / "build_translation_credit.py",     ["--dry-run"]),
    ("build_texture_meta",           BUILD_DIR / "build_texture_meta.py",           ["--dry-run"]),
]

GLOBAL_STEPS: list[tuple[str, Path, list[str]]] = [
    ("build_authors",   BUILD_DIR / "build_authors.py",   ["--dry-run"]),
    ("build_mod_info",  BUILD_DIR / "build_mod_info.py",  ["--dry-run"]),
]

PACK_STEP = ("pack_mod_zip", BUILD_DIR / "pack_mod_zip.py", ["--dry-run"])
PROMOTE_STEP = ("copy_runtime_tsv_from_temp", BUILD_DIR / "copy_runtime_tsv_from_temp.py", [])
CLEAR_STEP = ("clear_temp_build", BUILD_DIR / "clear_temp_build.py", [])


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _run(label: str, script: Path, args: list[str], log_path: Path | None = None) -> int:
    _say(f"--- {label} {' '.join(args)} ---")
    if not script.exists():
        _say(f"[ERROR] step script missing: {script.relative_to(REPO)}")
        return 1
    cmd = [sys.executable, str(script)] + args
    if log_path is not None:
        cmd += ["--logpath", str(log_path)]
    rc = subprocess.run(cmd).returncode
    _say()
    return rc


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("locale", help="Locale name or 'all'")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip the promote step (runtime_tsv stays in staging only). "
                             "Default promote is disabled.")
    parser.add_argument("--promote", action="store_true", default=None,
                        help="Force promote runtime_tsv to deploy. "
                             "Default: True unless --dry-run.")
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file. "
                             "If omitted, a fresh log is created at "
                             ".log/build_mod_package_<timestamp>.log")
    args = parser.parse_args(argv[1:])

    promote = args.promote if args.promote is not None else (not args.dry_run)

    log_path = Path(args.logpath) if args.logpath else make_log_path(REPO, "build_mod_package")
    setup_logpath(str(log_path))

    if args.locale == TEMPLATE_LOCALE:
        _say(f"[ERROR] {TEMPLATE_LOCALE} is not a valid argument for this orchestrator.")
        _say("        Template is never built.")
        return 1

    if args.locale != "all" and not (TRANSLATIONS_ROOT / args.locale).exists():
        _say(f"[ERROR] locale directory not found: Translations/{args.locale}")
        return 1

    _say(f"=== Phase 3: build_mod_package ({args.locale}) ===")
    _say(f"  log:     {log_path.relative_to(REPO)}")
    _say(f"  promote: {promote}{'  (--dry-run)' if args.dry_run else ''}")
    _say()

    # 1. clear staging
    label, script, extra = CLEAR_STEP
    rc = _run(label, script, extra, log_path=log_path)
    if rc != 0:
        _say("[ERROR] clear_temp_build failed; aborting.")
        return 1

    # 2. per-locale build (sub-tools handle 'all' internally)
    for label, script, extra in PER_LOCALE_STEPS:
        rc = _run(label, script, [args.locale] + extra, log_path=log_path)
        if rc != 0:
            _say(f"[ERROR] {label} failed; aborting.")
            return 1

    # 3. global metadata
    for label, script, extra in GLOBAL_STEPS:
        rc = _run(label, script, extra, log_path=log_path)
        if rc != 0:
            _say(f"[ERROR] {label} failed; aborting.")
            return 1

    # 4. pack ZIP from staging
    label, script, extra = PACK_STEP
    rc = _run(label, script, [args.locale] + extra, log_path=log_path)
    if rc != 0:
        _say(f"[ERROR] {label} failed; aborting.")
        return 1

    # 5. promote runtime_tsv -> deploy (skipped when promote=False)
    if promote:
        label, script, extra = PROMOTE_STEP
        rc = _run(label, script, [args.locale] + extra, log_path=log_path)
        if rc != 0:
            _say(f"[ERROR] {label} failed; aborting.")
            return 1

    _say("=" * 60)
    _say(f"Build complete: {args.locale}")
    _say(f"  ZIP:           .tmp/temp_build/Trans To Vostok.zip (staging)")
    if promote:
        _say(f"  runtime_tsv:   promoted to Trans To Vostok/<locale>/runtime_tsv/ (deploy)")
    else:
        _say(f"  runtime_tsv:   staging only (promote skipped — use --promote to deploy)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
