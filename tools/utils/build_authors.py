"""
Auto-update the Translators section of AUTHORS.md from per-locale credits.json.

Reads `Trans To Vostok/<locale>/credits.json` for each locale (file is
populated by `tools/crowdin/get_member_list.py` for translator fields and
`tools/utils/get_texture_credits.py` for texture rework credits).

credits.json schema:
    {
      "translation_updated": "<ISO timestamp>",
      "Translator": {
        "Leader":      [...],   # Crowdin: Owner / Manager / Language Coordinator
        "Translator":  [...],   # Crowdin: Proofreader
        "Contributor": [...]    # Crowdin: Member with translated > 0
      },
      "Texture_reworker": [...]  # Texture.xlsx Reworked by + Contributors (off-Crowdin)
    }

Aggregates them into a single Translators section in AUTHORS.md, between
BEGIN/END markers. Manual sections (Author / Lead Developer, Code
Contributors, How to add yourself) are preserved.

Markers (must already exist in AUTHORS.md):
    <!-- BEGIN AUTO-GENERATED: Translators -->
    ...replaced content...
    <!-- END AUTO-GENERATED: Translators -->

Usage:
    python tools/utils/build_authors.py
"""
import json
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

MOD_ROOT = REPO / "Trans To Vostok"
CREDITS_FILE = "credits.json"

BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED: Translators -->"
END_MARKER = "<!-- END AUTO-GENERATED: Translators -->"


def _load_credits(credits_path: Path) -> dict | None:
    try:
        return json.loads(credits_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"  [WARN] Cannot read {credits_path}: {e}")
        return None


def _discover_locales(mod_root: Path) -> list[str]:
    """Locales are subdirectories of Trans To Vostok/ that contain credits.json."""
    out: list[str] = []
    if not mod_root.exists():
        return out
    for d in sorted(mod_root.iterdir()):
        if d.is_dir() and (d / CREDITS_FILE).exists():
            out.append(d.name)
    return out


def _dedup_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _render_subsection(label: str, names: list[str]) -> list[str]:
    if names:
        out = [f"**{label}:**"]
        for n in names:
            out.append(f"- {n}")
        out.append("")
    else:
        out = [f"**{label}:** _(none yet)_", ""]
    return out


def _render_locale(locale: str, credits: dict) -> list[str]:
    translator = credits.get("Translator") or {}
    leader = _dedup_keep_order(translator.get("Leader") or [])
    translator_tier = _dedup_keep_order(translator.get("Translator") or [])
    contributor = _dedup_keep_order(translator.get("Contributor") or [])
    texture = _dedup_keep_order(credits.get("Texture_reworker") or [])
    updated = credits.get("translation_updated")

    lines: list[str] = []
    lines.append(f"### {locale} (`Translations/{locale}/`)")
    lines.append("")
    if updated:
        lines.append(f"_Translation last updated: {updated}_")
        lines.append("")
    lines.extend(_render_subsection("Lead Translator(s)", leader))
    lines.extend(_render_subsection("Translator(s)", translator_tier))
    lines.extend(_render_subsection("Translation Contributors", contributor))
    lines.extend(_render_subsection("Texture Reworkers", texture))
    return lines


def build_auto_section(mod_root: Path) -> str:
    """Build the markdown content for the auto-generated Translators section."""
    locales = _discover_locales(mod_root)

    lines: list[str] = []
    lines.append("## Translators")
    lines.append("")
    lines.append(
        "_Auto-generated from each locale's `credits.json` by "
        "`tools/utils/build_authors.py`. credits.json itself is updated by "
        "`tools/crowdin/get_member_list.py` (translator roles from Crowdin) "
        "and `tools/utils/get_texture_credits.py` (texture rework from Texture.xlsx)._"
    )
    lines.append("")

    if not locales:
        lines.append("_(no locales with credits.json yet)_")
        return "\n".join(lines) + "\n"

    for locale in locales:
        credits = _load_credits(mod_root / locale / CREDITS_FILE)
        if credits is None:
            continue
        lines.extend(_render_locale(locale, credits))

    return "\n".join(lines) + "\n"


def update_authors_md(authors_path: Path, generated: str) -> bool:
    """Replace content between BEGIN/END markers. Returns True on success."""
    if not authors_path.exists():
        print(f"[ERROR] AUTHORS.md not found: {authors_path}")
        return False

    text = authors_path.read_text(encoding="utf-8")
    if BEGIN_MARKER not in text or END_MARKER not in text:
        print(f"[ERROR] AUTHORS.md is missing one or both markers:")
        print(f"    {BEGIN_MARKER}")
        print(f"    {END_MARKER}")
        print(f"  Add these markers around the section to be auto-generated.")
        return False

    before, _, rest = text.partition(BEGIN_MARKER)
    _, _, after = rest.partition(END_MARKER)

    new_text = f"{before}{BEGIN_MARKER}\n\n{generated}\n{END_MARKER}{after}"

    if new_text == text:
        print(f"  -> No changes (already up-to-date): {authors_path.name}")
        return True

    tmp = authors_path.with_suffix(authors_path.suffix + ".tmp")
    try:
        tmp.write_text(new_text, encoding="utf-8")
        tmp.replace(authors_path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
    print(f"  -> Updated: {authors_path.name}")
    return True


def main() -> int:
    authors_path = REPO / "AUTHORS.md"

    if not MOD_ROOT.exists():
        print(f"[ERROR] Mod root not found: {MOD_ROOT}")
        return 1
    if not authors_path.exists():
        print(f"[ERROR] AUTHORS.md not found: {authors_path}")
        return 1

    print(f"Mod root : {MOD_ROOT}")
    print(f"Target   : {authors_path}")
    print()

    locales = _discover_locales(MOD_ROOT)
    print(f"Locales with credits.json: {', '.join(locales) if locales else '(none)'}")
    print()

    auto_content = build_auto_section(MOD_ROOT)
    if not update_authors_md(authors_path, auto_content):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
