"""
Auto-generate Translation_Credit.md for a locale from credits.json.

Source:
    Trans To Vostok/<locale>/credits.json
        - translation_updated   -> "Translation last updated" line
        - Translator.Leader     -> Lead Translator(s)
        - Translator.Translator -> Translator(s)        (Crowdin Proofreader role)
        - Translator.Contributor -> Translation Contributors
        - Texture_reworker      -> Texture Reworkers

credits.json itself is updated by:
    - tools/crowdin/get_member_list.py    (Translator.* + translation_updated)
    - tools/utils/get_texture_credits.py  (Texture_reworker)

Output:
    <pkg_root>/<locale>/Translation_Credit.md

Usage:
    python tools/utils/build_translation_credit.py                  # default (Korean)
    python tools/utils/build_translation_credit.py --locale Korean
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
MOD_ROOT = REPO / "Trans To Vostok"
CREDITS_FILE = "credits.json"


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
        print(f"  [WARN] Cannot parse {path}: {e}", file=sys.stderr)
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
        "`tools/utils/build_translation_credit.py`. Do not edit manually — "
        "credits.json is updated by `tools/crowdin/get_member_list.py` "
        "(translator roles from Crowdin) and "
        "`tools/utils/get_texture_credits.py` (texture rework from Texture.xlsx)._"
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Translation_Credit.md from credits.json"
    )
    parser.add_argument("--locale", default="Korean",
                        help="Locale folder name (default: Korean)")
    parser.add_argument("--output", default=None,
                        help="Output path (default: <pkg_root>/<locale>/Translation_Credit.md)")
    args = parser.parse_args()

    credits = load_credits(args.locale)
    if credits is None:
        path = MOD_ROOT / args.locale / CREDITS_FILE
        print(f"[ERROR] credits.json not found or unreadable: {path}", file=sys.stderr)
        print(f"        Run tools/crowdin/get_member_list.py first.", file=sys.stderr)
        return 1

    translator = credits.get("Translator") or {}
    leader = _dedup_keep_order(translator.get("Leader") or [])
    translator_tier = _dedup_keep_order(translator.get("Translator") or [])
    contributor = _dedup_keep_order(translator.get("Contributor") or [])
    texture_reworker = _dedup_keep_order(credits.get("Texture_reworker") or [])
    translation_updated = credits.get("translation_updated")

    print(f"Locale: {args.locale}")
    print(f"  translation_updated      : {translation_updated or '(none)'}")
    print(f"  Lead translator(s)       : {len(leader)}")
    print(f"  Translator(s)            : {len(translator_tier)}")
    print(f"  Translation contributors : {len(contributor)}")
    print(f"  Texture reworkers        : {len(texture_reworker)}")
    print()

    output_path = (
        Path(args.output).resolve()
        if args.output
        else MOD_ROOT / args.locale / "Translation_Credit.md"
    )
    md = build_md(
        args.locale, translation_updated,
        leader, translator_tier, contributor, texture_reworker,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")

    rel = output_path
    try:
        rel = output_path.relative_to(REPO)
    except ValueError:
        pass
    print(f"Output: {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
