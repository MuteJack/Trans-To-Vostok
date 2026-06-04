"""Phase 3 step — build <locale>/texture_meta.json from canonical Texture TSVs.

Emits a flat JSON map: rel_path -> method ("replace" | "blend"),
consumed at runtime by texture_loader.gd to decide how to apply each
mod-side texture.

  - replace : substitute the original texture wholesale
  - blend   : composite mod overlay PNG on top of the original via
              Image.blend_rect at runtime (preserves PBR maps, ships
              only the translated text portion)
  - ignore  : asset exists in PCK but is not a translation target.
              Kept in TSV for completeness validation; not emitted
              to texture_meta.json (mod ships no PNG for these).
  - pending : explicitly deferred — rework would be difficult or
              low-value, so on hold. Like 'ignore', kept for
              completeness validation but not emitted to runtime.

Rows with empty method are treated as untriaged (not yet classified)
and skipped. Rows with empty File Directory + File Name are skipped
(no asset path to key on).

Input convention (Phase 3):
  <locale>   single locale
  all        every locale with enabled=true (English/Template excluded)
  Template   rejected — Template is never built.

Usage:
  python tools/build/build_texture_meta.py Korean
  python tools/build/build_texture_meta.py all
"""
import argparse
import csv
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
REPO = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
from utils.locale_config import load_locales  # noqa: E402

TRANSLATIONS_ROOT = REPO / "Translations"
PKG_ROOT = REPO / "Trans To Vostok"
DRY_RUN_ROOT = REPO / ".tmp" / "temp_build" / "Trans To Vostok"
CATEGORY = "Texture"
OUTPUT_NAME = "texture_meta.json"
TEMPLATE_LOCALE = "Template"
SOURCE_LOCALE = "English"

RUNTIME_METHODS = {"replace", "blend"}
NON_RUNTIME_METHODS = {"ignore", "pending"}
VALID_METHODS = RUNTIME_METHODS | NON_RUNTIME_METHODS


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _normalize_path(file_directory: str, file_name: str) -> str:
    """Join 'File Directory' + 'File Name' into a runtime rel path.

    File Directory uses Windows-style backslashes and may have a leading
    slash. Runtime expects forward slashes and no leading slash.
    """
    fd = (file_directory or "").strip().replace("\\", "/").strip("/")
    fn = (file_name or "").strip()
    if not fn:
        return ""
    return f"{fd}/{fn}" if fd else fn


def build_for_locale(locale: str, dry_run: bool = False) -> int:
    src_dir = TRANSLATIONS_ROOT / locale / "tsv" / CATEGORY
    out_root = DRY_RUN_ROOT if dry_run else PKG_ROOT
    out_path = out_root / locale / OUTPUT_NAME

    if not src_dir.exists():
        _say(f"  [SKIP] TSV dir not found: {src_dir.relative_to(REPO)}")
        return 0

    meta: dict[str, str] = {}
    duplicates: list[tuple[str, str, str]] = []
    invalid: list[tuple[Path, int, str]] = []
    non_runtime_counts: dict[str, int] = {m: 0 for m in NON_RUNTIME_METHODS}
    untriaged = 0

    for tsv in sorted(src_dir.glob("*.tsv")):
        with open(tsv, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row_num, row in enumerate(reader, start=2):
                method = (row.get("method") or "").strip().lower()
                if not method:
                    untriaged += 1
                    continue
                if method not in VALID_METHODS:
                    invalid.append((tsv, row_num, method))
                    continue
                if method in NON_RUNTIME_METHODS:
                    non_runtime_counts[method] += 1
                    continue

                rel = _normalize_path(
                    row.get("File Directory", ""),
                    row.get("File Name", ""),
                )
                if not rel:
                    continue

                if rel in meta and meta[rel] != method:
                    duplicates.append((rel, meta[rel], method))
                meta[rel] = method

    if invalid:
        _say(f"  [WARN] {len(invalid)} rows with invalid method value:")
        for tsv, row_num, method in invalid[:5]:
            _say(f"    {tsv.name}:{row_num}  method={method!r}")
        if len(invalid) > 5:
            _say(f"    ... and {len(invalid) - 5} more")

    if duplicates:
        _say(f"  [WARN] {len(duplicates)} path collisions (same file with different method):")
        for rel, old, new in duplicates[:5]:
            _say(f"    {rel}: {old!r} -> {new!r}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    counts = {m: sum(1 for v in meta.values() if v == m) for m in RUNTIME_METHODS}
    counts_str = ", ".join(f"{m}={n}" for m, n in counts.items())
    extras = [f"{m}={n}" for m, n in non_runtime_counts.items() if n]
    if untriaged:
        extras.append(f"untriaged={untriaged}")
    if extras:
        counts_str += ", " + ", ".join(extras) + " (not emitted)"
    _say(f"  {len(meta)} entries ({counts_str})")
    _say(f"  -> {out_path.relative_to(REPO)}")
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
    parser.add_argument("--dry-run", action="store_true",
                        help="Output to .tmp/temp_build/Trans To Vostok/<locale>/ instead of deploy path")
    args = parser.parse_args(argv[1:])

    if args.locale == TEMPLATE_LOCALE:
        _say(f"[ERROR] {TEMPLATE_LOCALE} is not a valid argument for this build step.")
        _say("        Template is never built - only validated.")
        return 1

    if args.locale == "all":
        locales = _discover_enabled_locales()
        if not locales:
            _say("[ERROR] no enabled locales found in src/locale.json")
            return 1
    else:
        if not (TRANSLATIONS_ROOT / args.locale).exists():
            _say(f"[ERROR] locale directory not found: Translations/{args.locale}")
            return 1
        locales = [args.locale]

    _say(f"=== build_texture_meta ({len(locales)} locale(s)) ===")
    _say(f"  Locales: {', '.join(locales)}")
    _say()

    overall = 0
    for loc in locales:
        _say(f"--- {loc} ---")
        rc = build_for_locale(loc, dry_run=args.dry_run)
        if rc != 0:
            overall = rc
        _say()

    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv))
