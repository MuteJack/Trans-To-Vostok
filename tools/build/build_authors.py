"""Phase 3 step — refresh the Translators section of AUTHORS.md.

Aggregates `Trans To Vostok/<locale>/credits.json` across every locale
that has one and rewrites the auto-generated block in AUTHORS.md.

credits.json schema:
    {
      "translation_updated": "<ISO timestamp>",
      "Translator": {
        "Leader":      [...],   # Crowdin: Owner / Manager / Language Coordinator
        "Translator":  [...],   # Crowdin: Proofreader
        "Contributor": [...]    # Crowdin: Member with translated > 0
      },
      "Texture_reworker": [...]  # Texture.xlsx Reworked by + Contributors
    }

credits.json is updated by:
  - tools/crowdin/get_member_list.py        (translator roles)
  - tools/build/get_texture_credits.py      (texture rework)

This step is global (no locale argument): it iterates every locale that
has credits.json and replaces the content between AUTHORS.md's markers:

    <!-- BEGIN AUTO-GENERATED: Translators -->
    ...replaced content...
    <!-- END AUTO-GENERATED: Translators -->

Manual sections (Author / Lead Developer, Code Contributors,
Acknowledgments, How to add yourself) are preserved verbatim.

Usage:
  python tools/build/build_authors.py
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helper.helper_log import setup_logpath  # noqa: E402

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
AUTHORS_MD = REPO / "AUTHORS.md"
DRY_RUN_AUTHORS_MD = REPO / ".tmp" / "temp_build" / "AUTHORS.md"
CREDITS_FILE = "credits.json"

BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED: Translators -->"
END_MARKER = "<!-- END AUTO-GENERATED: Translators -->"


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _load_credits(credits_path: Path) -> dict | None:
    try:
        return json.loads(credits_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _say(f"  [WARN] Cannot read {credits_path.relative_to(REPO)}: {e}")
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
        "`tools/build/build_authors.py`. credits.json itself is updated by "
        "`tools/crowdin/get_member_list.py` (translator roles from Crowdin) "
        "and `tools/build/get_texture_credits.py` (texture rework from Texture.xlsx)._"
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


def update_authors_md(in_path: Path, generated: str, out_path: Path | None = None) -> bool:
    """Replace content between BEGIN/END markers. Writes to out_path (default: in_path)."""
    if out_path is None:
        out_path = in_path
    if not in_path.exists():
        _say(f"[ERROR] AUTHORS.md not found: {in_path}")
        return False

    text = in_path.read_text(encoding="utf-8")
    if BEGIN_MARKER not in text or END_MARKER not in text:
        _say("[ERROR] AUTHORS.md is missing one or both markers:")
        _say(f"    {BEGIN_MARKER}")
        _say(f"    {END_MARKER}")
        _say("  Add these markers around the section to be auto-generated.")
        return False

    before, _, rest = text.partition(BEGIN_MARKER)
    _, _, after = rest.partition(END_MARKER)

    new_text = f"{before}{BEGIN_MARKER}\n\n{generated}\n{END_MARKER}{after}"

    if new_text == text and out_path == in_path:
        _say(f"  -> No changes (already up-to-date): {out_path.name}")
        return True

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    try:
        tmp.write_text(new_text, encoding="utf-8")
        tmp.replace(out_path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
    _say(f"  -> Updated: {out_path.relative_to(REPO)}")
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Output to .tmp/temp_build/AUTHORS.md instead of deploy path")
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file "
                             "(used by orchestrator)")
    args = parser.parse_args(argv[1:])
    setup_logpath(args.logpath)

    if not MOD_ROOT.exists():
        _say(f"[ERROR] Mod root not found: {MOD_ROOT}")
        return 1
    if not AUTHORS_MD.exists():
        _say(f"[ERROR] AUTHORS.md not found: {AUTHORS_MD}")
        return 1

    out_path = DRY_RUN_AUTHORS_MD if args.dry_run else AUTHORS_MD

    _say("=== build_authors (global) ===")
    locales = _discover_locales(MOD_ROOT)
    _say(f"  Locales with credits.json: {', '.join(locales) if locales else '(none)'}")
    _say(f"  Target: {out_path.relative_to(REPO)}")
    _say()

    auto_content = build_auto_section(MOD_ROOT)
    if not update_authors_md(AUTHORS_MD, auto_content, out_path):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
