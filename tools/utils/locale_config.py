"""Helpers for reading the canonical locale registry.

The registry lives at `Trans To Vostok/locale.json` and is the single
source-of-truth for:
  - locale folder name (`dir`) — used by every tool that touches a locale
  - display name + UI strings — used by the mod runtime
  - `crowdin_id` (optional) — Crowdin language id for tools that sync
    with Crowdin (push_to_crowdin, pull_from_crowdin, etc.)

Tools that need locale info should import from here rather than
hardcoding mappings.
"""
import json
from pathlib import Path

# tools/utils/<this file> -> mod root
_REPO = Path(__file__).resolve().parent.parent.parent
LOCALE_JSON = _REPO / "Trans To Vostok" / "locale.json"


def load_locales() -> list[dict]:
    """Returns the raw list of locale entries from locale.json."""
    with open(LOCALE_JSON, encoding="utf-8") as f:
        return json.load(f)["locales"]


def load_crowdin_locale_map() -> dict[str, str]:
    """Returns {dir_name: crowdin_id} for locales that have a crowdin_id.

    Locales without crowdin_id (e.g. English source) are excluded.
    """
    return {
        loc["dir"]: loc["crowdin_id"]
        for loc in load_locales()
        if loc.get("crowdin_id")
    }


def dir_to_crowdin_id(dir_name: str) -> str | None:
    """Look up a single locale's Crowdin id by folder name. None if not found."""
    return load_crowdin_locale_map().get(dir_name)
