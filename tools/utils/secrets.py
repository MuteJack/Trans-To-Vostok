"""Load API secrets from secrets.json (gitignored, repo root).

Returns None for missing keys — callers decide whether to fall back
to env vars or error out.

Setup: copy secrets.example.json to secrets.json and fill in values.
"""
import json
import os
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
SECRETS_PATH = _REPO / "secrets.json"


def _load() -> dict:
    if not SECRETS_PATH.exists():
        return {}
    return json.loads(SECRETS_PATH.read_text(encoding="utf-8"))


def get_deepl_api_key() -> str | None:
    """DeepL API auth key. Falls back to DEEPL_AUTH_KEY env var."""
    return _load().get("deepl_api_key") or os.environ.get("DEEPL_AUTH_KEY") or None


def get_crowdin_personal_token() -> str | None:
    """Crowdin personal access token. Falls back to CROWDIN_PERSONAL_TOKEN env var."""
    return _load().get("crowdin_personal_token") or os.environ.get("CROWDIN_PERSONAL_TOKEN") or None
