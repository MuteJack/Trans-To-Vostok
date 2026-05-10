"""Composite identifier generation for Crowdin string `identifier` column.

Crowdin requires a single, file-unique identifier per string. Our xlsx
schema uses multiple columns to identify a row (filename / parent /
name / type / property / unique_id for Translation; File Name + Text
for Texture). This module composes those columns into a single
deterministic string.

Properties:
  - **Stable**: same row → same identifier across runs (push/pull match)
  - **Unique-within-file**: rows that differ in their identifying
    columns get distinct identifiers
  - **Reversible-ish**: prefix tells the category at a glance (T/X);
    body keeps the structural info readable

Patterns:
  Translation (location-bound):
    T:<filename>:<parent>:<name>:<type>:<property>[:<unique_id>]
  Translation (global — method=substr / literal/pattern with no location):
    T:GLOBAL:<method>:<text_hash>
  Texture:
    X:<File_Name>:<text_hash>
"""
import hashlib

# How many hex chars to keep from sha1 — collision risk @ 8 chars is
# ~1 in 4 billion, plenty for our scale (~3000 rows).
HASH_LENGTH = 8


def short_hash(s: str) -> str:
    """Stable, short hash of a string. Used for global / fallback ids."""
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:HASH_LENGTH]


def _is_global_translation(row: dict) -> bool:
    """A Translation row is 'global' if it uses substr, or it's
    literal/pattern WITHOUT a location (== applies anywhere in the game)."""
    method = (row.get("method") or "").strip()
    if method == "substr":
        return True
    if method in ("literal", "pattern", ""):
        # method '' defaults to literal in our schema
        location = (row.get("location") or "").strip()
        return not location
    return False


def make_translation_id(row: dict) -> str:
    """Generate composite_id for a Translation row.

    Returns "" for rows that should NOT be pushed (ignore / untranslatable).
    Caller should filter on empty return.
    """
    method = (row.get("method") or "").strip()
    if method == "ignore":
        return ""
    if (row.get("untranslatable") or "").strip() == "1":
        return ""
    if not (row.get("text") or "").strip():
        return ""

    if _is_global_translation(row):
        effective_method = method or "literal"
        return f"T:GLOBAL:{effective_method}:{short_hash(row['text'])}"

    # Location-bound: filename:parent:name:type:property:unique_id:text_hash
    # text_hash is ALWAYS included because the same node location can hold
    # multiple text variants (scoped literal with dynamic text — e.g.,
    # `Tooltip/.../Penetration:Value:Label` showing "Level 1" through "Level 5").
    parts = [
        (row.get("filename") or "").strip(),
        (row.get("parent") or "").strip(),
        (row.get("name") or "").strip(),
        (row.get("type") or "").strip(),
        (row.get("property") or "").strip(),
        (row.get("unique_id") or "").strip(),
        short_hash(row.get("text", "")),
    ]
    return "T:" + ":".join(parts)


def make_texture_id(row: dict) -> str:
    """Generate composite_id for a Texture row."""
    text = (row.get("Text") or "").strip()
    if not text:
        return ""
    file_name = (row.get("File Name") or "").strip()
    parts = [
        file_name or "_",
        short_hash(text),
    ]
    return "X:" + ":".join(parts)
