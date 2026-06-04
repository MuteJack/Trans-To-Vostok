"""Find Translation rows where `text` differs only in whitespace from the parser.

For every locale (Template included), compare each Translation row's
`text` column against the parser-extracted game text. If the raw text
differs but the whitespace-normalized form matches, the row is flagged
as WHITESPACE_MISMATCH — a common symptom of stray trailing newlines,
CRLF/LF drift, or extra internal spaces introduced during xlsx editing.

Why parse-direct (not via Template):
  Comparing locale-vs-Template lets a Template-side whitespace bug
  propagate silently to every locale that synced from it. Going
  directly to parse catches such bugs at the locale level too, with
  no transitive trust assumption.

Matching:
  tscn / scn  by (filetype, unique_id) — exact uid lookup
  tres / gd   by text-set membership — fallback uses the normalized
              whitespace form to detect "same content, different ws"

Scope (Translation only): rows where BOTH `filename` and `filetype`
are set — consistent with check_deprecated.py. Method / untranslatable
not filtered (catalog hygiene check).

Texture rows are NOT checked: Texture's `Text` column is hand-entered
(what's drawn on the texture), not derived from a parser, so there is
no parse-side reference to compare against. Use check_diff_with_Template
for Texture text drift between Template and locale.

Translator-side whitespace (text ↔ translation) is a different concern
covered by check_whitespace_translated.py.

Usage:
  python tools/validation/check_whitespace_text.py Template
  python tools/validation/check_whitespace_text.py Korean
  python tools/validation/check_whitespace_text.py all
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent.parent
TRANSLATIONS = REPO / "Translations"
PARSED_TEXT_DIR = REPO / ".tmp" / "parsed_text"
LOCALE_JSON = REPO / "src" / "locale.json"
TEMPLATE_LOCALE = "Template"

SCENE_FILETYPES = {"tscn", "scn"}
KNOWN_FILETYPES = SCENE_FILETYPES | {"tres", "gd"}
SAMPLE_LIMIT = 10

sys.path.insert(0, str(REPO / "tools"))
from helper.helper_translation_common import (
    load_tsv_index,
    load_tres_text_set,
    load_gd_text_set,
)


class Issue(NamedTuple):
    locale: str
    sheet: str
    row: int
    filetype: str
    detail: str


def _normalize_ws(s: str) -> str:
    """Collapse every whitespace run to a single space and strip."""
    return " ".join((s or "").split())


def _escape(s: str) -> str:
    return (s or "").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def _preview(s: str, n: int = 40) -> str:
    p = _escape(s)
    return p[:n] + ("..." if len(p) > n else "")


def check_locale_against_parse(locale: str, tsv_index: dict,
                               tres_texts: set, gd_texts: set) -> list[Issue]:
    """Compare every location-bound Translation row in `locale` against the
    parser's actual game text. Report rows whose raw text differs from the
    parser's but matches after whitespace normalization."""
    issues: list[Issue] = []
    tr_dir = TRANSLATIONS / locale / "tsv" / "Translation"
    if not tr_dir.exists():
        return issues

    # Pre-normalize parse-side text sets for O(1) "any normalized match" lookup.
    norm_tres = {_normalize_ws(t): t for t in tres_texts}
    norm_gd = {_normalize_ws(t): t for t in gd_texts}

    for tsv in sorted(tr_dir.glob("*.tsv")):
        if tsv.name.startswith("_"):
            continue
        with open(tsv, encoding="utf-8", newline="") as f:
            for row_num, row in enumerate(csv.DictReader(f, delimiter="\t"), start=2):
                filename = (row.get("filename") or "").strip()
                filetype = (row.get("filetype") or "").strip()
                if not filename or filetype not in KNOWN_FILETYPES:
                    continue
                text = row.get("text", "") or ""
                if not text:
                    continue

                if filetype in SCENE_FILETYPES:
                    uid = (row.get("unique_id") or "").strip()
                    if not uid:
                        continue
                    candidates = tsv_index.get(uid) or []
                    if any(c["text"] == text for c in candidates):
                        continue  # exact match, no drift
                    norm = _normalize_ws(text)
                    match = next((c for c in candidates
                                  if _normalize_ws(c["text"]) == norm), None)
                    if match is not None:
                        issues.append(Issue(
                            locale, tsv.stem, row_num, filetype,
                            f"uid={uid}  xlsx={_preview(text)!r}  parse={_preview(match['text'])!r}",
                        ))

                elif filetype == "tres":
                    if text in tres_texts:
                        continue
                    parse_match = norm_tres.get(_normalize_ws(text))
                    if parse_match is not None:
                        issues.append(Issue(
                            locale, tsv.stem, row_num, filetype,
                            f"xlsx={_preview(text)!r}  parse={_preview(parse_match)!r}",
                        ))

                elif filetype == "gd":
                    if text in gd_texts:
                        continue
                    parse_match = norm_gd.get(_normalize_ws(text))
                    if parse_match is not None:
                        issues.append(Issue(
                            locale, tsv.stem, row_num, filetype,
                            f"xlsx={_preview(text)!r}  parse={_preview(parse_match)!r}",
                        ))
    return issues


def _discover_locales() -> list[str]:
    locales: list[str] = [TEMPLATE_LOCALE]
    if not LOCALE_JSON.exists():
        return locales
    try:
        data = json.loads(LOCALE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return locales
    for loc in data.get("locales", []):
        name = loc.get("dir")
        if loc.get("enabled") and name and name not in ("English", TEMPLATE_LOCALE):
            locales.append(name)
    return locales


def _summarize(issues: list[Issue], locale: str) -> None:
    subset = [i for i in issues if i.locale == locale]
    if not subset:
        return
    by_filetype: dict[str, int] = defaultdict(int)
    for i in subset:
        by_filetype[i.filetype] += 1
    print(f"  WHITESPACE_MISMATCH: {len(subset)}")
    for ft, n in sorted(by_filetype.items()):
        print(f"    {ft:6s} {n}")
    for i in subset[:SAMPLE_LIMIT]:
        print(f"      {i.filetype:6s} {i.sheet}:r{i.row}  {i.detail}")
    if len(subset) > SAMPLE_LIMIT:
        print(f"      ... and {len(subset) - SAMPLE_LIMIT} more")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "locale",
        help="Locale name (e.g. Korean), 'Template', or 'all'",
    )
    args = parser.parse_args(argv[1:])

    if args.locale == "all":
        locales = _discover_locales()
    else:
        if not (TRANSLATIONS / args.locale).exists():
            print(f"[ERROR] locale directory not found: {args.locale}")
            return 1
        locales = [args.locale]

    if not PARSED_TEXT_DIR.exists():
        print(f"[ERROR] parsed_text/ not found at {PARSED_TEXT_DIR.relative_to(REPO)}")
        print(f"        Run: python tools/parse_translatables.py")
        return 1

    tsv_index = load_tsv_index(PARSED_TEXT_DIR)
    tres_texts = load_tres_text_set(PARSED_TEXT_DIR)
    gd_texts = load_gd_text_set(PARSED_TEXT_DIR)
    tscn_records = sum(len(v) for v in tsv_index.values())
    print(f"Parse: tscn uid={len(tsv_index)} (records={tscn_records}), "
          f"tres={len(tres_texts)}, gd={len(gd_texts)}")

    all_issues: list[Issue] = []
    for locale in locales:
        local = check_locale_against_parse(locale, tsv_index, tres_texts, gd_texts)
        if not local:
            continue
        print()
        print(f"=== {locale} ===")
        all_issues.extend(local)
        _summarize(all_issues, locale)

    print()
    print(f"=== Grand Total ===")
    print(f"  WHITESPACE_MISMATCH: {len(all_issues)}")
    if all_issues:
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
