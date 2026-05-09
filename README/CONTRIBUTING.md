# Contributing to Trans To Vostok

Thank you for your interest in contributing to Trans To Vostok.

> **Note**: This document currently covers only the basic "how to be
> credited" flow. Detailed contribution guidelines (style, PR process,
> review checklist, license agreement, etc.) will be added later.

---

## How to be credited

Your name is added to `AUTHORS.md` (and `Translation_Credit.md` for the
locale you contributed to) **automatically** on the next build. Do NOT
edit `AUTHORS.md` directly — the Translators section is regenerated on
every build, and any direct edits there will be overwritten.

To be credited, edit the appropriate xlsx file:

### As a translator (text)

Edit `Trans To Vostok/<locale>/Translation.xlsx` → **MetaData** sheet:

| Role         | Field in MetaData          |
| ------------ | -------------------------- |
| Lead         | `Translator`               |
| Contributor  | `Contributor (Translate)`  |

For multiple names in one cell, separate by **line breaks** (`Alt+Enter`
inside the cell in Excel).

### As a texture / image worker

Edit `Trans To Vostok/<locale>/Texture.xlsx`:

| Role           | Column in any sheet  |
| -------------- | -------------------- |
| Primary rework | `Reworked by`        |
| Secondary help | `Contributors`       |

Same rule for multiple names: line break (`Alt+Enter`) inside the cell.

### As a code contributor (Python tools / GDScript)

There is no programmatic data source for code contributions, so this is
the only category that requires editing `AUTHORS.md` directly. Add an
entry under the **Code Contributors** section using this format:

```
- **Name (or handle)** <email or contact>
  - Brief description of contribution
```

This section sits OUTSIDE the auto-generated markers, so it is
preserved across builds.

---

## After editing

Run the build to regenerate the credit files:

```
python tools/build_mod_package.py
```

Or just commit the xlsx changes — the maintainer will run the build at
release time.

---

## Adding a new language with DeepL machine translation

This mod uses **DeepL API** to bootstrap translations for new languages.
The pipeline reads English source text from existing xlsx files,
deduplicates, sends only unique texts to DeepL, and writes results back
to the new locale's xlsx files.

### Prerequisites

1. A DeepL API key (Free or Pro). Save it as a single-line file at
   `tools/.deepl_key` (gitignored), or set the `DEEPL_AUTH_KEY` env var.
2. Python deps installed: `pip install -r tools/requirements.txt`
3. Knowledge of the target language's DeepL code
   (e.g., `FR` for French, `JA` for Japanese, `PT-BR` for Brazilian
   Portuguese — see https://developers.deepl.com/docs/getting-started/supported-languages).

### Step 1 — Create the locale folder

Copy from `Template/`:

```powershell
$loc = "French"   # change to your target locale folder name
mkdir "Trans To Vostok/$loc"
cp "Trans To Vostok/Template/Translation.xlsx" "Trans To Vostok/$loc/"
cp "Trans To Vostok/Template/Texture.xlsx"     "Trans To Vostok/$loc/"
cp "Trans To Vostok/Template/Glossary.xlsx"    "Trans To Vostok/$loc/"
```

The Template should have **empty `translation` columns** so DeepL has
work to do. If your Template inherited translations from another locale,
clear those columns first (see "Glossary inheritance caveat" below).

### Step 2 — Run the translation pipeline

A single command runs export -> DeepL -> import for the locale:

```
python tools/machine_translation_deepl.py French
```

Optional flags:

| Flag | Purpose |
| --- | --- |
| `--deepl-lang FR` | Override the auto-mapped DeepL code (e.g., for `BrazilianPortuguese` -> `PT-BR`) |
| `--limit 10` | Translate only the first 10 unique texts (smoke test before full run) |
| `--dry-run` | Run export + show what would be translated; skip API call and import |

Internally the orchestrator chains three steps in `tools/utils/`:

1. **`export_unique_text.py French`** — scans `Translation.xlsx`,
   `Texture.xlsx`, `Glossary.xlsx`. Filters skip ignore/pattern/
   untranslatable rows and rows whose translation column is already
   filled. Deduplicates by exact text. Writes `.tmp/unique_text/French/unique.tsv`.
2. **`translate_with_deepl.py FR --source French`** — sends each unique
   text to DeepL with placeholder protection (`{name}` -> `<x>{name}</x>`)
   and XML-escape (`&`/`<`/`>`). Resume is text-keyed, so re-running
   the pipeline only translates newly-discovered or previously-failed
   texts. Output: `.tmp/unique_text/French/translated_FR.tsv`.
3. **`import_translations.py French`** — writes translations back to
   the 3 xlsx files in `Trans To Vostok/French/` using the per-row
   logic below.

If you prefer to run the steps manually (e.g., to insert an LLM review
between translate and import), each script is invokable on its own —
the orchestrator just chains them.

#### Per-row import logic

| Row condition | Action |
| --- | --- |
| translation already non-empty | skip (preserves human edits / curated entries) |
| `untranslatable=1` | copy source text to translation; do NOT touch Comments |
| `method=pattern` | skip (regex source can't be machine-translated) |
| `method=ignore` + text found in DeepL results | use that translation; append `#Machine Translated` to Comments |
| `method=ignore` + text NOT in DeepL results | fallback: copy source text (e.g., "Road to Vostok" game title) |
| regular row + text found | write translation; append `#Machine Translated` to Comments |

### Step 3 — Add the locale to `locale.json`

Edit `Trans To Vostok/locale.json` to register the new language:

```json
{
  "locale": "French",
  "dir": "French",
  "display": "Français",
  "message": "Sélectionnez une langue",
  "compatible": "Mode compatible (à utiliser si certains textes ne sont pas traduits)",
  "enabled": true
}
```

### Step 4 — Build and verify

```
python tools/build_mod_package.py
```

This regenerates everything for all locales:
- runtime TSVs (loaded by translator.gd in-game)
- `Texture_Attribution.md` (per locale)
- `Translation_Credit.md` (per locale)
- `AUTHORS.md` (auto-section, all locales)
- `Translations/<locale>/<category>/*.tsv` (git diff visibility)
- Final `Trans To Vostok.zip`

Verify:
- `Trans To Vostok/French/Translation.xlsx` — translations populated
- `Trans To Vostok/French/runtime_tsv/` — runtime files generated
- The mod zip contains the new locale

### Quirks & common issues

**Glossary inheritance caveat.** If the Template was previously copied
from a translated locale (e.g., Korean), the Glossary's translation
column may still contain that other language's text. The pipeline's
"already translated" filter will skip those rows. To get fresh DeepL
translations:
- Clear the translation column in `<NewLocale>/Glossary.xlsx`, OR
- (Better) keep the Template's translation columns empty so all new
  locales start clean.

**DeepL XML parse errors.** Texts with `&`, `<`, or `>` were causing
batch failures (`Tag handling parsing failed`). The current tool
auto-escapes these to `&amp;` / `&lt;` / `&gt;` before sending and
reverses on the way back.

**Resume on failure.** If the DeepL call partially fails (network,
quota, etc.), re-run `translate_with_deepl.py FR --source French`. It
loads existing successes from `translated_FR.tsv` (keyed by source
text, robust to unique_id renumbering) and retries error rows.

**Free quota.** DeepL Free is 500K chars/month. Our full Korean source
is about 62K chars unique, so you can afford ~8 more languages per
month, plus retries.

**Quality review.** DeepL output is a starting point, not final. After
import, review:
- Proper nouns / game terms (Vostok, Outpost, etc.) — should match the
  intended convention
- UI strings (short, contextual) — DeepL sometimes mistranslates without
  context
- The Glossary specifically — it is meant to be **human-curated**, so
  treat the DeepL output as a draft and edit as needed.

---

## (Reserved for future expansion)

The following areas of the contribution guide will be filled in later:

- Project overview and scope
- Code style guidelines
- Pull request checklist
- Translation style / glossary policy
- License agreement for contributions
- Review process

For now, please open an issue if you have any questions.
