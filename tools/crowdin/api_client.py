"""Thin Python SDK wrapper around crowdin-api-client.

Replaces the need for the Crowdin CLI (Java-based) — translators only need
`pip install -r tools/requirements.txt`.

Operations exposed:
  - upload_translations_for_locale(locale_dir, language_id, ...)
        Upload every non-empty translation in locale_dir (full sync).
  - upload_translations_diff(diff_rows, language_id, ...)
        Upload only the (file, identifier, translation) rows in diff_rows
        — used by smart push to avoid overwriting other contributors' edits.

Configuration:
  - Project ID + source path prefix: tools/crowdin/config.json (committed)
  - Auth token: secrets.json:crowdin_personal_token (gitignored)

The flow for uploading one TSV:
  1. POST /storages          (upload file bytes, get storage_id)
  2. POST /projects/{id}/translations/{lang}   (link storage_id to source file)
"""
import csv
import json
import sys
import tempfile
from pathlib import Path

try:
    from crowdin_api import CrowdinClient
except ImportError:
    print("ERROR: crowdin-api-client is required. pip install -r tools/requirements.txt",
          file=sys.stderr)
    raise

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.secrets import get_crowdin_personal_token

_SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = _SCRIPT_DIR / "config.json"


def _load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def make_client() -> tuple["CrowdinClient", int, str]:
    """Returns (client, project_id, source_path_prefix). Errors if token missing."""
    token = get_crowdin_personal_token()
    if not token:
        raise RuntimeError(
            "Crowdin token not found. Add `crowdin_personal_token` to secrets.json "
            "(copy from secrets.example.json) or set CROWDIN_PERSONAL_TOKEN env var."
        )
    cfg = _load_config()
    client = CrowdinClient(token=token, project_id=cfg["project_id"])
    return client, cfg["project_id"], cfg["source_path_prefix"]


def list_source_files(client, project_id: int) -> dict[str, int]:
    """Returns {full_path: file_id} for all source files in the project.

    Pagination handled automatically — Crowdin caps at 500 per request.
    """
    out: dict[str, int] = {}
    offset = 0
    limit = 500
    while True:
        resp = client.source_files.list_files(
            projectId=project_id, limit=limit, offset=offset
        )
        items = resp.get("data", [])
        if not items:
            break
        for entry in items:
            data = entry["data"]
            # Crowdin's path is relative to project root, leading slash included.
            out[data["path"]] = data["id"]
        if len(items) < limit:
            break
        offset += len(items)
    return out


def upload_storage(client, file_path: Path) -> int:
    """Upload a file's bytes to Crowdin's /storages and return storage_id."""
    with open(file_path, "rb") as f:
        resp = client.storages.add_storage(file=f)
    return resp["data"]["id"]


def upload_translation(client, project_id: int, language_id: str,
                       file_id: int, storage_id: int,
                       auto_approve: bool = False) -> dict:
    """Register an uploaded storage as a translation for one (file, language)."""
    return client.translations.upload_translation(
        projectId=project_id,
        languageId=language_id,
        fileId=file_id,
        storageId=storage_id,
        autoApproveImported=auto_approve,
    )


def upload_translations_for_locale(
    locale_dir: Path,
    language_id: str,
    *,
    auto_approve: bool = False,
) -> dict:
    """Upload every TSV under locale_dir/* to Crowdin for the given language.

    locale_dir is e.g. Crowdin_Mirror/translations/Korean/. Each TSV's path
    relative to locale_dir is used to locate the matching source file:
        locale_dir/Translation/Main.tsv
            → source file path "<source_path_prefix>/Translation/Main.tsv"

    Returns stats dict: {"uploaded": int, "skipped_no_source": int, "errors": list}
    """
    client, project_id, source_prefix = make_client()

    print(f"Listing source files for project {project_id}...")
    sources = list_source_files(client, project_id)
    print(f"  {len(sources)} source files found")

    stats = {"uploaded": 0, "skipped_no_source": 0, "errors": []}
    tsv_paths = sorted(locale_dir.rglob("*.tsv"))
    print(f"Local TSVs to upload: {len(tsv_paths)}")
    print()

    for tsv in tsv_paths:
        rel = tsv.relative_to(locale_dir).as_posix()
        source_path = f"{source_prefix}/{rel}"
        file_id = sources.get(source_path)
        if file_id is None:
            print(f"  [SKIP] no source file for {rel}  (expected {source_path})")
            stats["skipped_no_source"] += 1
            continue
        try:
            storage_id = upload_storage(client, tsv)
            upload_translation(
                client, project_id, language_id, file_id, storage_id,
                auto_approve=auto_approve,
            )
            stats["uploaded"] += 1
            print(f"  [OK]   {rel}  (file_id={file_id})")
        except Exception as e:
            stats["errors"].append((rel, str(e)))
            print(f"  [ERR]  {rel}  → {e}")

    return stats


# Minimal scheme for diff uploads. Crowdin only needs `identifier` (matching key)
# + `translation` (value). Other columns are kept empty.
_DIFF_SCHEME = ["identifier", "source_phrase", "translation", "context", "labels", "max_length"]


def _write_minimal_tsv(rows: dict[str, str], dest: Path) -> None:
    """Write a TSV with only identifier + translation populated."""
    with open(dest, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(_DIFF_SCHEME)
        for ident, tx in rows.items():
            w.writerow([ident, "", tx, "", "", ""])


def upload_translations_diff(
    diff_rows: dict[str, dict[str, str]],
    language_id: str,
    *,
    auto_approve: bool = False,
) -> dict:
    """Upload only the rows in diff_rows. Each file gets a minimal TSV with
    just its changed rows; Crowdin matches by identifier and updates only those.

    diff_rows: {file_relpath: {identifier: translation_string}}
    file_relpath uses forward slashes, e.g. "Translation/Main.tsv".

    Returns stats:
        {"uploaded_rows": int, "uploaded_files": int,
         "skipped_no_source": int, "errors": list[(rel, msg)]}
    """
    if not diff_rows:
        return {"uploaded_rows": 0, "uploaded_files": 0,
                "skipped_no_source": 0, "errors": []}

    client, project_id, source_prefix = make_client()

    print(f"Listing source files for project {project_id}...")
    sources = list_source_files(client, project_id)
    print(f"  {len(sources)} source files found")
    print()

    stats = {"uploaded_rows": 0, "uploaded_files": 0,
             "skipped_no_source": 0, "errors": []}

    with tempfile.TemporaryDirectory(prefix="crowdin_diff_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        for rel, ids_map in sorted(diff_rows.items()):
            source_path = f"{source_prefix}/{rel}"
            file_id = sources.get(source_path)
            if file_id is None:
                print(f"  [SKIP] {rel}  no Crowdin source (expected {source_path})")
                stats["skipped_no_source"] += 1
                continue

            # Write minimal TSV (uses safe path under temp dir)
            tmp_tsv = tmpdir_path / rel.replace("/", "_")
            _write_minimal_tsv(ids_map, tmp_tsv)

            try:
                storage_id = upload_storage(client, tmp_tsv)
                upload_translation(
                    client, project_id, language_id, file_id, storage_id,
                    auto_approve=auto_approve,
                )
                stats["uploaded_files"] += 1
                stats["uploaded_rows"] += len(ids_map)
                print(f"  [OK]   {rel}  ({len(ids_map)} rows, file_id={file_id})")
            except Exception as e:
                stats["errors"].append((rel, str(e)))
                print(f"  [ERR]  {rel}  → {e}")

    return stats
