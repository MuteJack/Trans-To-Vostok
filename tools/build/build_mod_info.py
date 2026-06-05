"""Phase 3 step — build <pkg_root>/info.json (project-wide metadata).

info.json feeds the F9 UI's Info tab. It is FULLY GENERATED — hand-edits
are overwritten on every build.

Fields auto-filled from upstream sources:
  - mod_version          : mod.txt              (`version="..."`)
  - target_game_version  : mod.txt              (`target_game_version="..."`)
                           — single source of truth shared with ModLoader.
  - build_date           : today's date (UTC)
  - lead_developer / code_contributors / acknowledgments
                         : AUTHORS.md (sections under `## ...`)

Per-locale data (translation_updated, translators, texture_reworkers, ...)
lives in `Trans To Vostok/<locale>/credits.json` and is consumed by the
F9 UI from there. info.json no longer carries a `locales` field.

This step is global (no locale argument).

Output:
  Trans To Vostok/info.json (UTF-8, indent=2)

Usage:
  python tools/build/build_mod_info.py
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
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
DRY_RUN_ROOT = REPO / ".tmp" / "temp_build" / "Trans To Vostok"
INFO_JSON = MOD_ROOT / "info.json"
DRY_RUN_INFO_JSON = DRY_RUN_ROOT / "info.json"
MOD_TXT = REPO / "mod.txt"
AUTHORS_MD = REPO / "AUTHORS.md"


def _say(msg: str = "") -> None:
    print(msg, flush=True)


def _parse_mod_txt_field(mod_txt: Path, field: str) -> str:
    """Read a `key="value"` line from mod.txt. Returns 'unknown' if missing."""
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


def build_info() -> dict:
    target_game_version = parse_target_game_version(MOD_TXT)
    if target_game_version == "unknown":
        _say('[WARN] target_game_version not set in mod.txt. '
             'Add `target_game_version="0.1.1.3"` to mod.txt\'s [mod] section.')

    sections = parse_authors_by_section(AUTHORS_MD)
    return {
        "mod_version": parse_mod_version(MOD_TXT),
        "build_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "target_game_version": target_game_version,
        "lead_developer": sections["lead_developer"],
        "code_contributors": sections["code_contributors"],
        "acknowledgments": sections["acknowledgments"],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Output to .tmp/temp_build/Trans To Vostok/info.json instead of deploy path")
    parser.add_argument("--logpath", default=None,
                        help="Append stdout/stderr to this log file "
                             "(used by orchestrator)")
    args = parser.parse_args(argv[1:])
    setup_logpath(args.logpath)

    out_path = DRY_RUN_INFO_JSON if args.dry_run else INFO_JSON

    _say("=== build_mod_info (global) ===")
    info = build_info()
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(info, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        _say(f"[ERROR] Failed to write {out_path}: {e}")
        return 1

    _say(f"  -> {out_path.relative_to(REPO)}")
    _say(f"  mod_version={info['mod_version']}, build_date={info['build_date']}")
    _say(f"  target_game_version={info['target_game_version']}")
    _say(f"  lead_developer={len(info['lead_developer'])}, "
         f"code_contributors={len(info['code_contributors'])}, "
         f"acknowledgments={len(info['acknowledgments'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
