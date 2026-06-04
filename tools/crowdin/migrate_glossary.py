"""One-shot migration: Translations/<locale>/Glossary/Main.tsv -> Crowdin native Glossary.

Reads each locale's Glossary TSV and adds terms to the Crowdin glossary
already assigned to the project (project.assignedGlossaries[0]).

Each Template row becomes one "concept" containing:
  - English source term (from Template's `text` column)
  - One translation per locale (from <locale>'s `translation` column)

Column mapping (TSV -> Crowdin):
  text             -> term text
  translation      -> per-language term text
  DESCRIPTION      -> term description (English term only; translations inherit)
  Category /       -> joined into `note`
    Sub-Category /
    Class
  untranslatable=1 -> translation forced = source; note prefixed with "(do not translate)"
  max_length       -> dropped (not supported)
  Comments         -> appended to note

Usage:
    python tools/crowdin/migrate_glossary.py --dry-run                  # print plan, no calls
    python tools/crowdin/migrate_glossary.py --limit 5                  # first 5 rows only
    python tools/crowdin/migrate_glossary.py --clear                    # wipe glossary first
    python tools/crowdin/migrate_glossary.py --clear --limit 5          # wipe + spot test
    python tools/crowdin/migrate_glossary.py --locales Korean,French    # subset

Safe to re-run: pair `--clear` with the run to avoid duplicates.
"""
import argparse
import csv
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
REPO = TOOLS_DIR.parent

sys.path.insert(0, str(TOOLS_DIR))
from crowdin.api_client import make_client
from helper.helper_locale_config import load_crowdin_locale_map, default_source_locale

GLOSSARY_DIR_NAME = "Glossary"
SHEET = "Main.tsv"


def load_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        rows = list(reader)
    if not rows:
        return [], []
    header = rows[0]
    out: list[dict[str, str]] = []
    for r in rows[1:]:
        while len(r) < len(header):
            r.append("")
        out.append(dict(zip(header, r)))
    return header, out


def build_note(row: dict[str, str], untranslatable: bool) -> str:
    """Compose a single `note` string from our metadata columns."""
    parts: list[str] = []
    if untranslatable:
        parts.append("(do not translate)")
    cls = "/".join(
        v for v in (row.get("Category", ""), row.get("Sub-Category", ""), row.get("Class", ""))
        if v.strip()
    )
    if cls:
        parts.append(f"[{cls}]")
    comments = row.get("Comments", "").strip()
    if comments:
        parts.append(comments)
    return " ".join(parts)


def collect_rows(locales: list[str]) -> list[dict]:
    """Build a list of {text, description, note, untranslatable, translations: {locale: tx}}."""
    template_path = REPO / "Translations" / "Template" / GLOSSARY_DIR_NAME / SHEET
    if not template_path.exists():
        raise SystemExit(f"[ERROR] Missing template: {template_path}")
    _, template_rows = load_tsv(template_path)

    locale_rows: dict[str, list[dict[str, str]]] = {}
    for loc in locales:
        p = REPO / "Translations" / loc / GLOSSARY_DIR_NAME / SHEET
        if not p.exists():
            print(f"  [WARN] Skip locale {loc}: missing {p}")
            continue
        _, locale_rows[loc] = load_tsv(p)
        if len(locale_rows[loc]) != len(template_rows):
            print(f"  [WARN] {loc} row count {len(locale_rows[loc])} != Template {len(template_rows)}")

    out: list[dict] = []
    for i, t in enumerate(template_rows):
        text = t.get("text", "").strip()
        if not text:
            continue
        untranslatable = t.get("untranslatable", "").strip() == "1"
        description = t.get("DESCRIPTION", "").strip()
        note = build_note(t, untranslatable)

        translations: dict[str, str] = {}
        for loc, lrows in locale_rows.items():
            if i >= len(lrows):
                continue
            tx = lrows[i].get("translation", "").strip()
            if untranslatable:
                # Force translation = source for "do not translate" terms.
                tx = text
            if tx:
                translations[loc] = tx
        out.append({
            "text": text,
            "description": description or None,
            "note": note or None,
            "untranslatable": untranslatable,
            "translations": translations,
        })
    return out


def get_glossary_id(client, project_id: int) -> int:
    proj = client.projects.get_project(projectId=project_id)
    assigned = proj["data"].get("assignedGlossaries") or []
    if not assigned:
        raise SystemExit(
            "[ERROR] No glossary assigned to project. "
            "Create one in Crowdin web UI (Resources > Glossaries) first, "
            "or assign an existing one."
        )
    return assigned[0]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen, no API calls (except listing).")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only the first N concepts (0 = all).")
    parser.add_argument("--clear", action="store_true",
                        help="Wipe glossary before uploading. Use to retry cleanly.")
    parser.add_argument("--locales", type=str, default="",
                        help="Comma-separated locales (default: all active from locale.json).")
    args = parser.parse_args(argv[1:])

    locale_map = load_crowdin_locale_map()
    if args.locales:
        wanted = [s.strip() for s in args.locales.split(",") if s.strip()]
        for w in wanted:
            if w not in locale_map:
                print(f"[ERROR] Unknown locale: {w}. Known: {list(locale_map)}", file=sys.stderr)
                return 1
        locales = wanted
    else:
        locales = list(locale_map)

    print(f"Source locale (English):  Template")
    print(f"Target locales:           {', '.join(locales)} -> "
          f"{[locale_map[l] for l in locales]}")
    print()

    print("Loading TSVs...")
    rows = collect_rows(locales)
    print(f"  {len(rows)} concepts (non-empty text)")
    if args.limit:
        rows = rows[: args.limit]
        print(f"  --limit {args.limit} -> {len(rows)} concepts")

    print()
    client, project_id, _ = make_client()
    glossary_id = get_glossary_id(client, project_id)
    print(f"Project glossary id: {glossary_id}")

    if args.clear and not args.dry_run:
        print(f"Clearing glossary {glossary_id}...")
        client.glossaries.clear_glossary(glossaryId=glossary_id)
        print("  cleared")
    elif args.clear:
        print("[dry-run] would clear glossary")

    stats = {"concepts": 0, "en_terms": 0, "tx_terms": 0, "errors": []}
    for i, r in enumerate(rows, 1):
        en_text = r["text"]
        prefix = f"[{i:3d}/{len(rows)}] {en_text[:40]:40s}"
        if args.dry_run:
            tx_summary = ", ".join(f"{l}={r['translations'].get(l, '-')[:20]!r}" for l in locales)
            print(f"{prefix}  EN | {tx_summary}")
            stats["concepts"] += 1
            stats["en_terms"] += 1
            stats["tx_terms"] += sum(1 for v in r["translations"].values() if v)
            continue

        try:
            kwargs = {
                "glossaryId": glossary_id,
                "languageId": "en",
                "text": en_text,
            }
            if r["description"]:
                kwargs["description"] = r["description"]
            if r["note"]:
                kwargs["note"] = r["note"]
            en_resp = client.glossaries.add_term(**kwargs)
            concept_id = en_resp["data"]["conceptId"]
            stats["concepts"] += 1
            stats["en_terms"] += 1
        except Exception as e:
            stats["errors"].append((en_text, "en", str(e)))
            print(f"{prefix}  [EN ERR] {e}")
            continue

        tx_added = 0
        for loc, tx in r["translations"].items():
            try:
                client.glossaries.add_term(
                    glossaryId=glossary_id,
                    languageId=locale_map[loc],
                    text=tx,
                    conceptId=concept_id,
                )
                tx_added += 1
                stats["tx_terms"] += 1
            except Exception as e:
                stats["errors"].append((en_text, loc, str(e)))
                print(f"{prefix}  [{loc} ERR] {e}")
        print(f"{prefix}  conceptId={concept_id}  +{tx_added} tx")

    print()
    print("=== Done ===")
    print(f"  concepts created    : {stats['concepts']}")
    print(f"  EN terms added      : {stats['en_terms']}")
    print(f"  translation terms   : {stats['tx_terms']}")
    print(f"  errors              : {len(stats['errors'])}")
    if stats["errors"]:
        for text, loc, msg in stats["errors"][:10]:
            print(f"    {loc:6s} {text[:40]!r}: {msg}")
    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
