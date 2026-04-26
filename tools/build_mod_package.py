"""
Package the Trans To Vostok mod into a .zip file.

Usage:
    python build_mod_package.py [locale...]

Examples:
    python build_mod_package.py Korean
    python build_mod_package.py Korean Japanese  (when multi-locale supported)
    python build_mod_package.py                   (default: Korean)

Behavior:
1. Call build_runtime_tsv for the specified locale to generate TSVs (including validation)
2. Compress the mod file structure into ZIP, producing ../Trans To Vostok.zip
    - mod.txt                                               (mod metadata)
    - Trans To Vostok/translator_ui.gd                      (UI + engine management)
    - Trans To Vostok/translator.gd                         (text translation engine)
    - Trans To Vostok/texture_loader.gd                     (texture replacement engine)
    - Trans To Vostok/locale.json                           (locale configuration)
    - Trans To Vostok/<locale>/translation_*.tsv            (runtime TSVs)
    - Trans To Vostok/<locale>/metadata.tsv
    - Trans To Vostok/<locale>/textures/**                   (translated images, included if present)

Output: mods/Trans To Vostok.zip
"""
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Windows console Korean output support
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


MOD_NAME = "Trans To Vostok"
MOD_FILES = ["translator_ui.gd", "translator.gd", "texture_loader.gd", "locale.json"]
LOCALE_FILES = [
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


def build_locale(tools_dir: Path, locale: str, soft: bool = False, ignore: bool = False) -> bool:
    """Call build_runtime_tsv.py to generate TSVs. Returns whether it succeeded."""
    print(f"=== Building locale: {locale} ===")
    cmd = [sys.executable, "build_runtime_tsv.py", locale]
    if ignore:
        cmd.append("--ignore")
    elif soft:
        cmd.append("--soft")
    result = subprocess.run(cmd, cwd=tools_dir)
    if result.returncode != 0:
        print(f"[ERROR] {locale} build failed")
        return False
    print()
    return True


def build_attributions_for_locale(tools_dir: Path, locale: str) -> bool:
    """Call build_attributions.py. Skipped if Images.xlsx is absent.
    Output goes to the default path of build_attributions.py (<pkg_root>/<locale>/Attribution.md)."""
    print(f"=== Building attribution: {locale} ===")
    cmd = [sys.executable, "build_attributions.py", "--locale", locale]
    result = subprocess.run(cmd, cwd=tools_dir)
    if result.returncode != 0:
        print(f"[ERROR] {locale} attribution build failed")
        return False
    print()
    return True


def package_mod(mod_root: Path, locales: list[str], out_path: Path) -> tuple[int, int]:
    """
    Package the mod as .vmz (ZIP).
    Returns: (total file count, texture file count)
    """
    pkg_root = mod_root / MOD_NAME
    count = 0
    texture_count = 0

    # atomic write
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. mod.txt → ZIP root (outer/repo root)
            mod_txt = mod_root / "mod.txt"
            if not mod_txt.exists():
                raise FileNotFoundError(f"mod.txt not found: {mod_txt}")
            zf.write(mod_txt, "mod.txt")
            count += 1

            # 2. mod files (pkg_root) → Trans To Vostok/
            for fname in MOD_FILES:
                src = pkg_root / fname
                if not src.exists():
                    raise FileNotFoundError(f"Mod file not found: {src}")
                zf.write(src, f"{MOD_NAME}/{fname}")
                count += 1

            # 3. locale files → Trans To Vostok/<locale>/
            for locale in locales:
                locale_dir = pkg_root / locale
                for fname in LOCALE_FILES:
                    src = locale_dir / fname
                    if not src.exists():
                        raise FileNotFoundError(f"Locale file not found: {src}")
                    zf.write(src, f"{MOD_NAME}/{locale}/{fname}")
                    count += 1

                # 4. texture folder → Trans To Vostok/<locale>/textures/**
                # skipped if folder is absent (per-locale optional)
                textures_dir = locale_dir / TEXTURE_DIR
                if textures_dir.exists() and textures_dir.is_dir():
                    for tex_file in sorted(textures_dir.rglob("*")):
                        if not tex_file.is_file():
                            continue
                        if tex_file.suffix.lower() not in TEXTURE_EXTENSIONS:
                            continue
                        rel = tex_file.relative_to(locale_dir).as_posix()
                        zf.write(tex_file, f"{MOD_NAME}/{locale}/{rel}")
                        count += 1
                        texture_count += 1

                # 5. Attribution.md → Trans To Vostok/<locale>/Attribution.md
                # generated by build_attributions.py. Locales without Images.xlsx have no file → skip
                attribution_path = locale_dir / "Attribution.md"
                if attribution_path.exists() and attribution_path.is_file():
                    zf.write(attribution_path, f"{MOD_NAME}/{locale}/Attribution.md")
                    count += 1

        # overwrite original on success
        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    return count, texture_count


def load_locale_config(mod_root: Path) -> list[dict]:
    """Return list of locales with enabled=true from locale.json."""
    locale_json = mod_root / MOD_NAME / "locale.json"
    if not locale_json.exists():
        return []
    try:
        data = json.loads(locale_json.read_text(encoding="utf-8"))
        return [loc for loc in data.get("locales", []) if loc.get("enabled", False)]
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] Failed to read locale.json: {e}", file=sys.stderr)
        return []


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent                # mods/Trans To Vostok

    # parse --soft / --hard / --ignore
    cli_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cli_flags = {a for a in sys.argv[1:] if a.startswith("--")}
    soft = "--soft" in cli_flags
    ignore = "--ignore" in cli_flags

    # if command-line args provided, override; otherwise read from locale.json
    if cli_args:
        locales = cli_args
        print(f"Command-line locales: {locales}")
    else:
        locale_config = load_locale_config(mod_root)
        if locale_config:
            locales = [lc["dir"] for lc in locale_config]
            display = [f"{lc.get('display', lc['dir'])} ({lc['dir']})" for lc in locale_config]
            print(f"Loaded from locale.json: {', '.join(display)}")
        else:
            locales = ["Korean"]
            print("locale.json not found, default: Korean")
    mods_parent = mod_root.parent                # mods/
    out_path = mods_parent / f"{MOD_NAME}.zip"

    # 1. build each locale (includes validate, skip locales without folder)
    pkg_root = mod_root / MOD_NAME
    build_locales = []
    for locale in locales:
        locale_dir = pkg_root / locale
        xlsx_path = locale_dir / "Translation.xlsx"
        if not locale_dir.exists() or not xlsx_path.exists():
            print(f"[SKIP] {locale} - translation folder/xlsx not found (default language)")
            continue
        if not build_locale(script_dir, locale, soft=soft, ignore=ignore):
            return 1
        build_locales.append(locale)
    locales = build_locales

    # 2. build attributions (only for locales with Images.xlsx)
    for locale in locales:
        if not build_attributions_for_locale(script_dir, locale):
            return 1

    # 3. packaging
    print(f"=== Packaging ===")
    print(f"Target locales: {', '.join(locales)}")
    print(f"Output file: {out_path}")
    try:
        file_count, texture_count = package_mod(mod_root, locales, out_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    size_kb = out_path.stat().st_size / 1024.0
    print()
    print("=" * 60)
    print(f"Build complete: {out_path.name}")
    print(f"  Files:    {file_count}  (including {texture_count} textures)")
    print(f"  Size:     {size_kb:.1f} KB")
    print(f"  Locales:  {', '.join(locales)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
