"""Build <pkg_root>/info.json — project-wide metadata consumed by F9 UI's Info tab.

info.json is a hybrid file (read-modify-write):
  - target_game_version  : HAND-EDITED in info.json itself, preserved by this script
  - mod_version          : auto from mod.txt        (`version="..."`)
  - build_date           : auto, today's date (UTC)
  - lead_developer / code_contributors / acknowledgments
                         : auto from AUTHORS.md (sections under `## ...`)

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


def parse_mod_version(mod_txt: Path) -> str:
    if not mod_txt.exists():
        return "unknown"
    try:
        text = mod_txt.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    for line in text.splitlines():
        m = re.match(r'\s*version\s*=\s*"?([^"\n]+?)"?\s*$', line)
        if m:
            return m.group(1).strip()
    return "unknown"


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


def load_existing_info() -> dict:
    if not INFO_JSON.exists():
        return {}
    try:
        return json.loads(INFO_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[WARN] Cannot read existing {INFO_JSON.name}: {e}", file=sys.stderr)
        return {}


def build_info(repo_root: Path) -> dict:
    existing = load_existing_info()
    target_game_version = existing.get("target_game_version", "unknown")
    if target_game_version == "unknown":
        print(f"[WARN] target_game_version not set in {INFO_JSON.name}. "
              "Edit info.json by hand to set it (e.g. \"0.1.1.3\").", file=sys.stderr)

    sections = parse_authors_by_section(repo_root / "AUTHORS.md")
    return {
        "mod_version": parse_mod_version(repo_root / "mod.txt"),
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
