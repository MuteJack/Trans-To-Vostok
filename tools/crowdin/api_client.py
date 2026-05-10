"""Thin Python SDK wrapper around crowdin-api-client.

Replaces the need for the Crowdin CLI (Java-based) -- translators only need
`pip install -r tools/requirements.txt`.

Operations exposed:
  - upload_translations_for_locale(locale_dir, language_id, ...)
        Upload every non-empty translation in locale_dir (full sync).
  - upload_translations_diff(diff_rows, language_id, ...)
        Upload only the (file, identifier, translation) rows in diff_rows
        -- used by smart push to avoid overwriting other contributors' edits.
  - download_translations(language_id=None, extract_to=None)
        Build + download project translations as zip, extract.

Configuration:
  - Project ID + source path prefix: tools/crowdin/config.json (committed)
  - Auth token: secrets.json:crowdin_personal_token (gitignored)
"""
import csv
import io
import json
import sys
import tempfile
import time
import urllib.request
import zipfile
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
                       auto_approve: bool = False,
                       import_eq_suggestions: bool = True) -> dict:
    """Register an uploaded storage as a translation for one (file, language).

    `import_eq_suggestions=True` is set by default to encourage Crowdin to
    accept translations identical to source (proper nouns, abbreviations,
    UI labels that we intentionally keep in English). Crowdin's default is
    False, which silently skips these — visible as empty translation cells
    on the web UI.
    """
    return client.translations.upload_translation(
        projectId=project_id,
        languageId=language_id,
        fileId=file_id,
        storageId=storage_id,
        autoApproveImported=auto_approve,
        importEqSuggestions=import_eq_suggestions,
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


def _build_locale_to_folder_map(client, project_id: int) -> dict[str, str]:
    """Map Crowdin's exported locale codes to our canonical folder names.

    The zip Crowdin builds uses each language's BCP-47 `locale` (e.g. "ko-KR")
    as the folder segment under `Crowdin_Mirror/translations/`. Our repo
    layout uses friendly folder names from languages.json (e.g. "Korean").

    We bridge the two by:
      - languages.json registry: folder_name -> crowdin_id (e.g. Korean -> ko)
      - Crowdin API:             id -> locale (e.g. ko -> ko-KR)
    Compose: locale -> folder_name (e.g. ko-KR -> Korean).

    Both `locale` and `id` are added as keys for robustness, since some
    builds export by short id (e.g. pt-BR) which already matches `locale`.
    """
    languages_path = _SCRIPT_DIR.parent / "languages.json"
    registry = json.loads(languages_path.read_text(encoding="utf-8"))["languages"]
    cid_to_folder = {
        entry["crowdin_id"]: dir_name
        for dir_name, entry in registry.items()
        if entry.get("crowdin_id")
    }

    proj = client.projects.get_project(projectId=project_id)
    target_langs = proj["data"].get("targetLanguages", [])
    out: dict[str, str] = {}
    for lang in target_langs:
        cid = lang.get("id")
        folder = cid_to_folder.get(cid)
        if not folder:
            continue
        for code in (lang.get("locale"), cid):
            if code:
                out[code] = folder
    return out


def download_translations(
    language_id: str | None = None,
    extract_to: Path | None = None,
    *,
    poll_interval: float = 3.0,
    poll_timeout: float = 600.0,
) -> Path:
    """Build + download project translations as zip and extract.

    Steps:
      1. Trigger a project build (server-side export). If language_id is given,
         build only that target; else build all targets.
      2. Poll build status until "finished" (or fail/cancel/timeout).
      3. Fetch the resulting zip via the issued URL.
      4. Extract zip into extract_to (defaults to cwd), remapping the
         locale folder segment from Crowdin's BCP-47 code (e.g. ko-KR) to
         the canonical folder name (e.g. Korean) per languages.json.

    Returns extract_to.
    """
    client, project_id, _ = make_client()
    extract_to = Path(extract_to) if extract_to else Path.cwd()

    locale_map = _build_locale_to_folder_map(client, project_id)

    build_args: dict = {"projectId": project_id}
    if language_id:
        build_args["targetLanguageIds"] = [language_id]
    print(f"Triggering Crowdin build (project {project_id}, "
          f"lang={language_id or 'all'})...")
    build = client.translations.build_crowdin_project_translation(**build_args)
    build_id = build["data"]["id"]
    print(f"  Build ID: {build_id}")

    deadline = time.time() + poll_timeout
    last_progress = -1
    while True:
        status = client.translations.check_project_build_status(
            projectId=project_id, buildId=build_id
        )
        state = status["data"]["status"]
        progress = status["data"].get("progress", 0)
        if progress != last_progress or state != "inProgress":
            print(f"  Build status: {state} ({progress}%)")
            last_progress = progress
        if state == "finished":
            break
        if state in ("failed", "canceled"):
            raise RuntimeError(f"Crowdin build {state}: {status['data']}")
        if time.time() > deadline:
            raise RuntimeError(f"Crowdin build timed out after {poll_timeout}s")
        time.sleep(poll_interval)

    dl = client.translations.download_project_translations(
        projectId=project_id, buildId=build_id
    )
    url = dl["data"]["url"]

    print(f"  Downloading zip...")
    with urllib.request.urlopen(url) as resp:
        zip_bytes = resp.read()
    print(f"  Got {len(zip_bytes)} bytes; extracting to {extract_to}")

    extract_to.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for member in z.infolist():
            if member.is_dir():
                continue
            new_name = _rewrite_locale_in_path(member.filename, locale_map)
            dest = extract_to / new_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(dest, "wb") as out:
                out.write(src.read())
            written += 1
        skipped = len(z.namelist()) - written
    print(f"  Wrote {written} files (skipped {skipped} dir entries)")

    return extract_to


def _rewrite_locale_in_path(path: str, locale_map: dict[str, str]) -> str:
    """Replace the locale segment under `Crowdin_Mirror/translations/<locale>/`.

    No-op for paths outside that prefix or for locales not in the map
    (extracted as-is so nothing is silently lost).
    """
    parts = path.split("/")
    if (len(parts) >= 3
            and parts[0] == "Crowdin_Mirror"
            and parts[1] == "translations"
            and parts[2] in locale_map):
        parts[2] = locale_map[parts[2]]
        return "/".join(parts)
    return path
