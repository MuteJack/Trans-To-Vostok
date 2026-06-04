"""Phase 3 helper — promote runtime_tsv from .tmp/temp_build/ to deploy.

Copies the dry-run-built runtime TSV bundle to the deploy location so
the local game can pick up the new runtime data immediately. ZIP
packaging and other artifacts stay in the staging tree.

Source: .tmp/temp_build/Trans To Vostok/<locale>/runtime_tsv/
Target: Trans To Vostok/<locale>/runtime_tsv/

Each file is copied atomically (write to .tmp + rename) so partial
copies do not corrupt the deploy path. Stale TSVs at the deploy target
(files that no longer exist in the staging tree) are removed.

Input convention (Phase 3):
  <locale>   single locale
  all        every locale with enabled=true (English/Template excluded)
  Template   rejected — Template is never deployed.

Usage:
  python tools/build/copy_runtime_tsv_from_temp.py Korean
  python tools/build/copy_runtime_tsv_from_temp.py all
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

sys.path.insert(0, str(TOOLS_DIR))
from utils.locale_config import load_locales  # noqa: E402

MOD_NAME = "Trans To Vostok"
MOD_ROOT = REPO / MOD_NAME
DRY_RUN_ROOT = REPO / ".tmp" / "temp_build" / MOD_NAME
RUNTIME_TSV_DIR = "runtime_tsv"
TEMPLATE_LOCALE = "Template"
SOURCE_LOCALE = "English"


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _atomic_copy(src: Path, dst: Path) -> None:
    """Copy src -> dst via dst.tmp + rename."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    try:
        shutil.copy2(src, tmp)
        tmp.replace(dst)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def promote_for_locale(locale: str) -> int:
    src_dir = DRY_RUN_ROOT / locale / RUNTIME_TSV_DIR
    dst_dir = MOD_ROOT / locale / RUNTIME_TSV_DIR

    if not src_dir.exists():
        _say(f"  [ERROR] staging runtime_tsv not found: {src_dir.relative_to(REPO)}")
        _say("          Run build_runtime_tsv.py --dry-run first.")
        return 1

    src_files = sorted(p for p in src_dir.iterdir() if p.is_file())
    if not src_files:
        _say(f"  [ERROR] no files under {src_dir.relative_to(REPO)}")
        return 1

    copied = 0
    for src in src_files:
        dst = dst_dir / src.name
        _atomic_copy(src, dst)
        copied += 1
        _say(f"  -> {dst.relative_to(REPO)}")

    expected = {p.name for p in src_files}
    removed = 0
    if dst_dir.exists():
        for stale in dst_dir.iterdir():
            if stale.is_file() and stale.name not in expected:
                try:
                    stale.unlink()
                    removed += 1
                    _say(f"  x removed stale: {stale.relative_to(REPO)}")
                except OSError as e:
                    _say(f"  [WARN] Failed to remove stale: {stale.name} ({e})")

    _say(f"  {copied} copied, {removed} stale removed")
    return 0


def _discover_enabled_locales() -> list[str]:
    out: list[str] = []
    for loc in load_locales():
        name = loc.get("dir")
        if loc.get("enabled") and name and name not in (SOURCE_LOCALE, TEMPLATE_LOCALE):
            out.append(name)
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("locale", help="Locale name or 'all'")
    args = parser.parse_args(argv[1:])

    if args.locale == TEMPLATE_LOCALE:
        _say(f"[ERROR] {TEMPLATE_LOCALE} is not a valid argument for this step.")
        _say("        Template is never deployed.")
        return 1

    if args.locale == "all":
        locales = _discover_enabled_locales()
        if not locales:
            _say("[ERROR] no enabled locales found in src/locale.json")
            return 1
    else:
        locales = [args.locale]

    _say(f"=== copy_runtime_tsv_from_temp ({len(locales)} locale(s)) ===")
    _say(f"  Locales: {', '.join(locales)}")
    _say()

    overall = 0
    for loc in locales:
        _say(f"--- {loc} ---")
        rc = promote_for_locale(loc)
        if rc != 0:
            overall = rc
        _say()

    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv))
