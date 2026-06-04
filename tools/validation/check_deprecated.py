"""Find rows in the canonical TSV that no longer match the parsed game data.

A DEPRECATED row claims a specific game location (via filename + filetype)
but the parser can't find a matching node/text in the recovered PCK.
Typical cause: a game update renamed/removed the node or changed the
source text. The complementary check — parse entries without a row — is
covered by check_missing.py.

Translation scope:
  Only rows where BOTH `filename` and `filetype` are set are considered;
  manual entries (empty filetype) cannot be cross-checked against the
  parser and are silently skipped. Recognized filetypes: tscn, scn, tres,
  gd.

  Method (`ignore`, `pattern`, `substr`, ...) and `untranslatable=1` are
  NOT filtered. The canonical TSV doubles as a catalog of game text —
  any row that claims a specific game location should still be valid
  even if it's marked "don't translate" or matched globally. A stale
  ignore row is exactly the kind of catalog drift this check exists to
  surface.

Texture scope:
  Every row has File Directory + File Name by schema, so all rows are
  checked; the join is against parsed_textures/textures.tsv.

Confidence (informational; helps triage):
  HIGH    tscn / scn  — unique_id-based matching, parser reliable
  HIGH    Texture     — PCK extraction is deterministic
  MEDIUM  tres        — text-based matching, parser reliable
  LOW     gd          — heuristic extraction, false miss expected

Usage:
  python tools/validation/check_deprecated.py Template
  python tools/validation/check_deprecated.py Korean
  python tools/validation/check_deprecated.py all
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
PARSED_TEXTURES_TSV = REPO / ".tmp" / "parsed_textures" / "textures.tsv"
LOCALE_JSON = REPO / "src" / "locale.json"
TEMPLATE_LOCALE = "Template"

SCENE_FILETYPES = {"tscn", "scn"}
KNOWN_FILETYPES = SCENE_FILETYPES | {"tres", "gd"}
CONFIDENCE = {"tscn": "HIGH", "scn": "HIGH", "tres": "MEDIUM", "gd": "LOW"}
SAMPLE_LIMIT = 8

sys.path.insert(0, str(REPO / "tools"))
from utils.helper_translation_common import (
    load_tsv_index,
    load_tres_text_set,
    load_gd_text_set,
)


class Issue(NamedTuple):
    locale: str
    category: str     # Translation / Texture
    filetype: str     # tscn / scn / tres / gd / texture
    confidence: str   # HIGH / MEDIUM / LOW
    sheet: str
    row: int
    detail: str


def _preview(s: str, n: int = 40) -> str:
    p = (s or "").replace("\n", " ⏎ ")
    return p[:n] + ("..." if len(p) > n else "")


def _norm_path_key(file_dir: str, file_name: str) -> str:
    fd = (file_dir or "").strip().replace("/", "\\").strip("\\")
    fn = (file_name or "").strip()
    if fn:
        return (fd + "\\" + fn) if fd else fn
    return fd


# -----------------------------------------------------------------------------
# Translation
# -----------------------------------------------------------------------------

def check_translation(locale: str, tsv_index: dict, tres_texts: set,
                      gd_texts: set) -> list[Issue]:
    deprecated: list[Issue] = []

    tr_dir = TRANSLATIONS / locale / "tsv" / "Translation"
    if not tr_dir.exists():
        return deprecated

    for tsv in sorted(tr_dir.glob("*.tsv")):
        if tsv.name.startswith("_"):
            continue
        with open(tsv, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row_num, row in enumerate(reader, start=2):
                filename = (row.get("filename") or "").strip()
                filetype = (row.get("filetype") or "").strip()
                if not filename or filetype not in KNOWN_FILETYPES:
                    continue

                text = row.get("text", "") or ""

                if filetype in SCENE_FILETYPES:
                    uid = (row.get("unique_id") or "").strip()
                    if not uid:
                        continue
                    candidates = tsv_index.get(uid)
                    if candidates is None or not any(c["text"] == text for c in candidates):
                        deprecated.append(Issue(
                            locale, "Translation", filetype,
                            CONFIDENCE[filetype], tsv.stem, row_num,
                            f"uid={uid} text={_preview(text)!r}",
                        ))
                elif filetype == "tres":
                    if text and text not in tres_texts:
                        deprecated.append(Issue(
                            locale, "Translation", filetype,
                            CONFIDENCE[filetype], tsv.stem, row_num,
                            f"text={_preview(text)!r}",
                        ))
                elif filetype == "gd":
                    if text and text not in gd_texts:
                        deprecated.append(Issue(
                            locale, "Translation", filetype,
                            CONFIDENCE[filetype], tsv.stem, row_num,
                            f"text={_preview(text)!r}",
                        ))

    return deprecated


# -----------------------------------------------------------------------------
# Texture
# -----------------------------------------------------------------------------

def load_pck_catalog() -> set[str]:
    keys: set[str] = set()
    if not PARSED_TEXTURES_TSV.exists():
        return keys
    with open(PARSED_TEXTURES_TSV, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            keys.add(_norm_path_key(row["File Directory"], row["File Name"]))
    return keys


def check_texture(locale: str, pck: set[str]) -> list[Issue]:
    deprecated: list[Issue] = []

    tex_dir = TRANSLATIONS / locale / "tsv" / "Texture"
    if not tex_dir.exists():
        return deprecated

    for tsv in sorted(tex_dir.glob("*.tsv")):
        if tsv.name.startswith("_"):
            continue
        with open(tsv, encoding="utf-8", newline="") as f:
            for row_num, row in enumerate(csv.DictReader(f, delimiter="\t"), start=2):
                key = _norm_path_key(row.get("File Directory", ""),
                                     row.get("File Name", ""))
                if not key:
                    continue
                if key not in pck:
                    deprecated.append(Issue(
                        locale, "Texture", "texture",
                        "HIGH", tsv.stem, row_num, f"path={key}",
                    ))

    return deprecated


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------

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
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for i in subset:
        counts[(i.category, i.confidence)] += 1
    print(f"  DEPRECATED: {len(subset)}")
    for (cat, conf), n in sorted(counts.items()):
        print(f"    [{conf:6s}] {cat:12s} {n}")
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    samples = sorted(subset, key=lambda i: (order.get(i.confidence, 9), i.sheet, i.row))[:SAMPLE_LIMIT]
    for i in samples:
        loc = f"{i.sheet}:r{i.row}" if i.row else i.sheet
        print(f"      [{i.confidence:6s}] {i.category:11s} {i.filetype:7s} {loc:22s} {i.detail}")
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

    have_translation_parse = PARSED_TEXT_DIR.exists()
    have_texture_parse = PARSED_TEXTURES_TSV.exists()
    if not have_translation_parse:
        print(f"[WARN] parsed_text/ not found at {PARSED_TEXT_DIR.relative_to(REPO)} "
              f"— Translation checks skipped. Run tools/parse_translatables.py first.")
    if not have_texture_parse:
        print(f"[WARN] parsed_textures/textures.tsv not found "
              f"— Texture checks skipped. Run tools/utils/parse_textures.py first.")
    if not (have_translation_parse or have_texture_parse):
        return 1

    # Load parse references once
    tsv_index = tres_texts = gd_texts = pck = None
    if have_translation_parse:
        tsv_index = load_tsv_index(PARSED_TEXT_DIR)
        tres_texts = load_tres_text_set(PARSED_TEXT_DIR)
        gd_texts = load_gd_text_set(PARSED_TEXT_DIR)
        tscn_records = sum(len(v) for v in tsv_index.values())
        print(f"Parse: tscn uid={len(tsv_index)} (records={tscn_records}), "
              f"tres={len(tres_texts)}, gd={len(gd_texts)}")
    if have_texture_parse:
        pck = load_pck_catalog()
        print(f"Parse: textures={len(pck)}")

    all_issues: list[Issue] = []
    for locale in locales:
        local: list[Issue] = []
        if have_translation_parse:
            local.extend(check_translation(locale, tsv_index, tres_texts, gd_texts))
        if have_texture_parse:
            local.extend(check_texture(locale, pck))
        if not local:
            continue
        print()
        print(f"=== {locale} ===")
        all_issues.extend(local)
        _summarize(all_issues, locale)

    print()
    print(f"=== Grand Total ===")
    print(f"  DEPRECATED: {len(all_issues)}")
    if any(i.confidence == "HIGH" for i in all_issues):
        return 1
    if all_issues:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
