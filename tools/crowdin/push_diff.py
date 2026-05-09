"""HEAD-based diff for smart push.

Compares Crowdin_Mirror/translations/<locale>/<cat>/*.tsv (the would-be
upload, generated from current xlsx) against the same files in git's HEAD —
i.e. the last committed canonical state. Only rows whose translation differs
since last commit are pushed.

Why HEAD (not state file):
  - HEAD is shared by all contributors after `git pull` — no per-user state
    file to lose.
  - Fresh-cloned translators inherit a meaningful baseline immediately.
  - Self-correcting: commit after push refreshes baseline for future pushes.

Cost: invokes `git show HEAD:<path>` per Mirror file. Cheap (~ms per file).
"""
import csv
import io
import subprocess
from pathlib import Path


def read_head_tsv(repo_root: Path, rel_path: str) -> str | None:
    """Return the file contents at HEAD for `rel_path` (POSIX path relative
    to repo_root). Returns None if the file is not in HEAD (new file).
    """
    result = subprocess.run(
        ["git", "show", f"HEAD:{rel_path}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return None
    return result.stdout


def parse_tsv_translations(text: str) -> dict[str, str]:
    """Parse a TSV containing identifier+translation columns.

    Returns {identifier: translation} for non-empty translations.
    Used both for Crowdin_Mirror/translations/<locale>/<cat>/*.tsv (already
    has identifier column) and for canonical TSV (which has structural
    columns — handled by `parse_canonical_tsv` instead).
    """
    if not text:
        return {}
    rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
    if not rows:
        return {}
    header = rows[0]
    if "identifier" not in header or "translation" not in header:
        return {}
    id_idx = header.index("identifier")
    tx_idx = header.index("translation")
    out: dict[str, str] = {}
    for r in rows[1:]:
        while len(r) < len(header):
            r.append("")
        ident = r[id_idx].strip()
        tx = r[tx_idx]
        if ident and tx.strip():
            out[ident] = tx
    return out


def parse_canonical_tsv_translations(text: str, id_func, tx_field: str) -> dict[str, str]:
    """Parse a canonical TSV (the one in Translations/<locale>/<cat>/<sheet>.tsv).

    Canonical TSV doesn't have a precomputed `identifier` column — the
    identifier is derived from structural columns via `id_func(row_dict)`.
    `tx_field` is the column name holding the translation ("translation"
    for Translation/Glossary, "Translation" for Texture).
    """
    if not text:
        return {}
    rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
    if not rows:
        return {}
    header = rows[0]
    if tx_field not in header:
        return {}
    tx_idx = header.index(tx_field)
    out: dict[str, str] = {}
    for r in rows[1:]:
        while len(r) < len(header):
            r.append("")
        row_dict = dict(zip(header, r))
        ident = id_func(row_dict)
        if not ident:
            continue
        tx = r[tx_idx]
        if tx.strip():
            out[ident] = tx
    return out


def read_mirror_translations(mirror_locale_dir: Path) -> dict[str, dict[str, str]]:
    """Read every TSV under mirror_locale_dir, return {file_relpath: {id: translation}}."""
    out: dict[str, dict[str, str]] = {}
    for tsv in sorted(mirror_locale_dir.rglob("*.tsv")):
        rel = tsv.relative_to(mirror_locale_dir).as_posix()
        text = tsv.read_text(encoding="utf-8")
        rows = parse_tsv_translations(text)
        if rows:
            out[rel] = rows
    return out


def diff_against_head(
    repo_root: Path,
    locale: str,
    mirror_locale_dir: Path,
    canonical_locale_dir: Path,
) -> dict[str, dict[str, str]]:
    """Return rows in Mirror that differ from HEAD's canonical TSV.

    For each file in mirror_locale_dir (e.g. Translation/Main.tsv):
      - Map to the canonical TSV path: <canonical_locale_dir>/<category>/<sheet>.tsv
      - Read HEAD's version of that canonical TSV via git
      - Compute identifier→translation map for HEAD
      - Compute diff: rows in Mirror but not in HEAD, or with different value

    Returns {file_relpath: {identifier: translation}} ready to upload.
    """
    # Lazy-import so this module works without crowdin-api-client deps just for diff.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from crowdin.identifier import (
        make_translation_id,
        make_glossary_id,
        make_texture_id,
    )

    id_func = {
        "Translation": make_translation_id,
        "Glossary": make_glossary_id,
        "Texture": make_texture_id,
    }
    tx_field = {
        "Translation": "translation",
        "Glossary": "translation",
        "Texture": "Translation",
    }

    local = read_mirror_translations(mirror_locale_dir)
    out: dict[str, dict[str, str]] = {}

    for rel, local_rows in local.items():
        # Mirror path: Translation/Main.tsv  →  canonical: Translations/<locale>/Translation/Main.tsv
        category = rel.split("/", 1)[0]
        if category not in id_func:
            continue
        canonical_rel_path = (canonical_locale_dir / rel).relative_to(repo_root).as_posix()
        head_text = read_head_tsv(repo_root, canonical_rel_path)
        head_rows = parse_canonical_tsv_translations(
            head_text or "", id_func[category], tx_field[category]
        )

        changed: dict[str, str] = {
            ident: tx
            for ident, tx in local_rows.items()
            if head_rows.get(ident) != tx
        }
        if changed:
            out[rel] = changed

    return out


def total_rows(diff: dict[str, dict[str, str]]) -> int:
    return sum(len(v) for v in diff.values())
