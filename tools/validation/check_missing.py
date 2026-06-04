"""Find parse entries that have no row in the canonical TSV (catalog gap).

Counterpart to check_deprecated.py. The two tools share the same scope
(`filename` and `filetype` present on the xlsx side) but probe opposite
directions:

  check_deprecated.py  — row in canonical TSV but absent from parse
  check_missing.py     — parse entry present but absent from canonical TSV

A MISSING result usually means the game update added new text (or the
parser extracts something the xlsx hasn't catalogued yet).

Translation scope:
  Parse entries from .tmp/parsed_text/ (tscn/scn/tres/gd). For each parse
  entry, we look it up in the xlsx-side index built from canonical TSVs;
  the index includes every row regardless of method or untranslatable —
  the xlsx doubles as a catalog of game text. A row counts as covering
  a parse entry as long as it has filename+filetype set and the matching
  fields (unique_id+text for tscn, text for tres/gd) line up.

Texture scope:
  Parse entries from .tmp/parsed_textures/textures.tsv. Each PCK PNG
  must have a row in some Texture TSV (matching by File Directory +
  File Name). Texture rows always have these by schema, so no extra
  filter applies.

Confidence (informational):
  HIGH    tscn / scn     unique_id-based matching, parser reliable
  HIGH    Texture        PCK extraction is deterministic
  MEDIUM  tres           text-based matching
  LOW     gd             heuristic extraction; gd false positives expected

Usage:
  python tools/validation/check_missing.py Template
  python tools/validation/check_missing.py Korean
  python tools/validation/check_missing.py all
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
    category: str    # Translation / Texture
    filetype: str    # tscn / scn / tres / gd / texture
    confidence: str  # HIGH / MEDIUM / LOW
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

def _build_translation_xlsx_index(locale: str) -> tuple[set, set, set]:
    """Build xlsx-side indexes for MISSING lookup.

    Returns (xlsx_tscn_keys, xlsx_tres_texts, xlsx_gd_texts).
    Rows are included regardless of method/untranslatable — the xlsx
    plays a catalog role here, so the *existence* of any row covering
    a parse entry counts.
    """
    xlsx_tscn: set[tuple[str, str]] = set()
    xlsx_tres: set[str] = set()
    xlsx_gd: set[str] = set()

    tr_dir = TRANSLATIONS / locale / "tsv" / "Translation"
    if not tr_dir.exists():
        return xlsx_tscn, xlsx_tres, xlsx_gd

    for tsv in sorted(tr_dir.glob("*.tsv")):
        if tsv.name.startswith("_"):
            continue
        with open(tsv, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                filename = (row.get("filename") or "").strip()
                filetype = (row.get("filetype") or "").strip()
                if not filename or filetype not in KNOWN_FILETYPES:
                    continue
                text = row.get("text", "") or ""
                if filetype in SCENE_FILETYPES:
                    uid = (row.get("unique_id") or "").strip()
                    if uid:
                        xlsx_tscn.add((uid, text))
                elif filetype == "tres" and text:
                    xlsx_tres.add(text)
                elif filetype == "gd" and text:
                    xlsx_gd.add(text)
    return xlsx_tscn, xlsx_tres, xlsx_gd


def check_translation(locale: str, tsv_index: dict, tres_texts: set,
                      gd_texts: set) -> list[Issue]:
    issues: list[Issue] = []
    xlsx_tscn, xlsx_tres, xlsx_gd = _build_translation_xlsx_index(locale)

    # tscn / scn
    for uid, candidates in tsv_index.items():
        for c in candidates:
            if (uid, c["text"]) not in xlsx_tscn:
                ft = c.get("filetype") or "tscn"
                issues.append(Issue(
                    locale, "Translation", ft, CONFIDENCE.get(ft, "HIGH"),
                    f"uid={uid} text={_preview(c['text'])!r}",
                ))
    # tres
    for text in tres_texts:
        if text not in xlsx_tres:
            issues.append(Issue(
                locale, "Translation", "tres", CONFIDENCE["tres"],
                f"text={_preview(text)!r}",
            ))
    # gd
    for text in gd_texts:
        if text not in xlsx_gd:
            issues.append(Issue(
                locale, "Translation", "gd", CONFIDENCE["gd"],
                f"text={_preview(text)!r}",
            ))

    return issues


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


def _build_texture_xlsx_keys(locale: str) -> set[str]:
    keys: set[str] = set()
    tex_dir = TRANSLATIONS / locale / "tsv" / "Texture"
    if not tex_dir.exists():
        return keys
    for tsv in sorted(tex_dir.glob("*.tsv")):
        if tsv.name.startswith("_"):
            continue
        with open(tsv, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                key = _norm_path_key(row.get("File Directory", ""),
                                     row.get("File Name", ""))
                if key:
                    keys.add(key)
    return keys


def check_texture(locale: str, pck: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    xlsx_keys = _build_texture_xlsx_keys(locale)
    for key in pck:
        if key not in xlsx_keys:
            issues.append(Issue(
                locale, "Texture", "texture", "HIGH", f"path={key}",
            ))
    return issues


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
    print(f"  MISSING: {len(subset)}")
    for (cat, conf), n in sorted(counts.items()):
        print(f"    [{conf:6s}] {cat:12s} {n}")
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    samples = sorted(subset, key=lambda i: (order.get(i.confidence, 9), i.detail))[:SAMPLE_LIMIT]
    for i in samples:
        print(f"      [{i.confidence:6s}] {i.category:11s} {i.filetype:7s} {i.detail}")
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
        print(f"[WARN] parsed_text/ not found — Translation checks skipped. "
              f"Run tools/parse_translatables.py first.")
    if not have_texture_parse:
        print(f"[WARN] parsed_textures/textures.tsv not found — Texture checks "
              f"skipped. Run tools/utils/parse_textures.py first.")
    if not (have_translation_parse or have_texture_parse):
        return 1

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
        local_issues: list[Issue] = []
        if have_translation_parse:
            local_issues.extend(check_translation(locale, tsv_index, tres_texts, gd_texts))
        if have_texture_parse:
            local_issues.extend(check_texture(locale, pck))
        if not local_issues:
            continue
        print()
        print(f"=== {locale} ===")
        all_issues.extend(local_issues)
        _summarize(all_issues, locale)

    print()
    print(f"=== Grand Total ===")
    print(f"  MISSING: {len(all_issues)}")
    if any(i.confidence == "HIGH" for i in all_issues):
        return 1
    if all_issues:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
