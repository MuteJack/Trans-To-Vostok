"""Phase 3 step — generate <locale>/Translation_Credit.md from credits.json.

Source (Trans To Vostok/<locale>/credits.json):
    translation_updated      -> "Translation last updated" line
    Translator.Leader        -> Lead Translator(s)
    Translator.Translator    -> Translator(s)             (Crowdin Proofreader)
    Translator.Contributor   -> Translation Contributors
    Texture_reworker         -> Texture Reworkers

credits.json is owned by:
    tools/crowdin/get_member_list.py        (Translator.*, translation_updated)
    tools/build/get_texture_credits.py      (Texture_reworker)

Output:
    Trans To Vostok/<locale>/Translation_Credit.md

Input convention (Phase 3):
  <locale>   single locale
  all        every locale with enabled=true (English/Template excluded)
  Template   rejected — Template is never built.

Usage:
  python tools/build/build_translation_credit.py Korean
  python tools/build/build_translation_credit.py all
"""
import argparse
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

sys.path.insert(0, str(TOOLS_DIR))
from helper.helper_locale_config import load_locales  # noqa: E402
from helper.helper_log import setup_logpath  # noqa: E402

MOD_ROOT = REPO / "Trans To Vostok"
DRY_RUN_ROOT = REPO / ".tmp" / "temp_build" / "Trans To Vostok"
CREDITS_FILE = "credits.json"
OUTPUT_NAME = "Translation_Credit.md"
TEMPLATE_LOCALE = "Template"
SOURCE_LOCALE = "English"


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _dedup_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items or []:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def load_credits(locale: str) -> dict | None:
    path = MOD_ROOT / locale / CREDITS_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        _say(f"  [WARN] Cannot parse {path.relative_to(REPO)}: {e}")
        return None


def build_md(
    locale: str,
    translation_updated: str | None,
    leader: list[str],
    translator_tier: list[str],
    contributor: list[str],
    texture_reworker: list[str],
) -> str:
    def section(title: str, names: list[str]) -> list[str]:
        out = [f"## {title}", ""]
        if names:
            for n in names:
                out.append(f"- {n}")
        else:
            out.append("_(none yet)_")
        out.append("")
        return out

    lines: list[str] = []
    lines.append(f"# {locale} Translation Credits")
    lines.append("")
    lines.append(
        f"People who contributed to translating Road to Vostok into {locale}. "
        f"This includes both text translation and texture / image rework."
    )
    lines.append("")
    if translation_updated:
        lines.append(f"_Translation last updated: {translation_updated}_")
        lines.append("")
    lines.extend(section("Lead Translator(s)", leader))
    lines.extend(section("Translator(s)", translator_tier))
    lines.extend(section("Translation Contributors", contributor))
    lines.extend(section("Texture Reworkers", texture_reworker))
    lines.append("---")
    lines.append("")
    lines.append(
        "_Auto-generated from `Trans To Vostok/<locale>/credits.json` by "
        "`tools/build/build_translation_credit.py`. Do not edit manually - "
        "credits.json is updated by `tools/crowdin/get_member_list.py` "
        "(translator roles from Crowdin) and "
        "`tools/build/get_texture_credits.py` (texture rework from Texture.xlsx)._"
    )
    return "\n".join(lines) + "\n"


def build_for_locale(locale: str, dry_run: bool = False) -> int:
    credits = load_credits(locale)
    if credits is None:
        path = MOD_ROOT / locale / CREDITS_FILE
        _say(f"  [ERROR] credits.json not found or unreadable: {path.relative_to(REPO)}")
        _say("          Run tools/crowdin/get_member_list.py first.")
        return 1

    translator = credits.get("Translator") or {}
    leader = _dedup_keep_order(translator.get("Leader") or [])
    translator_tier = _dedup_keep_order(translator.get("Translator") or [])
    contributor = _dedup_keep_order(translator.get("Contributor") or [])
    texture_reworker = _dedup_keep_order(credits.get("Texture_reworker") or [])
    translation_updated = credits.get("translation_updated")

    _say(f"  translation_updated      : {translation_updated or '(none)'}")
    _say(f"  Lead translator(s)       : {len(leader)}")
    _say(f"  Translator(s)            : {len(translator_tier)}")
    _say(f"  Translation contributors : {len(contributor)}")
    _say(f"  Texture reworkers        : {len(texture_reworker)}")

    out_root = DRY_RUN_ROOT if dry_run else MOD_ROOT
    out_path = out_root / locale / OUTPUT_NAME
    md = build_md(
        locale, translation_updated,
        leader, translator_tier, contributor, texture_reworker,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
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
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file "
                             "(used by orchestrator)")
    args = parser.parse_args(argv[1:])
    setup_logpath(args.logpath)

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
        if not (MOD_ROOT / args.locale).exists():
            _say(f"[ERROR] locale directory not found: Trans To Vostok/{args.locale}")
            return 1
        locales = [args.locale]

    _say(f"=== build_translation_credit ({len(locales)} locale(s)) ===")
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
