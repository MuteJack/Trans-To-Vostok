"""Fetch Crowdin contributors per locale and update Trans To Vostok/<locale>/credits.json.

Updates the translator-related fields (Leader / Translator / Contributor) and
`translation_updated`. Preserves any existing `Texture_reworker` entry — that
list is curated by a separate workflow (texture work happens off-Crowdin).

Role mapping (Crowdin -> our schema):
    owner / manager / language_coordinator -> Leader
    proofreader                            -> Translator
    translator (member) + translated > 0   -> Contributor

owner / manager are project-wide. They're added to a locale's Leader list
only if they have actual translation activity on that locale (translated > 0).

Credits file lives at:
    Trans To Vostok/<locale>/credits.json   (committed; ships in mod zip)

Usage:
    python tools/crowdin/get_member_list.py              # all active locales
    python tools/crowdin/get_member_list.py Korean       # one locale
"""
import argparse
import enum
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
REPO = TOOLS_DIR.parent

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass

sys.path.insert(0, str(TOOLS_DIR))
from crowdin.api_client import make_client
from utils.locale_config import load_crowdin_locale_map

from crowdin_api.api_resources.reports.enums import Format
from crowdin_api.sorting import Sorting, SortingOrder, SortingRule

MOD_ROOT = REPO / "Trans To Vostok"
CREDITS_FILE = "credits.json"

LEADER_ROLES = {"owner", "manager", "language_coordinator"}


class _SortField(enum.Enum):
    """Local helper enum -- SDK's SortingRule requires an enum.Enum value.

    list_language_translations only supports `createdAt` as a sort field
    (`updatedAt` returns 'orderByFieldInvalid'), but we still emit the
    `updatedAt` field on each row so downstream code can compute a
    max-of-both for the latest activity timestamp.
    """
    CREATED_AT = "createdAt"


def fetch_top_members(client, project_id: int, language_id: str,
                     poll_interval: float = 2.0,
                     poll_timeout: float = 120.0) -> dict[int, dict]:
    """Build {user_id: {"username", "fullName", "translated", "approved"}} for a language."""
    resp = client.reports.generate_top_members_report(
        projectId=project_id, languageId=language_id, format=Format.JSON
    )
    rid = resp["data"]["identifier"]
    deadline = time.time() + poll_timeout
    while True:
        s = client.reports.check_report_generation_status(projectId=project_id, reportId=rid)
        st = s["data"]["status"]
        if st == "finished":
            break
        if st in ("failed", "canceled"):
            raise RuntimeError(f"top_members_report({language_id}) {st}: {s['data']}")
        if time.time() > deadline:
            raise RuntimeError(f"top_members_report({language_id}) timed out")
        time.sleep(poll_interval)

    dl = client.reports.download_report(projectId=project_id, reportId=rid)
    with urllib.request.urlopen(dl["data"]["url"]) as r:
        report = json.loads(r.read().decode("utf-8"))

    out: dict[int, dict] = {}
    for entry in report.get("data", []):
        u = entry["user"]
        try:
            uid = int(u["id"])
        except (KeyError, ValueError, TypeError):
            continue
        out[uid] = {
            "username": u.get("username"),
            "fullName": u.get("fullName"),
            "translated": entry.get("translated", 0),
            "approved": entry.get("approved", 0),
        }
    return out


def classify(member: dict, lang_id: str, activity: dict | None) -> str | None:
    """Return 'Leader' / 'Translator' / 'Contributor' or None (skip)."""
    role = (member.get("role") or "").lower()
    translated = (activity or {}).get("translated", 0)

    # Project-wide roles: include only if active for this language.
    if role in ("owner", "manager"):
        return "Leader" if translated > 0 else None

    perms = member.get("permissions") or {}
    lang_role = perms.get(lang_id) if isinstance(perms, dict) else None
    if lang_role:
        lang_role = lang_role.lower()

    if lang_role in LEADER_ROLES:
        return "Leader"
    if lang_role == "proofreader":
        return "Translator"
    if lang_role in ("translator", "member"):
        return "Contributor" if translated > 0 else None
    return None


def display_name(user: dict) -> str:
    return (user.get("fullName") or user.get("username") or "").strip() or "(unknown)"


def _to_datetime(value) -> datetime | None:
    """Crowdin returns timestamps as either ISO strings or pre-parsed datetimes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def fetch_last_activity(client, project_id: int, language_id: str) -> datetime | None:
    """Return the most recent translation activity timestamp for this language.

    Walks all translations (auto-paginated) and takes max(createdAt, updatedAt)
    so both new translations AND edits to existing ones are captured.
    """
    sort = Sorting([SortingRule(_SortField.CREATED_AT, SortingOrder.DESC)])
    resp = client.string_translations.with_fetch_all().list_language_translations(
        projectId=project_id, languageId=language_id, orderBy=sort,
    )
    latest: datetime | None = None
    for entry in resp.get("data", []):
        d = entry["data"]
        for field in ("createdAt", "updatedAt"):
            ts = _to_datetime(d.get(field))
            if ts is None:
                continue
            if latest is None or ts > latest:
                latest = ts
    return latest


def update_credits_for_locale(client, project_id: int, locale: str, lang_id: str) -> dict:
    """Fetch + classify members, write credits.json. Returns the new credits dict."""
    members_resp = client.users.list_project_members(
        projectId=project_id, languageId=lang_id, limit=500
    )
    members = [m["data"] for m in members_resp.get("data", [])]

    top = fetch_top_members(client, project_id, lang_id)
    last_activity = fetch_last_activity(client, project_id, lang_id)

    buckets: dict[str, list[str]] = {"Leader": [], "Translator": [], "Contributor": []}
    seen: set[str] = set()
    for m in members:
        uid = m.get("id")
        cls = classify(m, lang_id, top.get(uid) if isinstance(uid, int) else None)
        if not cls:
            continue
        name = display_name(m)
        if name in seen:
            continue
        seen.add(name)
        buckets[cls].append(name)

    credits_path = MOD_ROOT / locale / CREDITS_FILE
    existing: dict = {}
    if credits_path.exists():
        try:
            existing = json.loads(credits_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  [WARN] {credits_path} is not valid JSON; recreating from scratch.")
            existing = {}

    if last_activity is not None:
        translation_updated = last_activity.astimezone().isoformat(timespec="seconds")
    else:
        # No translations yet for this language -- record sync time as fallback.
        translation_updated = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    # Overwrite only the fields this script owns; preserve any other field
    # (e.g. Texture_reworker, set by tools/utils/get_texture_credits.py).
    new_credits = dict(existing)
    new_credits["translation_updated"] = translation_updated
    new_credits["Translator"] = buckets
    new_credits.setdefault("Texture_reworker", [])

    credits_path.parent.mkdir(parents=True, exist_ok=True)
    credits_path.write_text(
        json.dumps(new_credits, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return new_credits


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale", nargs="?", default=None,
        help="Locale folder name (one of active). If omitted, processes all active locales.",
    )
    args = parser.parse_args(argv[1:])

    locale_map = load_crowdin_locale_map()
    if args.locale is not None:
        if args.locale not in locale_map:
            print(f"[ERROR] Unknown locale: {args.locale}", file=sys.stderr)
            print(f"        Known: {', '.join(locale_map)}", file=sys.stderr)
            return 1
        locales = {args.locale: locale_map[args.locale]}
    else:
        locales = locale_map

    client, project_id, _ = make_client()
    print(f"Project {project_id}  Locales: {', '.join(locales)}")
    print()

    for loc, lang_id in locales.items():
        print(f"=== {loc} ({lang_id}) ===")
        try:
            new = update_credits_for_locale(client, project_id, loc, lang_id)
        except Exception as e:
            print(f"  [ERR] {e}", file=sys.stderr)
            return 1
        for k, v in new["Translator"].items():
            label = ", ".join(v) if v else "(none)"
            print(f"  {k:11s}: {len(v):2d} {label}")
        print(f"  Texture    : {len(new['Texture_reworker']):2d} (preserved)")
        print(f"  Updated    : {new['translation_updated']}")
        print()

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
