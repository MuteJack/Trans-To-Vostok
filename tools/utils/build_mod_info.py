"""Build <pkg_root>/info.json — project-wide metadata consumed by F9 UI's Info tab.

info.json is FULLY GENERATED from upstream sources. Hand-edits are overwritten.
All fields below auto-fill:
  - mod_version          : from mod.txt              (`version="..."`)
  - target_game_version  : from mod.txt              (`target_game_version="..."`)
                           — single source of truth shared with ModLoader.
  - build_date           : today's date (UTC)
  - lead_developer / code_contributors / acknowledgments
                         : from AUTHORS.md (sections under `## ...`)

Per-locale data (translation_updated, translators, texture_reworkers, ...)
lives in `Trans To Vostok/<locale>/credits.json` and is consumed directly
by the F9 UI from there. info.json no longer carries a `locales` field.

Output:
  <pkg_root>/info.json (UTF-8, indent=2)

Usage:
  python tools/utils/build_mod_info.py
"""
import json
import re
import sys
from datetime import datetime, timezone
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
INFO_JSON = MOD_ROOT / "info.json"


def _parse_mod_txt_field(mod_txt: Path, field: str) -> str:
    """Read a `key="value"` line from mod.txt's [mod] section. Returns
    'unknown' if the file or the field is missing."""
    if not mod_txt.exists():
        return "unknown"
    try:
        text = mod_txt.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    pattern = re.compile(rf'\s*{re.escape(field)}\s*=\s*"?([^"\n]+?)"?\s*$')
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            return m.group(1).strip()
    return "unknown"


def parse_mod_version(mod_txt: Path) -> str:
    return _parse_mod_txt_field(mod_txt, "version")


def parse_target_game_version(mod_txt: Path) -> str:
    return _parse_mod_txt_field(mod_txt, "target_game_version")


def parse_authors_by_section(authors_md: Path) -> dict:
    """AUTHORS.md → { 'lead_developer': [...], 'code_contributors': [...],
    'acknowledgments': [...] }. Reads `- **Name**` patterns under each `##`.
    Skips the auto-generated Translators section (handled separately)."""
    out = {"lead_developer": [], "code_contributors": [], "acknowledgments": []}
    if not authors_md.exists():
        return out
    try:
        text = authors_md.read_text(encoding="utf-8")
    except OSError:
        return out

    section_map = {
        "Author / Lead Developer": "lead_developer",
        "Code Contributors": "code_contributors",
        "Acknowledgments": "acknowledgments",
    }
    current_key = None
    for line in text.splitlines():
        h = re.match(r'##\s+(.+?)\s*$', line)
        if h:
            current_key = section_map.get(h.group(1).strip())
            continue
        if current_key is None:
            continue
        n = re.match(r'-\s*\*\*([^*]+)\*\*', line)
        if not n:
            continue
        name = n.group(1).strip()
        if not name or name.lower() in {"none", "unknown", "tbd"}:
            continue
        if name not in out[current_key]:
            out[current_key].append(name)
    return out


def build_info(repo_root: Path) -> dict:
    mod_txt = repo_root / "mod.txt"
    target_game_version = parse_target_game_version(mod_txt)
    if target_game_version == "unknown":
        print(f"[WARN] target_game_version not set in mod.txt. "
              "Add `target_game_version=\"0.1.1.3\"` to mod.txt's [mod] section.",
              file=sys.stderr)

    sections = parse_authors_by_section(repo_root / "AUTHORS.md")
    return {
        "mod_version": parse_mod_version(mod_txt),
        "build_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "target_game_version": target_game_version,
        "lead_developer": sections["lead_developer"],
        "code_contributors": sections["code_contributors"],
        "acknowledgments": sections["acknowledgments"],
    }


def main() -> int:
    info = build_info(REPO)
    try:
        INFO_JSON.parent.mkdir(parents=True, exist_ok=True)
        INFO_JSON.write_text(
            json.dumps(info, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        print(f"[ERROR] Failed to write {INFO_JSON}: {e}", file=sys.stderr)
        return 1
    print(f"[OK] Wrote {INFO_JSON.relative_to(REPO)}")
    print(f"  mod_version={info['mod_version']}, build_date={info['build_date']}")
    print(f"  target_game_version={info['target_game_version']}")
    print(f"  lead_developer={len(info['lead_developer'])}, "
          f"code_contributors={len(info['code_contributors'])}, "
          f"acknowledgments={len(info['acknowledgments'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
