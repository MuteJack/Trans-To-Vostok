"""
Translate unique.tsv using the DeepL API.

Reads .tmp/unique_text/<source>/unique.tsv, sends each text to DeepL with
placeholder protection, and writes .tmp/unique_text/<source>/translated_<TARGET>.tsv.

Placeholder protection:
    {name}  ->  wrapped as <x>{name}</x>
                tag_handling="xml" + ignore_tags=["x"] tells DeepL to preserve
                the content of <x>...</x> exactly.
    \\n      ->  preserved automatically (preserve_formatting=True)

Auth:
    secrets.json (repo root) — `deepl_api_key` field.
    Falls back to DEEPL_AUTH_KEY environment variable if absent.
    See secrets.example.json for setup.

Output (under <mod_root>/.tmp/unique_text/<source>/):
    translated_<TARGET>.tsv     unique_id, source, translation, status, message

Status values:
    ok                  translated cleanly, all placeholders preserved
    placeholder_lost    one or more {placeholder} missing in result (warning)
    error               DeepL API error (translation field empty)

Resume:
    If translated_<TARGET>.tsv already exists, rows present there are skipped.
    Re-running picks up where the previous run stopped.

Usage:
    python tools/translate_with_deepl.py <TARGET_LANG> [--source <locale>] [--limit N] [--dry-run]

Examples:
    python tools/translate_with_deepl.py JA               # Japanese, source=Korean
    python tools/translate_with_deepl.py JA --limit 10    # first 10 rows only
    python tools/translate_with_deepl.py PT-BR            # Brazilian Portuguese
    python tools/translate_with_deepl.py JA --dry-run     # show plan, no API call

DeepL language codes: see https://developers.deepl.com/docs/getting-started/supported-languages
"""
import csv
import re
import sys
from pathlib import Path

try:
    import deepl
except ImportError:
    print("ERROR: deepl is required. pip install deepl", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.secrets import get_deepl_api_key

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
PROTECTED_RE = re.compile(r"<x>(\{[a-zA-Z_][a-zA-Z0-9_]*\})</x>")
BATCH_SIZE = 50  # DeepL accepts up to 50 texts per API call


def load_api_key() -> str | None:
    """Load DeepL API key from secrets.json (or DEEPL_AUTH_KEY env var)."""
    return get_deepl_api_key()


def wrap_placeholders(text: str) -> list[str]:
    """XML-escape special chars (& < >), then wrap {name} as <x>{name}</x>.

    Required because tag_handling="xml" makes DeepL parse input as XML;
    bare '&' or '<' would cause "Tag handling parsing failed" errors.

    Returns (wrapped_text, list of original placeholders before wrap).
    """
    placeholders: list[str] = []

    # 1. XML-escape special characters first
    escaped = (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))

    # 2. Wrap placeholders. {name} survives escape (braces aren't XML-special)
    def repl(m: "re.Match[str]") -> str:
        placeholders.append(m.group(0))
        return f"<x>{m.group(0)}</x>"

    wrapped = PLACEHOLDER_RE.sub(repl, escaped)
    return wrapped, placeholders


def unwrap_placeholders(text: str) -> str:
    """Reverse wrap_placeholders: unwrap <x>...</x> then unescape XML entities."""
    # 1. Unwrap <x>{name}</x> -> {name}
    out = PROTECTED_RE.sub(r"\1", text)
    # 2. Reverse XML escapes (order: &amp; LAST to avoid double-decoding)
    out = (out
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&"))
    return out


def verify_placeholders(source: str, translation: str) -> bool:
    """All source placeholders must appear in the translation (multiset equality)."""
    return sorted(PLACEHOLDER_RE.findall(source)) == sorted(PLACEHOLDER_RE.findall(translation))


def load_unique(unique_path: Path) -> list[dict]:
    rows = []
    with open(unique_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(row)
    return rows


def load_existing(translated_path: Path) -> dict:
    """Load existing translations keyed by SOURCE TEXT (not unique_id).

    Keying by text makes resume robust to unique.tsv re-generation: when
    export_unique_text.py re-runs and assigns different unique_ids, we still
    correctly recognize already-translated texts.

    Error rows are NOT counted as 'done' so they will be retried.
    """
    if not translated_path.exists():
        return {}
    latest: dict = {}
    with open(translated_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            text = row.get("source", "")
            if text:
                # last occurrence wins (in case of duplicates from prior runs)
                latest[text] = row
    # only return rows that succeeded; error rows will be retried
    return {text: row for text, row in latest.items() if row.get("status") != "error"}


def append_rows(translated_path: Path, header: list[str], rows: list[dict]) -> None:
    """Append rows to translated_<TARGET>.tsv (writes header on first write)."""
    is_new = not translated_path.exists()
    translated_path.parent.mkdir(parents=True, exist_ok=True)
    with open(translated_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        if is_new:
            writer.writerow(header)
        for row in rows:
            writer.writerow([row.get(c, "") for c in header])
        f.flush()


def translate_batch(translator, batch: list[dict], target_lang: str) -> list[dict]:
    """Translate a batch of {unique_id, text, ...} rows. Returns result rows."""
    wrapped_texts = []
    for item in batch:
        wrapped, _ = wrap_placeholders(item["text"])
        wrapped_texts.append(wrapped)

    try:
        results = translator.translate_text(
            wrapped_texts,
            source_lang="EN",
            target_lang=target_lang,
            tag_handling="xml",
            ignore_tags=["x"],
            preserve_formatting=True,
        )
    except deepl.DeepLException as e:
        return [
            {
                "unique_id": item["unique_id"],
                "source": item["text"],
                "translation": "",
                "status": "error",
                "message": str(e),
            }
            for item in batch
        ]

    out = []
    for item, result in zip(batch, results):
        translated = unwrap_placeholders(result.text)
        if verify_placeholders(item["text"], translated):
            status, message = "ok", ""
        else:
            src_phs = sorted(PLACEHOLDER_RE.findall(item["text"]))
            tgt_phs = sorted(PLACEHOLDER_RE.findall(translated))
            status = "placeholder_lost"
            message = f"src={src_phs} tgt={tgt_phs}"
        out.append({
            "unique_id": item["unique_id"],
            "source": item["text"],
            "translation": translated,
            "status": status,
            "message": message,
        })
    return out


def parse_args(argv: list[str]) -> tuple[str, str, int | None, bool] | None:
    """Returns (target_lang, source_locale, limit, dry_run) or None on parse error."""
    target_lang: str | None = None
    source_locale = "Korean"
    limit: int | None = None
    dry_run = False

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--source":
            if i + 1 >= len(argv):
                print("[ERROR] --source requires a value")
                return None
            source_locale = argv[i + 1]
            i += 2
        elif a == "--limit":
            if i + 1 >= len(argv):
                print("[ERROR] --limit requires a value")
                return None
            try:
                limit = int(argv[i + 1])
            except ValueError:
                print(f"[ERROR] --limit must be integer: {argv[i + 1]}")
                return None
            i += 2
        elif a == "--dry-run":
            dry_run = True
            i += 1
        elif a.startswith("--"):
            print(f"[ERROR] Unknown flag: {a}")
            return None
        else:
            if target_lang is None:
                target_lang = a.upper()
            else:
                print(f"[ERROR] Unexpected positional argument: {a}")
                return None
            i += 1

    if target_lang is None:
        return None
    return target_lang, source_locale, limit, dry_run


def main() -> int:
    parsed = parse_args(sys.argv[1:])
    if parsed is None:
        print(__doc__.split("Usage:")[1].split("DeepL language codes")[0])
        return 1
    target_lang, source_locale, limit, dry_run = parsed

    script_dir = Path(__file__).resolve().parent
    # script_dir = mods/Trans To Vostok/tools/utils
    tools_dir = script_dir.parent
    mod_root = tools_dir.parent
    base = mod_root / ".tmp" / "unique_text" / source_locale
    unique_path = base / "unique.tsv"
    translated_path = base / f"translated_{target_lang}.tsv"

    if not unique_path.exists():
        print(f"[ERROR] unique.tsv not found: {unique_path}")
        print(f"Run first: python tools/utils/export_unique_text.py {source_locale}")
        return 1

    api_key = load_api_key()
    if api_key is None and not dry_run:
        print("[ERROR] DeepL API key not found.")
        print(f"  - Add `deepl_api_key` to: {mod_root / 'secrets.json'}")
        print(f"    (copy from secrets.example.json and fill in)")
        print("  - Or set env var: DEEPL_AUTH_KEY=<key>")
        return 1

    print(f"Source unique.tsv  : {unique_path}")
    print(f"Output translated  : {translated_path}")
    print(f"Source language    : EN")
    print(f"Target language    : {target_lang}")
    if dry_run:
        print(f"DRY RUN (no API calls will be made)")
    print()

    rows = load_unique(unique_path)
    if limit is not None:
        rows = rows[:limit]
        print(f"Limited to first {limit} rows")

    existing = load_existing(translated_path)
    todo = [r for r in rows if r["text"] not in existing]
    skipped = len(rows) - len(todo)
    print(f"Total rows         : {len(rows)}")
    print(f"Already translated : {skipped}")
    print(f"To translate       : {len(todo)}")
    print()

    if not todo:
        print("Nothing to do.")
        return 0

    total_chars = sum(len(r["text"]) for r in todo)
    print(f"Estimated chars    : {total_chars}  (~{total_chars / 500_000 * 100:.2f}% of 500K Free quota)")
    print()

    if dry_run:
        return 0

    translator = deepl.Translator(api_key)
    try:
        usage = translator.get_usage()
        if usage.character.valid:
            print(f"Quota before       : {usage.character.count}/{usage.character.limit} chars")
            print()
    except Exception as e:
        print(f"[WARN] Could not fetch usage: {e}")

    header = ["unique_id", "source", "translation", "status", "message"]

    ok_count = 0
    warn_count = 0
    err_count = 0

    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i:i + BATCH_SIZE]
        results = translate_batch(translator, batch, target_lang)
        append_rows(translated_path, header, results)
        for r in results:
            if r["status"] == "ok":
                ok_count += 1
            elif r["status"] == "placeholder_lost":
                warn_count += 1
                print(f"  [WARN] uid={r['unique_id']} placeholder mismatch — {r['message']}")
            else:
                err_count += 1
                print(f"  [ERROR] uid={r['unique_id']} {r['message']}")
        progress = i + len(batch)
        print(f"  progress: {progress}/{len(todo)}  (ok={ok_count} warn={warn_count} err={err_count})")

    print()
    print("=" * 60)
    print(f"Done: {ok_count} ok, {warn_count} placeholder warnings, {err_count} errors")
    print(f"Output: {translated_path.relative_to(mod_root)}")

    try:
        usage = translator.get_usage()
        if usage.character.valid:
            print(f"Quota after        : {usage.character.count}/{usage.character.limit} chars")
    except Exception:
        pass

    return 0 if err_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
