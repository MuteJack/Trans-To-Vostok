"""Phase 3 step — package the built mod into a single ZIP.

Bundles already-built artifacts into `mods/Trans To Vostok.zip`. This
step does NOT invoke any other build step — it assumes everything is
already present:

  required (build aborts if missing):
    mod.txt                                                   (repo root)
    src/translator_ui.gd                                      (hand-edited)
    src/translator.gd                                         (hand-edited)
    src/texture_loader.gd                                     (hand-edited)
    src/mod_addon.gd                                          (hand-edited)
    src/locale.json                                           (hand-edited)
    Trans To Vostok/info.json                                 (build_mod_info)
    Trans To Vostok/<locale>/runtime_tsv/*.tsv                (build_runtime_tsv)

  optional per locale (skipped silently if absent):
    Trans To Vostok/<locale>/credits.json                     (get_member_list + get_texture_credits)
    Trans To Vostok/<locale>/Texture_Attribution.md           (build_attributions)
    Trans To Vostok/<locale>/Translation_Credit.md            (build_translation_credit)
    Trans To Vostok/<locale>/texture_meta.json                (build_texture_meta)
    Translations/<locale>/textures/**                         (hand-authored PNGs)

Input convention (Phase 3):
  <locale>   single locale -> zip contains just that locale
  all        every locale with enabled=true (English/Template excluded)
  Template   rejected — Template is never shipped.

Output: mods/Trans To Vostok.zip (atomic write via .tmp -> rename)

Usage:
  python tools/build/pack_mod_zip.py Korean
  python tools/build/pack_mod_zip.py all
"""
import argparse
import sys
import zipfile
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
TRANSLATIONS_ROOT = REPO / "Translations"
OUT_ZIP = REPO.parent / f"{MOD_NAME}.zip"
DRY_RUN_ROOT = REPO / ".tmp" / "temp_build" / MOD_NAME
DRY_RUN_OUT_ZIP = REPO / ".tmp" / "temp_build" / f"{MOD_NAME}.zip"
TEMPLATE_LOCALE = "Template"
SOURCE_LOCALE = "English"

SRC_FILES = [
    "translator_ui.gd",
    "translator.gd",
    "texture_loader.gd",
    "mod_addon.gd",
    "locale.json",
]
GENERATED_FILES = ["info.json"]

RUNTIME_TSV_DIR = "runtime_tsv"
RUNTIME_TSV_FILES = [
    "metadata.tsv",
    "translation_static.tsv",
    "translation_literal_scoped.tsv",
    "translation_pattern_scoped.tsv",
    "translation_literal.tsv",
    "translation_pattern.tsv",
    "translation_substr.tsv",
]

TEXTURE_DIR = "textures"
TEXTURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

OPTIONAL_LOCALE_FILES = [
    "credits.json",
    "Texture_Attribution.md",
    "Translation_Credit.md",
    "texture_meta.json",
]


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _discover_enabled_locales() -> list[str]:
    out: list[str] = []
    for loc in load_locales():
        name = loc.get("dir")
        if loc.get("enabled") and name and name not in (SOURCE_LOCALE, TEMPLATE_LOCALE):
            out.append(name)
    return out


def package_mod(locales: list[str], out_path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Build the ZIP. Returns (total file count, texture file count).

    Sourcing:
        Hand-edited (mod.txt, src/, Translations/<locale>/textures/) — always deploy.
        Build artifacts (info.json, runtime_tsv/, credits.json, *_Credit.md,
            Texture_Attribution.md, texture_meta.json) — `.tmp/temp_build/Trans To Vostok/`
            when dry_run else `Trans To Vostok/`.
    """
    src_root = REPO / "src"
    pkg_root = DRY_RUN_ROOT if dry_run else MOD_ROOT
    count = 0
    texture_count = 0

    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. mod.txt -> zip root  (always deploy)
            mod_txt = REPO / "mod.txt"
            if not mod_txt.exists():
                raise FileNotFoundError(f"mod.txt not found: {mod_txt}")
            zf.write(mod_txt, "mod.txt")
            count += 1

            # 2a. hand-edited src/ -> Trans To Vostok/  (always deploy)
            for fname in SRC_FILES:
                src = src_root / fname
                if not src.exists():
                    raise FileNotFoundError(f"Source file not found: {src}")
                zf.write(src, f"{MOD_NAME}/{fname}")
                count += 1

            # 2b. generated files (info.json) -> Trans To Vostok/
            for fname in GENERATED_FILES:
                src = pkg_root / fname
                if not src.exists():
                    raise FileNotFoundError(f"Generated file not found: {src}")
                zf.write(src, f"{MOD_NAME}/{fname}")
                count += 1

            # 3. per-locale content
            for locale in locales:
                locale_dir = pkg_root / locale
                runtime_dir = locale_dir / RUNTIME_TSV_DIR

                # required: runtime TSVs
                for fname in RUNTIME_TSV_FILES:
                    src = runtime_dir / fname
                    if not src.exists():
                        raise FileNotFoundError(
                            f"Runtime TSV not found ({locale}): {src}"
                        )
                    zf.write(src, f"{MOD_NAME}/{locale}/{RUNTIME_TSV_DIR}/{fname}")
                    count += 1

                # optional: textures from Translations/<locale>/textures/
                src_textures_dir = TRANSLATIONS_ROOT / locale / TEXTURE_DIR
                if src_textures_dir.exists() and src_textures_dir.is_dir():
                    for tex_file in sorted(src_textures_dir.rglob("*")):
                        if not tex_file.is_file():
                            continue
                        if tex_file.suffix.lower() not in TEXTURE_EXTENSIONS:
                            continue
                        rel = tex_file.relative_to(src_textures_dir).as_posix()
                        zf.write(tex_file, f"{MOD_NAME}/{locale}/{TEXTURE_DIR}/{rel}")
                        count += 1
                        texture_count += 1

                # optional per-locale build artifacts
                for fname in OPTIONAL_LOCALE_FILES:
                    src = locale_dir / fname
                    if src.exists() and src.is_file():
                        zf.write(src, f"{MOD_NAME}/{locale}/{fname}")
                        count += 1

        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    return count, texture_count


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("locale", help="Locale name or 'all'")
    parser.add_argument("--dry-run", action="store_true",
                        help="Output to .tmp/temp_build/Trans To Vostok.zip instead of mods/Trans To Vostok.zip")
    args = parser.parse_args(argv[1:])

    if args.locale == TEMPLATE_LOCALE:
        _say(f"[ERROR] {TEMPLATE_LOCALE} is not a valid argument for this build step.")
        _say("        Template is never shipped.")
        return 1

    if args.locale == "all":
        locales = _discover_enabled_locales()
        if not locales:
            _say("[ERROR] no enabled locales found in src/locale.json")
            return 1
    else:
        if not (MOD_ROOT / args.locale).exists():
            _say(f"[ERROR] locale directory not found: Trans To Vostok/{args.locale}")
            return 1
        locales = [args.locale]

    out_zip = DRY_RUN_OUT_ZIP if args.dry_run else OUT_ZIP
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    _say(f"=== pack_mod_zip ({len(locales)} locale(s)) ===")
    _say(f"  Locales: {', '.join(locales)}")
    _say(f"  Output:  {out_zip}")
    _say()

    try:
        file_count, texture_count = package_mod(locales, out_zip, dry_run=args.dry_run)
    except FileNotFoundError as e:
        _say(f"[ERROR] {e}")
        return 1

    size_kb = out_zip.stat().st_size / 1024.0
    _say("=" * 60)
    _say(f"Packaged: {out_zip.name}")
    _say(f"  Files:    {file_count}  (including {texture_count} textures)")
    _say(f"  Size:     {size_kb:.1f} KB")
    _say(f"  Locales:  {', '.join(locales)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
