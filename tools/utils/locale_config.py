"""Helpers for reading the locale registry + active locale list.

Two files in play:
  - `tools/languages.json` (registry) — maps locale folder name to
    DeepL / Crowdin codes. Lists every language we might ever support;
    adding new entries here doesn't activate them.
  - `Trans To Vostok/locale.json` (active list) — locales actually shipped
    in the mod, with UI strings (display, message, etc.). Each entry's
    `dir` references a key in the registry.

Tools that need a locale's external code should call the helpers below
rather than hardcoding mappings.
"""
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
LANGUAGES_JSON = _REPO / "tools" / "languages.json"
LOCALE_JSON = _REPO / "Trans To Vostok" / "locale.json"


def _load_registry() -> dict:
    with open(LANGUAGES_JSON, encoding="utf-8") as f:
        return json.load(f)


def load_languages() -> dict[str, dict]:
    """Read the master registry. Returns {dir_name: {"deepl_id": ..., "crowdin_id": ...}}."""
    return _load_registry()["languages"]


def default_source_locale() -> str:
    """Linguistic source language declared in languages.json.

    Tools that translate FROM source TO target use this to refuse pushing
    the source as a target (e.g. you can't translate English to English in
    a project where English is the source).
    """
    return _load_registry()["default_source"]


def load_locales() -> list[dict]:
    """Read the active locale list (raw entries from locale.json)."""
    with open(LOCALE_JSON, encoding="utf-8") as f:
        return json.load(f)["locales"]


def _active_dirs(enabled_only: bool = True) -> list[str]:
    return [
        loc["dir"] for loc in load_locales()
        if not enabled_only or loc.get("enabled", True)
    ]


def load_crowdin_locale_map(enabled_only: bool = True) -> dict[str, str]:
    """Active locales × registry → {dir: crowdin_id}.

    Excludes the registered source language (push/pull doesn't apply to source).
    """
    registry = load_languages()
    source = default_source_locale()
    out: dict[str, str] = {}
    for d in _active_dirs(enabled_only):
        if d == source:
            continue
        entry = registry.get(d)
        if entry and entry.get("crowdin_id"):
            out[d] = entry["crowdin_id"]
    return out


def load_deepl_locale_map(enabled_only: bool = True) -> dict[str, str]:
    """Active locales × registry → {dir: deepl_id}.

    Excludes the registered source language and any entry with null deepl_id.
    """
    registry = load_languages()
    source = default_source_locale()
    out: dict[str, str] = {}
    for d in _active_dirs(enabled_only):
        if d == source:
            continue
        entry = registry.get(d)
        if entry and entry.get("deepl_id"):
            out[d] = entry["deepl_id"]
    return out


def dir_to_crowdin_id(dir_name: str) -> str | None:
    """Single lookup. Doesn't filter by active list (registry is enough)."""
    return load_languages().get(dir_name, {}).get("crowdin_id")


def dir_to_deepl_id(dir_name: str) -> str | None:
    """Single lookup. Doesn't filter by active list (registry is enough)."""
    return load_languages().get(dir_name, {}).get("deepl_id")
