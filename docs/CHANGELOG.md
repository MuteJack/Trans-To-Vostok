# Changelog — Trans To Vostok

All notable changes to this mod will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.6.0] — 2026-05-31 (Texture Blend Method + Sign / Structure Textures)

This release introduces a new **`blend` texture method** that composites a
mod-side overlay PNG on top of the game's original texture at runtime,
preserving the original's PBR maps (normal, weathering, etc.) while replacing
only the translated text pixels. Sixteen blend overlays (signs, posters,
canteen sign, inventory icon, etc.) are shipped for Korean; other active
locales get the schema rows but empty translations, ready for Crowdin
contributors. The Texture canonical TSV gains a `method` column and is
reorganized into four sheets (Tutorial / UI / Signs / Structures). Several
new build / sync tools land alongside.

### Added

- **`blend` texture method** — alternative to existing `replace`. Mod ships
  a transparent-background PNG containing only the translated text pixels;
  at runtime, `texture_loader.gd` reads the original texture's Image,
  alpha-blends the overlay on top via `Image.blend_rect`, generates mipmaps
  to keep distant LOD readable, and assigns the composite back to the
  material's albedo. Two benefits over `replace`: (1) **copyright** — mod
  ships only original (mod-author) work, never a derivative of the game's
  texture pixels; (2) **less authoring per sign** — only the text region
  needs work, the original sign's PBR maps (normal, roughness, weathering)
  and lighting integration carry through automatically without manual
  recreation.
- **Korean blend textures (16)** at `Trans To Vostok/Korean/textures/`:
  - `Sign_Mines`, `Sign_Public_Road`, `Sign_VT7` (+ `Frame_Highway_Sign`),
    `Sign_Border_Zone` (4 variants), `Sign_School`, `Sign_Speedbump`,
    `Sign_Village_Crossroads`
  - `Canteen_Details` (translates KASSA / SOTILASKOTI on the
    Finnish-military-canteen building)
  - `Board_Message`, `Booth_Ticket`, `Box_Electric`, `Box_Transformer`
  - `Icon_Sign_Border_Zone` (inventory icon)
- **`method` column on Texture canonical TSV** — values: `replace`
  (substitute the whole texture) or `blend` (composite overlay onto
  original). Inserted between `Type` and `Text`. Existing Tutorial Billboards
  + WorldMap stay as `replace`.
- **Two new Texture sheets**: `Signs.tsv` (13 rows — road signs) and
  `Structures.tsv` (4 rows — building / equipment textures with text).
  All active locales now have 4 Texture sheets: Tutorial / UI / Signs /
  Structures.
- **`tools/utils/build_texture_meta.py`** — emits
  `Trans To Vostok/<locale>/texture_meta.json` mapping each translated
  texture rel-path to its method (`replace` / `blend`). Consumed at runtime
  by `texture_loader.gd` for per-texture routing.
- **`tools/push_source_to_crowdin.py`** — uploads Template's source TSVs to
  Crowdin via the SDK. Resolves the long-standing TODO: previously, new
  source files (Signs / Structures) had to be pushed manually via the Java
  CLI. The new tool reads `crowdin.yml` to apply the correct
  `exportPattern` to each new file (mirrors `/Crowdin_Mirror/translations/
  %locale%/<category>/%original_file_name%`).
- **`tools/utils/sync_texture_schema.py`** — propagates Template's
  `Texture/*.tsv` structure (sheets + rows) to all active locales,
  preserving each locale's existing `Translation` / `Reworked by` /
  `Contributors` / `Attribution`. Use after editing Template to keep all
  locales in lockstep.
- **`tools/rebuild_xlsx.py all`** — rebuild xlsx for every locale under
  `Translations/` in one command.
- **`tools/push_to_crowdin.py --base <rev>`** — diff against an arbitrary
  git revision (commit / tag / `HEAD~N`) instead of `HEAD`. Lets you push
  rows that are already committed (e.g., first push after a fresh source
  file was added to Crowdin via `push_source_to_crowdin.py`).

### Changed

- **`texture_loader.gd`** — added `_load_texture_meta()`, `_composite_blend()`,
  and a per-texture routing branch in `_try_bind_texture_property` /
  `_try_bind_shader_material`. `_blend_cache` keeps composites in memory so
  multiple instances of the same sign share a single blended ImageTexture.
- **`tools/utils/rebuild_texture_xlsx.py`** — `method` column gets a
  conditional-formatting rule (blue for `replace`; `blend` left default).
  Sample rendering follows the existing Translation TSV CF style.
- **`tools/build_mod_package.py`** — packaging step now calls
  `build_texture_meta.py` per locale and includes `texture_meta.json` in
  the mod zip (step 8 of the packaging loop).
- **`pull_from_crowdin.py` zip download** — switched from blocking
  `urlopen().read()` to chunked streaming with a 120-second timeout and
  per-second progress output. Resolves the prior hang on slow CDN paths.
- **`api_client.py` source-file upload**:
  - Adds `list_directories` / `create_directory` / `_ensure_directory`
    helpers and `add_source_file` / `update_source_file` with the correct
    `importOptions` (snake_case keys: `identifier`, `source_phrase`,
    `translation`, `context`, `labels`, `max_length`).
  - `upload_source_files` reads `crowdin.yml` and applies the matching
    `exportOptions.exportPattern` to each new file (avoids stray
    `<locale_code>/Crowdin_Mirror/source/...` directories on pull).
- **Texture schema sync**: all 8 active locales other than Korean now have
  the full Tutorial / UI / Signs / Structures layout in their canonical TSV
  and xlsx. Translation column empty for new entries — Crowdin contributors
  can pick them up.
- **Japanese — 83 strings refined** (contributor: Nineblood, via Crowdin).
  Pulled into `Translations/Japanese/Translation/*.tsv` via
  `pull_from_crowdin.py Japanese` + `apply_to_repo.py`.

### Fixed

- **Sign_VT7 / Frame_Highway_Sign path duplication** — the in-world
  directional sign uses `Assets/Frame_Highway/Files/TX_Frame_Highway_Sign_AL.png`,
  but the asset is named `Sign_VT7`. Mod now ships the same overlay PNG
  at both paths so the in-game directional sign actually picks up the
  translation.
- **Crowdin pull stray directories** (`mods/Trans To Vostok/de/`,
  `cs/`, `fi/`, …) — caused by newly-uploaded source files lacking an
  `exportPattern`, which defaulted to Crowdin's `<locale>/<source_path>`.
  Fixed by reading `crowdin.yml` patterns on push; the 2 affected files
  (`Signs.tsv`, `Structures.tsv`) had their pattern corrected on Crowdin
  web manually.

Note on LOD handling: the `blend` method generates mipmaps on the
composited Image before creating the ImageTexture. This isn't a fix of
a prior bug (no shipped feature regressed) — it's a required part of
the new path, documented under **Added** above.

### Internal / Tooling

- New tools: `build_texture_meta.py`, `push_source_to_crowdin.py`,
  `sync_texture_schema.py`.
- `push_to_crowdin.py --base <rev>` and `rebuild_xlsx.py all` extend
  existing tools.
- `target_game_version` continues to be tracked in both `mod.txt` and
  `info.json`; bumped target is `0.1.1.3` (no change).
- Documentation: `_sheet_order.txt` schema now includes `Signs` and
  `Structures` across all active locales.

## [0.5.3] — 2026-05-30 (Five New Languages — DeepL Initial Pass)

This release adds **five new locales** as initial DeepL machine-translated
passes (text only; texture translation pending). Locale registry was
retuned: Italian — added briefly during this cycle then dropped because
its initial DeepL pass never completed — was removed entirely, and Russian
was added but disabled (the DeepL Free monthly quota was exhausted
mid-pass; the partial Russian xlsx is preserved in-repo and will resume
on next month's quota reset). `target_game_version` is now also declared
in `mod.txt` (for ModLoader compatibility warnings) alongside the existing
`info.json` value (consumed by the F9 Info tab).

### Added

- **New locales (5)** — each via the standard
  `docs/dev/kr/Add_new_language.md` workflow (Template canonical TSV copy →
  `rebuild_xlsx.py` → DeepL pipeline → `locale.json` registration):
  - **Deutsch** — `display: "Deutsch"`, `message: "Sprache wählen"`.
  - **Español (LatAm)** — `dir: Spanish_LatAm`, DeepL `ES-419`,
    `display: "Español (LatAm)"`, `message: "Seleccionar idioma"`.
  - **日本語** — `display: "日本語"`, `message: "言語を選択"`.
  - **简体中文** — `dir: ChineseSimplified`, DeepL `ZH-HANS`,
    `display: "简体中文"`, `message: "选择语言"`.
  - **繁體中文** — `dir: ChineseTraditional`, DeepL `ZH-HANT`,
    `display: "繁體中文"`, `message: "選擇語言"`.
- **Russian locale (disabled)** — `dir: Russian`, `enabled: false`.
  DeepL pass partially completed (~252/1100 unique strings translated)
  before the Free monthly quota was exhausted. The partial xlsx is kept
  in-repo (`Translations/Russian/Translation.xlsx`) and will be completed
  on next month's quota reset, at which point the locale flips to
  `enabled: true`.
- **`mod.txt[target_game_version]` field** — declared so the value is
  also picked up by ModLoader (`MetroModLoader` etc.) for game-version
  compatibility warnings. `info.json` continues to carry its own
  hand-edited `target_game_version` consumed by the F9 Info tab; both
  should be kept in sync on each game-version bump.

### Changed

- **`substr_mode_label` localized for all new locales** in `locale.json`
  (Deutsch / Español LatAm / 日本語 / 简体中文 / 繁體中文 / Русский).
- **Korean — translation refinements + QA** across Tasks (*의뢰*),
  Tutorial Billboard textures, and miscellaneous UI strings
  (contributor: gap tal).

### Removed

- **Italian locale** — added briefly during this cycle and removed before
  release: the DeepL initial pass produced 0/1100 successful translations
  (Free quota was already exhausted by the time Italian's run began), and
  the locale was dropped entirely rather than shipped as an empty stub.
  All `Translations/Italian/` files and the `locale.json` Italian entry
  were deleted. Will be re-added in a future cycle once DeepL quota or
  community contribution makes initial coverage viable.

### Internal / Tooling

- **Russian `Translation.xlsx` left at partial fill** — `translate_with_deepl.py`
  resume support means a future run picks up at the remaining ~900 untranslated
  unique strings without reprocessing the existing 252.

## [0.5.2] — 2026-05-27 (Crowdin Integration & Doc Restructure)

This release completes the **Crowdin integration overhaul**: the Java
Crowdin CLI is fully replaced by the Python `crowdin-api-client` SDK
across both push and pull paths, the legacy Glossary xlsx workflow is
retired in favor of Crowdin's native Glossary resource, and per-locale
contributor credits move from `Translation.xlsx` MetaData sheets to a
new `Trans To Vostok/<locale>/credits.json` populated automatically
from the Crowdin members + activity reports. The contributor docs are
restructured into a `docs/translator/` / `docs/dev/` split so each
audience sees only their own workflow. Several runtime bugs that
affected Portuguese in particular are fixed.

### Added

- **Crowdin SDK pipeline** — Java CLI dependency removed. `push_to_crowdin.py`
  and `pull_from_crowdin.py` now drive the entire sync via the
  `crowdin-api-client` Python library. No Java install required.
  Token configured via `tools/configs/secrets.json:crowdin_personal_token`
  (gitignored). Required scopes: Projects (Read & Write), Source Files,
  Translations, Glossary (Read & Write).
- **Smart push (HEAD-based diff)** — `push_to_crowdin.py` computes the
  diff against the last git-committed canonical TSV and uploads only
  changed rows. Other contributors' edits to untouched rows are
  preserved. Working tree's `Translations/<locale>/` is no longer
  dirtied by push (xlsx → canonical TSV happens in `.tmp/`).
- **Smart pull (preserve-on-empty)** — `apply_to_repo.py` ignores empty
  translation cells returned by Crowdin so a row that's never been
  translated on Crowdin doesn't blank out an existing local value.
- **Per-locale `credits.json`** at `Trans To Vostok/<locale>/credits.json`
  (committed, packaged in mod zip). Schema:
  ```json
  {
    "translation_updated": "<ISO timestamp>",
    "Translator": {
      "Leader":      [...],   // Crowdin Owner / Manager / Language Coordinator
      "Translator":  [...],   // Crowdin Proofreader
      "Contributor": [...]    // Crowdin Member with translated > 0
    },
    "Texture_reworker": [...]
  }
  ```
  `translation_updated` is the most recent `max(createdAt, updatedAt)`
  across all translations for that language (full pagination scan).
- **`tools/crowdin/get_member_list.py`** (new) — fetches Crowdin members
  + Top Members Report per language, classifies by role + activity,
  writes Translator fields and `translation_updated` to credits.json.
  Preserves `Texture_reworker` across runs. Called by `pull_from_crowdin.py`.
- **`tools/utils/get_texture_credits.py`** (new) — extracts the
  `Reworked by` + `Contributors` columns from `Texture.xlsx` across all
  sheets, dedupes, writes to `credits.json:Texture_reworker`. Called
  per-locale during build.
- **F9 Info tab — per-locale data now reads credits.json directly**.
  `info.json` is no longer the carrier for per-locale fields; it stays
  a project-wide summary (mod_version, build_date, target_game_version,
  lead_developer, code_contributors, acknowledgments).
- **Docs structure overhaul** — `docs/translator/kr/` (Crowdin web or
  local+test) and `docs/dev/kr/` (maintainer / contributor) under a
  unified `docs/` root. New guides: `Translating_using_crowdin.md`,
  `Translating_on_Local.md`, `Pull_from_Crowdin.md`. CHANGELOG /
  CHANGELOG_user / README_USER also moved into `docs/`.
- **`tools/configs/`** — centralized JSON config location for
  `languages.json`, `width.json`, `parse_list_*.json`, and
  `secrets.json` / `secrets_example.json`. All tooling Path constants
  updated accordingly.

### Changed

- **`info.json` schema** — hybrid file (read-modify-write). The
  `target_game_version` field is now hand-edited in `info.json` and
  preserved across regenerations. The `locales` field is removed;
  per-locale data lives in each `<locale>/credits.json` (consumed by
  F9 UI directly).
- **`build_authors.py` / `build_translation_credit.py` / `build_mod_info.py`**
  refactored to read from `credits.json` instead of xlsx. `openpyxl`
  dependency dropped from these three scripts. AUTHORS.md gains a
  "Translator(s)" subsection (Crowdin Proofreader tier).
- **`build_mod_package.py`** — orchestration now calls
  `get_texture_credits.py` per locale before `build_translation_credit.py`
  so credits.json's Texture_reworker is always fresh in the build.
- **Crowdin pull / push require explicit `all` keyword** — bare invocation
  is rejected to prevent accidental mass operations.
- **Documentation tone** — `docs/translator/kr/` and `docs/dev/kr/`
  standardized on Korean formal tone (`~입니다 / ~합니다`); informal
  `~어요 / ~예요` replaced.

### Fixed

- **Portuguese (Brazil) translations were not loading in-game**.
  `translator_ui.gd` was using `locale.json`'s `locale` field as both
  identifier and folder path; Portuguese's `locale="Portuguese"` didn't
  match its actual folder `Portuguese_BR/`. UI now uses `locale.json`'s
  `dir` field for folder lookup, with automatic migration of saved
  settings from the legacy `locale` value.
- **`credits.json` was missing from the packaged mod zip** —
  `build_mod_package.py` packaging step did not include
  `<locale>/credits.json`, so the F9 Info tab fell back to "(unknown)"
  for Translation Updated despite the file existing on disk. Fixed by
  adding a step 7 to the per-locale packaging loop.
- **`pull_from_crowdin.py` mapping Crowdin's BCP-47 locale folders** —
  Crowdin's exported zip uses locale codes like `ko-KR`, `fr-FR`,
  `pt-BR` for folder names. The SDK download path now queries the
  project's `targetLanguages` once and rewrites zip entry paths to the
  canonical folder names (`Korean`, `French`, `Portuguese_BR`) during
  extraction.
- **DeepL pattern-row handling** — pattern rows (`method=pattern` with
  placeholders like `In {str} Days`) are no longer left with empty
  translations after the DeepL import; the import now copies source to
  translation for these rows so the runtime returns the English template
  instead of falling through to substr matching and producing mixed
  output like `In 5 Jours`.
- **`100%` and `100kg` ToolTip rows** marked `untranslatable=1` across
  all locales (proper handling per `untranslatable` semantics: numbers
  and units, not "translator's choice").
- **Branch naming in docs** — every reference to a `main` branch
  corrected to `master` (the actual default branch).

### Removed

- **`Translation.xlsx` MetaData sheet** — fields are now sourced from
  Crowdin (translator credits, translation_updated), `mod.txt`
  (mod_version), or hand-edited `info.json` (target_game_version).
  Canonical `Translations/<locale>/Translation/MetaData.tsv` files and
  the corresponding entry in `_sheet_order.txt` are removed.
- **Glossary xlsx workflow** — `Translations/<locale>/Glossary.xlsx`
  files, `Translations/<locale>/Glossary/` canonical TSV trees,
  `tools/utils/rebuild_glossary_xlsx.py`, the `Glossary` category from
  every tool's `CATEGORIES` constant, `make_glossary_id()` in
  `tools/crowdin/identifier.py`, and the Glossary `files:` entry in
  `crowdin.yml` are all deleted. Glossary terms now live as a Crowdin
  native Glossary resource (terms surface in the Editor's right panel
  during translation). One-shot migration tool kept at
  `tools/crowdin/migrate_glossary.py` for archival reference.
- **`README/0_..._kr.md` through `README/5_..._kr.md`** numbered guide
  series — content migrated to `docs/translator/kr/` and `docs/dev/kr/`
  with audience-appropriate splits. The legacy `README/CONTRIBUTING.md`
  is relocated to repo-root `CONTRIBUTING.md`.
- **`README_Translation.md`** — gdre_tools install instructions are
  already covered in `docs/translator/kr/Setting_Environments.md §1`.
- **`info.json[locales]` field** — per-locale data moved into the
  per-locale `credits.json` files.
- **`tools/utils/set_requirements.py`** (briefly introduced earlier in
  the cycle, then reverted before merge).

### Internal / Tooling

- **`tools/configs/`** consolidates all JSON config files (was scattered
  in `tools/` and repo root). All Python `Path()` constants updated.
- **GD code in `translator_ui.gd`** gains `_load_locale_credits(locale)`,
  `_load_json_dict(path)` helpers, and a `_date_only()` formatter for
  the ISO timestamp display.
- **Crowdin `download_translations()` SDK helper** in
  `tools/crowdin/api_client.py` — build + poll + zip download with
  locale-path remapping in one call.
- **`tools/utils/build_mod_info.py`** simplified — read existing
  `info.json` (for target_game_version preservation), parse mod.txt,
  parse AUTHORS.md sections, write back without `locales` field.

## [0.5.1] — 2026-05-08 (Patch Release)

This release adds **Portuguese (Brazil)** as a new locale (initial DeepL
machine-translated pass, text only — Texture not yet shipped),
introduces an **"Info" tab** in the F9 UI (mod version / build date /
target game version / contributors broken down by role), and reorganizes
the contributor documentation into a numbered Korean guide series under
`README/`. Internal: TSV-canonical xlsx rebuild pipeline replaces
ad-hoc direct xlsx edits; the mod's own F9 UI is now exempted from being
translated by itself.

### Added

- **New locale: Português (Brasil) / `Portuguese_BR`** — initial pass
  via DeepL `PT-BR` (text only; texture translation deferred).
  Generated through the standard `2_Add_new_language_kr.md` workflow:
  Template TSV copy → `rebuild_xlsx.py` → DeepL pipeline → `locale.json`
  registration. `display: "Português (Brasil)"`,
  `message: "Selecione um idioma (Português Brasileiro)"`.

- **F9 UI: "Info" tab** showing mod metadata. Layout follows the
  Whitelist / Addons tabs (HBox left/right split):
  - **Left (Mod Info)**: Mod Version (from `mod.txt`), Built (UTC date
    of last build), Target Game Version (from each locale's
    Translation.xlsx MetaData "Game Version" — Korean preferred,
    falls back to first available), Selected Locale + Translation
    Updated date (per-locale, from MetaData "Translation Updated Date").
  - **Right (Contributors)**: Lead Developer / Code Contributors /
    Acknowledgments (project-wide, from AUTHORS.md sections); then
    Translators / Translation Contributors / Image Reworkers /
    Image Contributors (current locale, from Translation.xlsx
    MetaData and Texture.xlsx columns).
  - Reads `<pkg_root>/info.json` generated at build time. Defensive
    against missing / malformed JSON: `_safe_get_string` /
    `_safe_get_array` / `_safe_get_dict` helpers with `is String/Array
    /Dictionary` type checks fall back to placeholder text. Failure
    in this tab can never propagate to other tabs / runtime.

- **F9 UI excluded from translation**. The Window node sets
  `set_meta("_ttv_skip_translate", true)` on creation; `translator.gd
  ._bind_node()` walks ancestors and skips any subtree under a node
  with that meta. Previously the mod's own UI text could be matched
  by `literal global` / `substr` rules and replaced with target-locale
  output, defeating the purpose.

- **`tools/rebuild_xlsx.py`** + per-category utilities
  (`tools/utils/rebuild_translation_xlsx.py` /
  `rebuild_glossary_xlsx.py` / `rebuild_texture_xlsx.py`).
  TSV → xlsx with current formatting / column widths /
  conditional formatting policies applied. Replaces the previous
  pattern of editing xlsx directly. Critical for new-locale flow
  (Template TSV is canonical → `rebuild_xlsx.py NewLocale` produces
  fresh xlsx ready for DeepL).

- **`tools/utils/build_mod_info.py`** — generates `info.json` consumed
  by the F9 Info tab. Sources: `mod.txt` (mod_version), today (UTC,
  build_date), Translation.xlsx MetaData (target_game_version,
  per-locale translation_updated / translators), Texture.xlsx
  data sheets (per-locale texture_reworkers / contributors),
  AUTHORS.md (lead_developer / code_contributors / acknowledgments).
  Best-effort parser: missing / malformed sources fall back to
  defaults so info.json always has the expected shape. Wired into
  `build_mod_package.py` as step 4.5 (after `build_authors_md`,
  before packaging).

- **`README_USER.md`** — separated user-facing README intended for
  the modworkshop description page (Features / Install / Compat
  mods / Languages / Attribution / Screenshots, English + Korean
  side-by-side). Image links point to GitHub raw URLs so they
  render on external sites. The repo `README.md` is now repo /
  developer-oriented (Quick Start to the README/ guide series,
  repository layout, tools tables, technical structure, license,
  roadmap).

- **Korean contributor guide series** under `README/`:
  - `0_Setting_Environments_kr.md` — Excel / Python / Git / VS Code
    / Fork & Clone setup; warns about not committing to `main`
    directly.
  - `1_unpack_and_decompile_game_kr.md` — gdre_tools setup +
    `parse_translatables.py` for full validation. Marked optional
    since `parsed_text/` absence no longer blocks build.
  - `2_Add_new_language_kr.md` — Template-from-Korean sync →
    `rebuild_xlsx.py Template` → copy to new locale → DeepL →
    `locale.json` → build.
  - `3_How_to_Translate_kr.md` — translator-facing: MetaData credit
    fields, translation column workflow, leading/trailing whitespace
    matching warning, build → in-game verification.
  - `3_How_to_Translate_kr(For Developers).md` — extended: full
    method semantics, 9-tier runtime priority (including substr as
    Tier 9, missing from `build_runtime_tsv.py` header), Godot
    identifier columns, conflict resolution.
  - `4_How_to_Pull_Request_kr.md` — branch hygiene, naming
    conventions (with collision-avoidance note), PR template.
  - `5_How_to_Update_from_MasterBranch_kr.md` — rebase-based
    upstream sync (consistent with "one branch = one contributor"
    policy), xlsx binary conflict resolution via TSV-shadow rebuild.

- **AUTHORS.md `## Acknowledgments`** section — credits **DIO-KAMI**
  for the prior RTV translation mod ([Korean Localization for
  DEMO](https://modworkshop.net/mod/55997)) as inspiration. Placed
  outside the auto-generated marker so `build_authors.py` runs
  preserve it.

### Changed

- **`tools/validate_translation.py`** — `tsv_dir` parameter is now
  `Optional[Path]`. When `None` or missing, `parsed_text`-dependent
  checks (`check_tsv_match` / `check_tres_text` / `check_gd_text`)
  are skipped and the rest (`check_flags` / `check_method_fields` /
  `check_empty_method` / `check_whitespace` / `check_duplicates` /
  `check_duplicates_cross_sheet`) still run. `build_runtime_tsv.py`
  auto-detects `parsed_text/` absence and runs partial validation
  with an informative message; `--ignore` still skips validation
  entirely. External contributors can now build without gdre_tools.

- **`tools/machine_translation_deepl.py`** — `DEFAULT_DEEPL_LANG`
  expanded from 11 to ~50 entries covering all DeepL target
  languages. Variant codes (`EN-GB` / `EN-US`, `PT-BR` / `PT-PT`,
  `ES-419`, `ZH-HANS` / `ZH-HANT`) get both camelCase
  (`EnglishGB`, `BrazilianPortuguese`) and underscore-suffix
  (`English_GB`, `Portuguese_BR`) aliases. `Portuguese_BR` works
  out of the box without `--deepl-lang` now.

- **README.md split** into repo (developer entry point) +
  `README_USER.md` (modworkshop). Repo README now starts with the
  Quick Start guide table linking to `README/0~5_*.md`.

- **`build_mod_package.py`** — `MOD_FILES` extended with `info.json`.
  New step 4.5 calls `build_mod_info.py` after `build_authors_md`
  finalizes AUTHORS.md but before TSV-shadow refresh and packaging.

- **LICENSE.md** — "Currently identified upstream sources include
  (non-exhaustive):" reworded to "For example:" to clarify the MML
  / Copernicus list is illustrative, not a claim of actual use.
  (Verified via `Texture_Attribution.md` content — no MML in any
  shipped texture currently.)

### Fixed

- **Items / Assets(Furniture) SUB** subdivided. Previously rows
  shared a coarse `SUB` value (e.g., `"Armor"` for all Armor items
  / `"Containers"` for all containers); this defeated the visual
  grouping of the rebuilder's group-separator borders. Now `SUB =
  <old_SUB> + filename[filename.rfind('/'):]` for rows with a
  non-empty filename (1,570 / 1,611 in Items; 265 / 267 in
  Assets(Furniture)). Empty-filename rows are skipped (preserve
  category-header semantics).

- **`build_runtime_tsv.py` header comment 9-tier list** — substr
  was missing as Tier 9 in the comment though it exists in the
  runtime priority chain. Documented in the header alongside the
  other 8 tiers.

### Removed

- **Decompile helper scripts purged from git history** via
  `git filter-repo`: `tools/a_decompile_pck.py`,
  `tools/decompile_gdc.bat`, `tools/unpack_and_decompile_pck.bat`,
  `tools/unpack_and_decompile_pck.py`, `tools/set_requirements.py`.

### Internal

- **TSV-canonical workflow established**. Korean is the source of
  truth for row structure; Template TSV is sync'd from Korean
  with quality flags reset to 0 and translations cleared.
  `Translation_TSV/Korean/Translation/Items.tsv` etc. are committed
  as the diff-friendly shadow; xlsx files are rebuilt from TSV via
  `rebuild_xlsx.py`. Sheet-agnostic key index used for cross-sheet
  reorganizations (sync_locale_to_korean tool, in `d:/tmp/` for
  now — to be promoted to `tools/utils/` when stable).

- **`info.json` schema** (consumed by `_build_info_tab`):
  ```
  {
    "mod_version": str,             // mod.txt
    "build_date": str,              // YYYY-MM-DD UTC
    "target_game_version": str,
    "lead_developer": [str, ...],
    "code_contributors": [str, ...],
    "acknowledgments": [str, ...],
    "locales": {
      "<locale>": {
        "translation_updated": str,
        "texture_updated": str,
        "translators": [str, ...],
        "translation_contributors": [str, ...],
        "texture_reworkers": [str, ...],
        "texture_contributors": [str, ...]
      }
    }
  }
  ```

## [0.5.0] — 2026-05-06 (Minor Release)

This release introduces a **mod compatibility addon system** — per-mod
runtime helpers wired into the translation engine, with a new "Addons"
tab in the language UI to toggle them. First addon implements
ImmersiveXP tooltip-prefix handling.

### Added

- **Mod compatibility addon system (`mod_addon.gd`)** — runtime helper
  module invoked from `translator.gd._apply_binding`. Loaded
  dynamically via `load("res://Trans To Vostok/mod_addon.gd")` because
  ModLoader-mounted mods are not registered in Godot's compile-time
  class cache (so `preload` and `class_name` don't work — both must
  be resolved at runtime after the mod's zip is mounted).

  First addon implemented: **ImmersiveXP prefix handling**. Oldman's
  Immersive Overhaul (modworkshop/50811) prepends one of the following
  prefixes to tooltip labels every 10 physics frames
  (`ImmersiveXP/HUD.gd:30,32`, `interactDot` feature):
    - `"\n\n"` (when aiming)
    - `"\n.\n"` (default, interact-dot mode)

  When the addon is enabled, `mod_addon.strip_immersivexp_prefix(text)`
  detects and strips these prefixes (including accumulated forms like
  `"\n.\n\n.\nFire …"`) before lookup, so all 9 match tiers (static /
  literal_scoped / pattern_scoped / literal_global / pattern_global /
  static-score / scoped-literal-score / scoped-pattern-score / substr)
  hit the inner text. The prefix is reattached to the translated
  result and written back to the node.

- **UI: "Addons" tab** in the language window (F9). Layout follows the
  Whitelist tab — left: per-addon checkbox + description + `Used
  with: <mod>` hint; right: `Activate All` / `Deactivate All` bulk
  buttons. Default is all OFF — the user only enables an addon for a
  mod they actually have installed. Addon state is persisted under
  the new `[addons]` section of `user://trans_to_vostok.cfg`.

- **`CHANGELOG_user.md`** — user-facing short changelog (English +
  Korean), covering only what users notice in-game. Internal
  refactors / build pipeline / license details remain in the
  developer-facing `CHANGELOG.md`. Top-level **Known Issues** section
  added (currently lists: the Select Language UI itself being
  partially translated when it shouldn't be — fix planned).

### Changed

- **CHANGELOG (developer)**: 0.4.5 substr boundary entry retoned. The
  earlier wording implied this was the main cause of the "0.4 이후
  번역이 제대로 안 된다" user reports — that was speculation, not
  measured. Reframed as a defensive safeguard: "could in theory
  produce garbled output like `Catalog → 고양이alog`". The 77-corpus
  simulation result is kept as factual evidence.

### Removed

- **Whitelist tab "Reset to Defaults" button** removed. All preset
  defaults are `false`, so the reset button produced the same result
  as `Deactivate All` — redundant. (Same decision applied
  preemptively to the new Addons tab.)

### Internal

- `build_mod_package.py`: `MOD_FILES` extended with `mod_addon.gd`.
  Without this, the new module is not in the packaged zip and
  runtime `load()` fails with `File not found`.
- `translator_ui.gd`: new `_enabled_addons` dictionary, persisted
  under `[addons]` in `user://trans_to_vostok.cfg`. New
  `_build_addons_tab(tabs)` function. Addon state passed to
  `translator_node.addon_*` variables on `_apply_locale`.
- `translator.gd`: new `MOD_ADDON_SCRIPT` constant + `_mod_addon:
  GDScript` reference + `addon_immersivexp_prefix: bool` flag.
  `_initialize()` runtime-loads the addon module. `_apply_binding()`
  strips the prefix before `_lookup_cached()` and reattaches it to
  the result — tier chain itself is unchanged; addon processing
  happens **outside** the tier chain at the binding apply level.
- Bumped `mod.txt` version `0.4.5 → 0.5.0`.

---

## [0.4.5] — 2026-05-05 (Hotfix)

### Fixed (Engine)

- **`translator.gd`: word-boundary safeguard for substr matches.**
  With 614 substr entries (many short tokens like `Use`, `Cat`, `Day`,
  `Map`, `Rig`, `Can`), `String.replace` would match anywhere a src
  appeared as a substring — including inside unrelated English words
  (e.g. `Cat` inside `Catalog`, `Day` inside `Daybreak`, `Fire` inside
  `Fireplace`, `Hard` inside `Hardware`). In theory this could produce
  garbled output like `Catalog` → `고양이alog`, `Daybreak` → `일break`.
  Added a word-boundary guard in `_apply_substr` /
  `_replace_at_word_boundaries`: a substr match is now applied only
  when the position is flanked by non-word chars (= non
  `[A-Za-z0-9_]`). Comma- or space-separated combined labels (e.g.
  `Hybrid, OZ5, Leopard, Magazine`) still translate fully (boundaries
  are commas/spaces). Simulation against the literal/static/scoped
  corpus identified 77 corpus texts where the unguarded behavior would
  differ from the boundary behavior — **all 77 are partial-word
  matches inside unrelated English words; 0 valid matches accidentally
  blocked**. The 0.4.1 idempotency guard is kept as a backup for the
  rare case where boundary alone doesn't catch accumulation (e.g.
  French `NVG → "Vision Nocturne (NVG)"` with parenthesis-flanked
  NVG).

- **`translator.gd`: `containerName` removed from `TRANSLATABLE_PROPS`.**
  `containerName` is a game-data field used by game logic for English
  string comparisons (e.g. **Expanded Storage**
  [modworkshop/56126](https://modworkshop.net/mod/56126)'s
  `if container.containerName in ["Fridge", "Cabinet", ...]`); writing
  a translated value into it broke that comparison and silently
  disabled the other mod's effect. Display labels still get translated
  via the regular `text` property — `containerName` writes are no
  longer needed because the game writes the same source text into a
  Label.text downstream (e.g. `Interface.gd:408 — containerName.text =
  container.containerName`), which our binding catches.

### Added (Common)

- **Trader / NPC-faction name entries (substr)** — Trader, Generalist,
  Doctor, Gunsmith, Driver, Grandma, Shaman, Fisherman, Scientist
  (traders); Bandit, Guards, Military (hostile NPC factions);
  Punisher (elite NPC). Registered in the Main sheet with
  `method=substr` so they translate even when other mods prepend a
  prefix to the label text (e.g. ImmersiveXP's `.\n\n{name}` pattern
  on Trader UI).
- The previous Interface-sheet `literal` entries for Doctor /
  Generalist / Gunsmith were folded into the Main-sheet substr
  entries to consolidate (avoid duplicate registration across
  sheets).
- The generic `Trader` row in the Events sheet is now `method=ignore`
  to prevent it from re-registering and conflicting with the
  Main-sheet entry above.

### Internal

- **Renamed `compatible_mode` → `substr_mode`** across the codebase. The
  flag's actual behavior is "extend substr_entries with all literal +
  static translations so substr fallback covers more cases" — unrelated
  to mod-compatibility. New name reflects what it actually does.
  Affected: `translator.gd` (var `_compatible_mode` → `_substr_mode`,
  func `_apply_compatible_mode` → `_apply_substr_mode`),
  `translator_ui.gd` (vars + UI checkbox label + config key),
  `locale.json` (key `compatible` → `substr_mode_label`, label text
  rewritten to "Substr Mode" wording for en/ko/fr).
  **One-time migration**: existing `user://trans_to_vostok.cfg` with the
  old `compatible_mode` key is auto-copied to `substr_mode` on next
  load, then the old key is erased. Old `locale.json` `compatible` key
  is read as fallback. No user action required.
- Bumped `mod.txt` version `0.4.4 → 0.4.5`.

---

## [0.4.4] — 2026-05-05 (Minor Fix)

### Added (Common)

- **Tutorial Exit** — registered the `nextZone = "Tutorial Exit"`
  string from `Modular/Doors/Transitions/Door_Tutorial_Exit`,
  which the HUD transition overlay (`Scripts/HUD.gd:94 — zone.text =
  transitionData.nextZone`) displays when leaving the tutorial map.
  Was previously shown in English regardless of locale.

### Internal

- Bumped `mod.txt` version `0.4.3 → 0.4.4`.

---

## [0.4.3] — 2026-05-05 (Hotfix)

### Fixed (Engine)

- **`translator.gd`: in-game language switch failed to refresh
  inventory / settings / other already-instantiated UI.** The
  `_ttv_bound_props` meta introduced by the 0.4.1/0.4.2 dedupe guard
  was not cleared in `shutdown()`, so after a language change the
  rebuild step (`_bind_tree`) skipped every node that already carried
  the meta — leaving the entire UI in the previous locale until those
  nodes were freed and re-instantiated. `shutdown()` now removes the
  meta in the same binding-restore loop that already cleans up
  `_ttv_popup_originals` and `_ttv_orig_offset_*`.

### Internal

- Bumped `mod.txt` version `0.4.2 → 0.4.3`.

---

## [0.4.2] — 2026-05-05 (Hotfix)

### Fixed (Engine)

- **`translator.gd`: performance regression from 0.4.1 dedupe guard.**
  The `_bind_node` duplicate guard introduced in 0.4.1 walked both
  `priority_bindings` and `normal_bindings` linearly on every call
  (~1030 entries at startup). Inventory / Trader UIs add many nodes in
  a short window, making the cost effectively O(N²) and causing
  noticeable hitches when opening crates or interacting with traders.
  Replaced with a per-node `_ttv_bound_props` meta lookup — O(1)
  membership check, and the meta is automatically discarded when the
  node is freed (no cleanup pass needed). Dedupe behavior unchanged.

### Internal

- Bumped `mod.txt` version `0.4.1 → 0.4.2`.

---

## [0.4.1] — 2026-05-05 (Hotfix)

### Fixed (Engine)

- **`translator.gd`: substr translation accumulation bug.** When a substr
  entry's translation contains the source text as a substring (e.g.
  English `Hybrid` → French `Hybride`), repeated applications compounded
  the result indefinitely (`Hybride` → `Hybridee` → `Hybrideee` → ...).
  Triggered on first appearance of an item card containing the affected
  text, because Godot's `node_added` signal fires multiple times per node
  during inventory layout (reparent / re-attach), and `_bind_node` had no
  duplicate guard — multiple bindings on the same `(node, prop)` each
  re-applied substr while bypassing the input-text-keyed translation
  cache. Two layers of fix:
  - **`_bind_node` dedupe** — refuses to register a new binding if the
    same `(node, prop)` is already bound. Stops binding accumulation
    regardless of how many times `node_added` fires.
  - **`_apply_substr` idempotency guard** — when `entry.text` is a
    substring of `entry.translation`, refuses to re-apply if the result
    has already been produced (detected by stripping the translation
    occurrence and checking whether the source still appears).

### Fixed (Language: French)

- **Intro paragraph line wrapping** — `se déroulant` → `situé` to keep
  the line break aligned with the Korean / English intro panels (7
  characters shorter; meaning unchanged).

### Internal

- Bumped `mod.txt` version `0.4.0 → 0.4.1`.

---

## [0.4.0] — 2026-05-05

This release adds **French language support** as the first non-Korean
locale. Behind the scenes, the public-release license / contribution
structure and a DeepL-based machine-translation pipeline for
bootstrapping additional languages are being prepared and tested.

### Added (Language: French)

- **French translation** — initial pass machine-translated via DeepL.
  Covers `Translation.xlsx` (game text), `Texture.xlsx` (image labels),
  and `Glossary.xlsx` (translator reference). _The translation is
  currently maintained internally; the public repository and
  contribution flow for community refinement are still being prepared
  (see Notes below)._
- French entry registered in `Trans To Vostok/locale.json` for in-game
  language selection.

### Fixed (Language: Korean)

- Minor mistranslation fixes across the text translation.
- **Tutorial billboard texture typo** — corrected 접격지대 → 접경지대
  (the misspelled label was visible on the billboard image; the texture
  has been re-exported with the corrected spelling).

### Fixed (Engine)

- **`_adjust_value_child_offset` (translator.gd): regression from game
  build 0.1.1.3.** The function had `if value.layout_mode != 0: return`,
  which silently skipped any Value node with `layout_mode=1` (ANCHORS)
  — including Trader-panel labels (`Tax:`, `Tasks:`, `Resupply:`) and
  other anchored Values across the game. This had been working in game
  builds **0.1.0.0** and **0.1.1.1 beta**, where the same Values were
  emitted with `layout_mode=0`, so the function ran normally. From game
  build **0.1.1.3** onward, those Values are emitted with `layout_mode=1`
  and were being silently skipped — meaning position adjustment was
  broken on 0.1.1.3 for Korean, French, and any locale that hits these
  nodes. The guard now accepts both `layout_mode=0` (POSITION) and `1`
  (ANCHORS); only `2` (CONTAINER) is excluded.

### Notes

- **Public repository preparation in progress** — license, NOTICE,
  AUTHORS, CONTRIBUTING, LICENSE-* files are in place. Additional
  housekeeping is still ongoing before the repository is made public.

### Internal

#### Licensing & contribution scaffolding (repo-only, not shipped in mod zip)

- **`LICENSE.md`** — master licensing overview with derivative-work
  preservation guide ("what to keep when forking / redistributing").
- **`LICENSE-CODE`** — Apache License 2.0 for code (Python tools,
  GDScript, batch).
- **`LICENSE-TRANSLATION`** — CC BY 4.0 for translation text content,
  with explicit notes that the original Road to Vostok English text
  remains the game developers' copyright.
- **`LICENSE-TEXTURE`** — CC BY 4.0 for texture/image assets, with
  upstream third-party attribution preservation requirements
  (Copernicus Sentinel-2, MML, Pixabay, Texturelabs, etc.) and
  warranty disclaimer.
- **`NOTICE`** — Apache 2.0 attribution notice (legally required to
  preserve in derivatives).
- **`AUTHORS.md`** — author / translator / contributor list. Translators
  section auto-generated from each locale's xlsx; manual sections
  preserved across regenerations via BEGIN/END markers.
- **`CONTRIBUTING.md`** — contribution guide with the DeepL pipeline
  walkthrough and per-role (translator / texture worker / code
  contributor) credit-registration steps.

#### Tooling — DeepL machine-translation pipeline

- **`tools/machine_translation_deepl.py`** — single-command DeepL
  pipeline orchestrator (export → translate → import). Supports
  `--limit`, `--dry-run`, and `--deepl-lang` override.
- **`tools/utils/export_unique_text.py`** — extracts deduplicated
  source texts from `Translation.xlsx`, `Texture.xlsx`, and
  `Glossary.xlsx`, filtered to "needs translation" status (already-
  translated rows skipped to save quota).
- **`tools/utils/translate_with_deepl.py`** — DeepL API caller with
  placeholder protection (`{name}` → `<x>{name}</x>`), XML escape
  (`&`/`<`/`>`), text-keyed resume, and error-row retry.
- **`tools/utils/import_translations.py`** — writes translations back
  into all three locale xlsx files. Per-row logic handles
  `untranslatable=1` (copy source), `method=ignore` (text-lookup with
  source-copy fallback), and `Machine translated=1` flag.

#### Tooling — credits & metadata generation

- **`tools/utils/build_translation_credit.py`** — auto-generates
  `<locale>/Translation_Credit.md` from MetaData (`Translator`,
  `Contributor (Translate)`) and Texture.xlsx (`Reworked by`,
  `Contributors`) columns.
- **`tools/utils/build_authors.py`** — auto-updates the Translators
  section of project-root `AUTHORS.md` (marker-bracketed regeneration).
- **`tools/utils/build_translation_tsv.py`** — exports each locale
  xlsx to per-sheet TSV under
  `Translation_TSV/<locale>/<xlsx>/<sheet>.tsv` for git-diff visibility.

#### Tooling — parser merge

- **`tools/parse_translatables.py`** — runs `parse_tscn_text.py`,
  `parse_tres_text.py`, and `parse_gd_text.py` in sequence (single
  command).

#### Tooling — diagnostic merge

- **`check_untranslated.py`** absorbs **`_diff_unique_id.py`** (deleted)
  — now reports `DRIFTED` rows where xlsx `unique_id` is stale relative
  to current parsed TSV; previously this required a separate tool run.

#### Repo structure & file moves

- **Tools reorganized** — `tools/` root holds user-facing entry points
  only (`build_mod_package.py`, `machine_translation_deepl.py`,
  `parse_translatables.py`, `validate_translation.py`, `check_*.py`).
  Helpers moved to `tools/utils/`.
- **`Images.xlsx` → `Texture.xlsx`** — singular-noun naming consistent
  with other workbooks (`Translation.xlsx`, `Glossary.xlsx`).
- **`Attribution.md` → `Texture_Attribution.md`** — clarifies scope
  (texture-source attribution only); person credit moved to
  `Translation_Credit.md`.
- **`<locale>/runtime_tsv/`** — runtime TSVs (translation_*.tsv,
  metadata.tsv) consolidated under a per-locale subfolder.
- **Glossary** — moved from single curated `glossary.tsv` to per-locale
  `Glossary.xlsx` for Excel-friendly editing; canonical TSVs auto-
  exported under `Translation_TSV/<locale>/Glossary/`.
- **`requirements.json` → `requirements.txt`** — standard pip format.
- **`set_requirements.py` and `unpack_and_decompile_pck.bat` removed**
  for public-release legal clarity. README documents the manual
  `gdre_tools` install path instead.

#### Version

- Bumped `mod.txt` version `0.3.4 → 0.4.0`.

---

## [0.3.4] — 2026-04-26 (Hotfix)

### Fixed (Language: Korean)

- **WorldMap texture** — corrected wrongly drawn road guidelines.

### Internal

- Bumped `mod.txt` version `0.3.3 → 0.3.4`.

---

## [0.3.3] — 2026-04-26

World map texture translation added. Build pipeline now auto-generates a per-locale Attribution document.

### Added (Language: Korean)

- **World map texture translation** — Korean version of the in-game world map (place names, decorative overlays). Base imagery: modified Copernicus Sentinel-2 data. Full per-asset credits at `Trans To Vostok/Korean/Attribution.md`.

### Notes

- **Public repository preparation for other-language support / contributions** — planned to begin from v0.4.x onwards (may take a while).

### Internal

- **`build_attributions.py`** — new tool. Reads `<locale>/Images.xlsx` (`File Name`, `Reworked by`, `Attribution` columns) and generates `<locale>/Attribution.md` summarizing per-image source credits.
- **`build_mod_package.py` integration** — automatically runs attribution generation for each locale; the resulting `Attribution.md` is included inside the mod zip.
- **README** — added Section 6 "Attribution" pointing users to the bundled `Attribution.md`.
- **In progress (carried from v0.3.2)**: public toolbox refactor.
- Bumped `mod.txt` version `0.3.2 → 0.3.3`.

---

## [0.3.2] — 2026-04-24

Translation update for the game's rendering-pipeline rework (game build v0.1.1.3).

### Added (Common)

- **Settings (Rendering) entries registered** — new render-resolution buttons (`Low` / `Native`), `Image Sharpness` label, and `SMAA Off / On` antialiasing toggle added to the xlsx as new translatable rows.
- **Main menu Compatibility warning registered** — the hidden red label shown when launching with the Compatibility renderer added as a translatable row.
- **Killbox messages registered** — newly added in the game's v0.1.1.3 update.

### Fixed (Common)

- **UI property updates** — refreshed xlsx entries for UI nodes whose properties changed in the game update.

### Added (Language: Korean)

- Korean translations filled in for all of the newly registered entries above (e.g., `Native` → 네이티브, `Image Sharpness` → 이미지 선명도, Compatibility warning → 호환 모드, `Item Returned: {name}` → 아이템 회수, `Player Returned` → 플레이어 복귀).

### Fixed (Language: Korean)

- **Mistranslation fixes** — e.g., `Border` in the Settings / Music preset refers to the border-area BGM, so the translation was corrected from 국경 → 접경지대 (and similar context-based fixes).

### Internal

- Bumped `mod.txt` version `0.3.1 → 0.3.2`.
- **In progress: image translation template** — standardizing the xlsx / texture-swap workflow so other languages can contribute translated textures.
- **In progress: toolbox refactor for public release** — removing potentially sensitive parts of the toolbox in preparation for publishing the translation-toolbox repository on GitHub.
- **In progress: Korean map translation** — localized world-map texture (place names, legends) under development.

---

## [0.3.1] — 2026-04-22

Adds a user-toggleable **priority whitelist** — a new F9 UI tab lets players opt specific UI areas (HUD map label, inventory, trader, etc.) into per-frame priority translation to counter flicker caused by other mods periodically rewriting in-game text (e.g., ImmersiveXP overriding HUD.gd `_physics_process`).

### Added (Engine)

- **`WHITELIST_PRESETS` in `translator.gd`** — const Dictionary of toggleable path-keyword presets, each with `nickname`, `description`, `mod_list`, `default` metadata. `_is_priority_node` now checks enabled presets in addition to the hardcoded base keywords. Seven initial presets shipped: HUD Info Area (Broad), HUD Map Label, Context Menu, Container / Inventory / Equipment / Trader UIs — all default OFF.
- **`enabled_whitelist` runtime field** passed from `translator_ui.gd` to `translator.gd` on init.

### Added (UI)

- **New F9 "Whitelist" tab** — `TabContainer` wraps existing settings into a "General" tab and introduces a second "Whitelist" tab. Left panel shows a scrollable list of preset checkboxes with descriptions, associated mod names (e.g., "Used with: ImmersiveXP"), and the underlying path keyword. Right panel reserved for future user-custom keyword input.
- **`[whitelist]` section in `user://trans_to_vostok.cfg`** — per-preset `true/false` state persists across sessions. Renamed or removed keys in older configs are safely ignored (falls back to preset default, no crash).

### Added (Language: Korean)

- **`[Open]` / `[Locked]` substr entries** — added as independent substr so the status tags still translate when other mods prepend a prefix to tooltip text (e.g., ImmersiveXP's `\n.\n` aim indicator breaks the `{containerName} [Open]` pattern match).

### Fixed (Language: Korean)

- **`Outpost` mistranslation in Task descriptions** — previously transliterated as 아웃포스트; corrected to the semantic translation 전초기지 for consistency with the term's meaning and other usages across the game.

### Fixed

- **HUD map name flicker with ImmersiveXP** — root-caused: `ImmersiveXP/HUD.gd._physics_process` overwrites `map.text` every 10 physics frames via `UpdateMap()`, racing with the translator's normal batch. Addressed by shipping the `hud/info/map` whitelist preset (default OFF; enable from F9 → Whitelist for affected players).

### Internal

- Bumped `mod.txt` version `0.3.0 → 0.3.1`.
- TODO: user-custom whitelist keyword input to cover unverified mods (right panel of the Whitelist tab).

---

## [0.3.0] — 2026-04-22

This release introduces **image / texture translation** — the mod can now ship localized replacements for in-game textures (sprites, Sprite3D, MeshInstance3D shader parameters) alongside the existing text translation pipeline. The first shipped set covers the Tutorial Billboards in Korean.

### Added (Language: Korean)

- **Tutorial Billboard textures** (17 images) — translated Korean versions of `TX_Tutorial_AI / Ammo / Armor / Attachments / Equipment / Grenades / Interface / Items / Maps / Medical / Settings / Shelters / Traders / Vostok / Weapons / World` + a re-exported pass with corrected typography. Original copyrighted game images are **not** bundled — only the translated layers.
  - **Note**: Translated textures were hand-crafted (reconstructed), and may include hand-drawn work and/or copyright-free assets, so some icons may differ slightly from the originals (e.g., Performance icon, Permadeath skull icon on the Tutorial Billboards).
- **`Korean/Images.xlsx`** — new metadata workbook tracking translated image assets (path, source, translator, notes).

### Added (Engine)

- **`texture_loader.gd`** — new runtime texture replacement engine (~287 lines). Scans `res://Trans To Vostok/<locale>/textures/` recursively, walks the scene tree + listens to `node_added`, and swaps:
  - `TextureRect` / `Sprite2D` / `Sprite3D` `.texture`
  - `MeshInstance3D` ShaderMaterial `sampler2D` parameters (`shader_parameter/*`)
  
  Original references are kept in `_bindings` so `shutdown()` restores them cleanly on language switch. Missing files are silently skipped — no crash, original texture stays.
- **`translator_ui.gd` lifecycle integration** — language switch now also shuts down and re-instantiates the texture loader for the new locale, mirroring the translator handling.

### Added (Tooling)

- **`build_mod_package.py`** — now includes each locale's `textures/` folder in the packaged mod zip. (Validation + texture metadata list generation flagged as TODO for a future release.)

### Internal

- Bumped `mod.txt` version `0.2.3 → 0.3.0`.

---

## [0.2.3] — 2026-04-21

### Changed (Language: Korean)

- **`Kilju` translation refined** — Previously rendered as 밀주 (generic Korean word for homemade liquor). Now kept as 킬유 (direct phonetic transliteration of the original Finnish term) to preserve the cultural/geographic flavor of the name. An in-line explanation (“킬유라고 내가 젊던 시절에 집에서 담궈먹던 밀주인데…”) was added to the Generalist quest dialogue so Korean players understand what Kilju is without losing the original proper noun.
- **Dialogue polish** — Minor tone/phrasing fixes across trader quest descriptions and event texts for more natural Korean.

### Internal

- Bumped `mod.txt` version `0.2.2 → 0.2.3`.

---

## [0.2.2] — 2026-04-20 (Hotfix)

### Added

- **ModWorkshop update integration** — Added `[updates] modworkshop=56214` to `mod.txt`. The MetroModLoader "Check for Updates" tab can now detect newer versions published on ModWorkshop and download the latest zip directly.

### Internal

- Bumped `mod.txt` version `0.2.1 → 0.2.2`.

---

## [0.2.1] — 2026-04-20 (Hotfix)

### Fixed

- **Cassette tape music titles partially translated** — Track names (e.g., `OST - Daybreak`, `Junna - Haavakko`) were previously registered with `method=ignore`, which excluded them from the runtime TSV entirely. As a result they fell through to Tier 9 substr matching, causing fragments like "Day" to be partially translated inside proper nouns. Re-registered as pass-through literals (translation equals source) so Tier 4 (literal global) hits first and substr matching never runs for these titles.

### Internal

- Bumped `mod.txt` version `0.2.0 → 0.2.1`.
- TODO noted: consider introducing a dedicated `preserve` / `ban` method for intentional pass-through rows to make intent explicit in xlsx.

---

## [0.2.0] — 2026-04-20

### Added

- **Performance options panel in F9 UI** — `Batch Size` and `Batch Interval` can now be tuned at runtime. Values persist to `user://trans_to_vostok.cfg`.
- **DEBUG_STATS performance instrumentation** — Optional 10-second periodic dump of apply calls, cache hit rate, regex tries, and binding counts (disabled by default).
- **`check_duplicate.py`** — New tool for pre-build duplicate key detection, runs the same check as validation without full TSV extraction.
- **Cross-sheet duplicate detection** — `validate_translation.py` now catches the same runtime key appearing in multiple sheets (e.g., Main vs Interface).
- **`Languages` subtitle** on the left side of the F9 UI.

### Fixed

- **OptionButton / PopupMenu dropdown items not translated** — Dropdown items (e.g., Settings → Window Size) were previously skipped because they are not exposed as regular Node properties. Now translated via `get_item_text` / `set_item_text`; originals are preserved on PopupMenu meta and restored on shutdown.
- **Signal double-connect error** on language switch — added `_initialized` guard to prevent `node_added` from being connected twice.
- **Incomplete state reset** on language switch — `_reset_state()` now clears all indexes, caches, and bindings on shutdown to prevent stale entries from accumulating.
- **Missing Korean translations** — Trader Event Descriptions and several other previously-untranslated entries.

### Removed

- **Duplicate translation entries** (e.g., `Knife`, `Bandit`) that appeared across multiple sheets with inconsistent translations.

### Internal

- Bumped `mod.txt` version `0.1.0 → 0.2.0`.
- `NORMAL_BATCH_INTERVAL` / `NORMAL_BATCH_SIZE` promoted from `const` to `var` so the UI can tune them at runtime without reloading the translator.

---

## [0.1.0] — 2026-04-17

First public test version.

### Added

- **Runtime translation engine** (`translator.gd`) — N-tier (9-tier) fallback matching chain: static exact → scoped literal → scoped pattern → global literal → global pattern → score-based → substr.
- **Language selection UI** (`translator_ui.gd`) — shown on mod load; switchable at runtime via `F9`. Selection persists to `user://trans_to_vostok.cfg`.
- **Compatibility Mode** — substr-only fallback for game updates that break precision matching. Toggle via F9 UI checkbox.
- **Text position realignment** — auto-adjusts `Label + Value` manual-layout offsets so translated text doesn't overlap (e.g., Tooltip "Weight: 0.8kg" style).
- **Korean translation** — initial pass covering UI, tooltips, items, tasks, events, traders.
- **Developer ToolBox** (Python pipeline):
  - `a_decompile_pck.py` — decompile game PCK
  - `b_extract_tscn_text.py` — extract text from `.tscn`
  - `c_extract_tres_text.py` — extract text from `.tres`
  - `d_check_untranslated.py` — coverage report
  - `e_validate_translation.py` — xlsx schema / duplicate / match validation
  - `f_build_runtime_tsv.py` — xlsx → runtime TSV
  - `g_build_mod_package.py` — build final mod zip
  - `check_conflict.py` — same-source-text different-translation detector
  - `check_old_translation.py` — stale translation detector

========================================

# 변경 이력 — Trans To Vostok

이 모드의 모든 주요 변경사항을 기록합니다.

포맷은 [Keep a Changelog](https://keepachangelog.com/) 을 따릅니다.

## [0.6.0] — 2026-05-31 (텍스처 Blend 방식 + 표지판 / 구조물 텍스처 추가)

이번 릴리스는 새로운 **`blend` 텍스처 방식**을 도입합니다. mod 측은 투명
배경 + 번역 텍스트만 담긴 overlay PNG 를 제공하고, 런타임에서 원본 텍스처
위에 alpha-blend 합성합니다. 원본의 PBR 정보 (normal map, weathering,
조명 통합) 가 그대로 유지되며, mod 는 본인 작업물 (텍스트 픽셀) 만
배포하는 방식으로 **잠재적인 저작권 문제를 예방**했습니다. Korean 에 16개의 blendable 텍스처들이
가 추가되었고 (표지판, 포스터, Sotilaskoti 간판, 인벤토리 아이콘 등),
다른 active locale 들은 schema 만 적용되어 Crowdin 번역자가 작업할 수 있는
상태로 준비되었습니다. Texture canonical TSV 는 `method` 컬럼 추가 +
4시트 (Tutorial / UI / Signs / Structures) 로 재구성. 여러 신규 빌드 /
sync 도구도 함께 추가됩니다.

### 추가

- **`blend` 텍스처 방식** — 기존 `replace` (전체 텍스처 교체) 의 대안.
  mod 가 투명 배경 + 번역 텍스트 픽셀만 담은 PNG 를 ship → 런타임에서
  `texture_loader.gd` 가 원본 텍스처의 Image 를 가져와 `Image.blend_rect`
  로 alpha-blend → mipmap 생성 후 ImageTexture 로 변환 → material albedo
  교체. `replace` 대비 두 가지 이점: (1) **저작권** — mod 가 원본 텍스처
  픽셀을 derivative 형태로 ship 하지 않고 번역 텍스트 픽셀만 ship;
  (2) **자산당 작업 부담 ↓** — 텍스트 영역만 작업하면 됨, 원본의 PBR
  (normal map, roughness, weathering) + 조명 통합은 자동으로 유지되어
  재작업 불필요.
- **Korean blend 텍스처 16개** (`Trans To Vostok/Korean/textures/`):
  - `Sign_Mines`, `Sign_Public_Road`, `Sign_VT7` (+ `Frame_Highway_Sign`),
    `Sign_Border_Zone` (4 변형), `Sign_School`, `Sign_Speedbump`,
    `Sign_Village_Crossroads`
  - `Canteen_Details` — Sotilaskoti (핀란드군 매점) 의 KASSA / SOTILASKOTI
    간판 한국어 합성
  - `Board_Message`, `Booth_Ticket`, `Box_Electric`, `Box_Transformer`
  - `Icon_Sign_Border_Zone` (인벤토리 아이콘)
- **Texture canonical TSV 의 `method` 컬럼** — 값: `replace` / `blend`.
  `Type` 과 `Text` 사이에 삽입. 기존 Tutorial Billboards + WorldMap 은
  `replace` 유지.
- **Texture 의 신규 2개 시트**: `Signs.tsv` (13행 — 도로 표지판) /
  `Structures.tsv` (4행 — 텍스트 포함 건물/장비 텍스처). 모든 active
  locale 의 Texture 가 4시트 구조 (Tutorial / UI / Signs / Structures)
  로 정돈.
- **`tools/utils/build_texture_meta.py`** (신규) — Texture TSV →
  `Trans To Vostok/<locale>/texture_meta.json` 생성. 런타임이 method
  라우팅에 사용.
- **`tools/push_source_to_crowdin.py`** (신규) — Template 의 source TSV 를
  Crowdin 에 SDK 로 업로드. 장기 pending TODO 해결. `crowdin.yml` 의
  export pattern 을 자동 적용해서 신규 source 파일도 정상 export path 로
  설정됨.
- **`tools/utils/sync_texture_schema.py`** (신규) — Template 의 Texture
  TSV 구조 (시트 + 행) 를 모든 active locale 에 propagate. 각 locale 의
  기존 Translation / Reworked by / Contributors / Attribution 보존.
- **`tools/rebuild_xlsx.py all`** — `Translations/` 하위 모든 locale 의
  xlsx 를 한 번에 재생성.
- **`tools/push_to_crowdin.py --base <rev>`** — diff baseline 으로 임의
  git 리비전 (commit / tag / `HEAD~N`) 지정 가능. 신규 source 파일 첫
  push 시 (이미 commit 된 상태에서) HEAD diff 가 비어있는 문제 해결.

### 변경

- **`texture_loader.gd`** — `_load_texture_meta()`, `_composite_blend()`
  추가 + `_try_bind_texture_property` / `_try_bind_shader_material` 에
  method 분기. `_blend_cache` 로 같은 sign 의 여러 인스턴스가 동일 합성
  결과 재사용.
- **`tools/utils/rebuild_texture_xlsx.py`** — `method` 컬럼에 조건부
  서식 (replace = 파란색; blend 는 기본 셀).
- **`tools/build_mod_package.py`** — 패키징 step 8 로 `texture_meta.json`
  zip 포함 + 각 locale 빌드 시 `build_texture_meta.py` 호출.
- **`pull_from_crowdin.py` zip 다운로드** — blocking `urlopen().read()`
  → chunked streaming (120초 timeout + 초당 진행률 출력). 이전 CDN 지연
  시 hang 문제 해결.
- **`api_client.py` source-file 업로드**:
  - `list_directories` / `create_directory` / `_ensure_directory` helper,
    `add_source_file` / `update_source_file` 추가. import scheme 키는
    snake_case (`identifier`, `source_phrase`, `translation`, `context`,
    `labels`, `max_length`).
  - `upload_source_files` 가 `crowdin.yml` 의 패턴을 읽어 신규 파일에
    `exportOptions.exportPattern` 자동 적용.
- **Texture schema sync**: Korean 외 8개 active locale 도 Tutorial / UI /
  Signs / Structures 4시트 갖춤. 번역 컬럼은 비어있음 (Crowdin 작업
  대기).
- **일본어 — 83개 string 다듬어짐** (기여자: Nineblood, Crowdin 경유).
  `pull_from_crowdin.py Japanese` + `apply_to_repo.py` 로
  `Translations/Japanese/Translation/*.tsv` 에 반영.

### 수정

- **거리에서 표지판이 원본 영문으로 보이는 LOD fallback** —
  `Image.generate_mipmaps()` 를 `ImageTexture.create_from_image` 전에
  호출하도록 변경. 이전엔 mipmap 부재로 거리에서 원본 PCK 텍스처의
  mipmap 으로 fallback.
- **Sign_VT7 / Frame_Highway_Sign 경로 중복** — 게임 내 도로 안내 표지판은
  실제로 `Assets/Frame_Highway/Files/TX_Frame_Highway_Sign_AL.png` 를
  사용하지만 asset 명은 `Sign_VT7`. mod 가 동일 overlay PNG 를 양쪽
  경로에 배치.
- **Crowdin pull stray 디렉토리** (`mods/Trans To Vostok/de/`, `cs/`,
  `fi/`, ...) — 신규 업로드 source 파일에 `exportPattern` 미설정 → Crowdin
  의 default 패턴 (`<locale>/<source_path>`) 적용 결과. `crowdin.yml` 의
  패턴을 코드가 읽어 적용하도록 fix. 영향받은 2개 파일 (Signs / Structures)
  의 패턴은 Crowdin 웹에서 수동 수정.

### 내부 / 도구

- 신규 도구: `build_texture_meta.py`, `push_source_to_crowdin.py`,
  `sync_texture_schema.py`.
- 기존 도구 확장: `push_to_crowdin.py --base <rev>`, `rebuild_xlsx.py all`.
- `target_game_version` 은 `mod.txt` 와 `info.json` 양쪽 유지 (변경
  없음, `0.1.1.3`).
- 문서: `_sheet_order.txt` 스키마에 `Signs` 와 `Structures` 추가됨 (모든
  active locale).

## [0.5.3] — 2026-05-30 (신규 5개 언어 — DeepL 1차 기계번역)

이번 릴리스는 **신규 5개 로케일**을 DeepL 1차 기계번역(텍스트만, 텍스처는
추후)으로 추가합니다. 로케일 레지스트리 재조정: 이번 사이클에서 임시로
추가되었다가 DeepL 1차 패스가 완료되지 못한 Italian 은 출시 전 완전히
제거했고, Russian 은 추가되었으나 비활성(`enabled: false`) 상태로 출시 —
DeepL Free 월간 quota 가 패스 도중 소진되었으며, 부분 완료된 Russian xlsx
는 저장소에 보존되어 다음 달 quota 리셋 시점에 이어서 완료할 예정입니다.
`target_game_version` 은 ModLoader 호환 경고용으로 `mod.txt` 에도 함께
선언되었습니다 (F9 Info 탭이 읽는 `info.json` 의 값과는 별도로 유지).

### 추가

- **신규 로케일 (5개)** — 모두 `docs/dev/kr/Add_new_language.md` 의 표준
  워크플로(Template canonical TSV 복사 → `rebuild_xlsx.py` → DeepL
  파이프라인 → `locale.json` 등록)로 추가:
  - **Deutsch** — `display: "Deutsch"`, `message: "Sprache wählen"`.
  - **Español (LatAm)** — `dir: Spanish_LatAm`, DeepL `ES-419`,
    `display: "Español (LatAm)"`, `message: "Seleccionar idioma"`.
  - **日本語** — `display: "日本語"`, `message: "言語を選択"`.
  - **简体中文** — `dir: ChineseSimplified`, DeepL `ZH-HANS`,
    `display: "简体中文"`, `message: "选择语言"`.
  - **繁體中文** — `dir: ChineseTraditional`, DeepL `ZH-HANT`,
    `display: "繁體中文"`, `message: "選擇語言"`.
- **러시아어 로케일 (비활성)** — `dir: Russian`, `enabled: false`.
  DeepL 패스 도중 Free 월간 quota 소진으로 부분 완료
  (~252/1100 unique 문자열). 부분 xlsx 는 저장소에 보존
  (`Translations/Russian/Translation.xlsx`) 되며, 다음 달 quota 리셋 시
  잔여분 완료 후 `enabled: true` 로 전환 예정.
- **`mod.txt[target_game_version]` 필드 추가** — ModLoader
  (`MetroModLoader` 등) 가 게임 버전 호환 경고를 표시할 때 참조하도록
  선언. F9 Info 탭이 읽는 `info.json` 의 `target_game_version` 은 그대로
  hand-edit 유지되며, 게임 버전 bump 시 양쪽을 함께 갱신해야 합니다.

### 변경

- **모든 신규 로케일에 대해 `locale.json` 의 `substr_mode_label` 현지화**
  (Deutsch / Español LatAm / 日本語 / 简体中文 / 繁體中文 / Русский).
- **한국어 — 번역 개선 및 QA** — Task (*의뢰*), Tutorial Billboard
  텍스처, 기타 UI string 다듬어짐 (기여자: gap tal).

### 제거

- **이탈리아어 로케일** — 이번 사이클 도중 추가되었다가 릴리스 전 제거.
  DeepL 1차 패스가 0/1100 성공 (이탈리아어 차례에 도달했을 시점에 이미
  Free quota 소진), 빈 stub 으로 출시하기보다 완전히 제거하는 것으로
  결정. `Translations/Italian/` 디렉토리와 `locale.json` 의 이탈리아어
  엔트리 모두 삭제. DeepL quota 또는 커뮤니티 기여로 초기 커버리지가
  가능해지는 향후 사이클에 재추가 예정.

### 내부 / 도구

- **러시아어 `Translation.xlsx` 는 부분 채움 상태로 유지** —
  `translate_with_deepl.py` 의 resume 지원으로 향후 run 은 기존 252개를
  재처리하지 않고 잔여 ~900개의 unique 문자열부터 이어서 처리.

## [0.5.2] — 2026-05-27 (Crowdin 통합 & 문서 재구조)

이번 릴리스는 **Crowdin 통합 오버홀**을 완료합니다: Java 기반 Crowdin
CLI 의존성을 Python `crowdin-api-client` SDK로 완전히 대체 (push / pull
양쪽), 기존 xlsx 기반 Glossary 워크플로를 Crowdin 네이티브 Glossary
리소스로 전환, 그리고 locale 별 기여자 크레딧을 `Translation.xlsx`의
MetaData 시트에서 새 `Trans To Vostok/<locale>/credits.json`(Crowdin
멤버 + 활동 리포트에서 자동 생성)으로 이전했습니다. 기여자 문서는
`docs/translator/` / `docs/dev/` 구분으로 재구성하여 대상별 워크플로만
보이도록 정리. 그리고 Portuguese 등 인게임 표시 관련 버그 다수 수정.

### 추가

- **Crowdin SDK 파이프라인** — Java CLI 의존 제거. `push_to_crowdin.py`,
  `pull_from_crowdin.py` 모두 `crowdin-api-client` 파이썬 라이브러리로
  전체 sync 수행. Java 설치 불필요. 토큰은
  `tools/configs/secrets.json:crowdin_personal_token`(gitignored)에 설정.
  필요 권한: Projects (Read & Write), Source Files, Translations,
  Glossary (Read & Write).
- **Smart push (HEAD-based diff)** — `push_to_crowdin.py`가 마지막 git
  commit의 canonical TSV 대비 diff를 계산해 변경된 행만 업로드.
  다른 contributor의 작업은 덮어쓰지 않음. xlsx → canonical TSV 변환이
  `.tmp/`에서 수행되어 working tree `Translations/<locale>/` 가 더 이상
  push 때문에 더러워지지 않음.
- **Smart pull (preserve-on-empty)** — `apply_to_repo.py`가 Crowdin이
  돌려준 빈 번역 칸을 무시하여 미번역 행이 로컬 값을 지우지 않도록 보호.
- **locale 별 `credits.json`** (`Trans To Vostok/<locale>/credits.json`,
  committed, 모드 zip에 포함). 스키마:
  ```json
  {
    "translation_updated": "<ISO timestamp>",
    "Translator": {
      "Leader":      [...],   // Crowdin Owner / Manager / Language Coordinator
      "Translator":  [...],   // Crowdin Proofreader
      "Contributor": [...]    // Crowdin Member with translated > 0
    },
    "Texture_reworker": [...]
  }
  ```
  `translation_updated`는 해당 언어의 모든 번역 행에 대해
  `max(createdAt, updatedAt)`(전체 페이지네이션 스캔).
- **`tools/crowdin/get_member_list.py`** (신규) — Crowdin 멤버 +
  Top Members Report 조회 → 역할/활동에 따라 분류 → credits.json의
  Translator 필드 + `translation_updated` 작성. `Texture_reworker`는
  run 간 보존. `pull_from_crowdin.py`가 호출.
- **`tools/utils/get_texture_credits.py`** (신규) — `Texture.xlsx`의
  `Reworked by` + `Contributors` 컬럼을 모든 시트에서 추출 + 중복 제거
  → credits.json의 `Texture_reworker`에 기재. 빌드 시 locale 별로 호출.
- **F9 Info 탭 — locale 별 데이터는 credits.json에서 직접 로드**.
  `info.json`은 더 이상 locale 별 데이터를 담지 않고 프로젝트 와이드
  요약(mod_version / build_date / target_game_version /
  lead_developer / code_contributors / acknowledgments)만 유지.
- **문서 구조 재정비** — `docs/translator/kr/`(Crowdin 웹 or 로컬 + 테스트)
  와 `docs/dev/kr/`(메인테이너 / 기여자) 로 분리, 통합 `docs/` 루트.
  신규 가이드: `Translating_using_crowdin.md`, `Translating_on_Local.md`,
  `Pull_from_Crowdin.md`. CHANGELOG / CHANGELOG_user / README_USER도
  `docs/` 로 이동.
- **`tools/configs/`** — 모든 JSON 설정 파일 통합 위치
  (`languages.json`, `width.json`, `parse_list_*.json`,
  `secrets.json` / `secrets_example.json`). 도구의 모든 Path 상수 갱신.

### 변경

- **`info.json` 스키마** — hybrid 파일(read-modify-write).
  `target_game_version`은 `info.json`에서 직접 hand-edit, 빌드 시 보존.
  `locales` 필드 제거 — locale 별 데이터는 각 `<locale>/credits.json`에
  존재 (F9 UI가 직접 로드).
- **`build_authors.py` / `build_translation_credit.py` / `build_mod_info.py`**
  를 credits.json에서 읽도록 리팩터. 이 세 스크립트에서 `openpyxl` 의존
  제거. AUTHORS.md에 "Translator(s)" 서브섹션 추가 (Crowdin Proofreader
  단계).
- **`build_mod_package.py`** — locale 별 흐름이 `build_translation_credit.py`
  전에 `get_texture_credits.py`를 호출하도록 보강. credits.json의
  Texture_reworker가 항상 fresh.
- **Crowdin pull / push 명시적 `all` 키워드 필수** — 빈 인자 호출은
  실수에 의한 대량 작업 방지를 위해 거부.
- **문서 톤** — `docs/translator/kr/` 와 `docs/dev/kr/` 의 한국어 톤을
  `~입니다 / ~합니다` 격식체로 통일. `~어요 / ~예요` 비격식 표현 치환.

### 수정

- **포르투갈어 (브라질) 번역이 인게임에서 로드되지 않던 문제**.
  `translator_ui.gd`가 `locale.json`의 `locale` 필드를 식별자이자 폴더
  경로로 사용 중이었는데, Portuguese의 `locale="Portuguese"`가 실제
  폴더 `Portuguese_BR/` 와 일치하지 않았음. 이제 폴더 lookup에
  `locale.json`의 `dir` 필드를 사용하며, 기존 settings에 저장된 legacy
  `locale` 값은 자동 마이그레이션.
- **`credits.json`이 패키지된 모드 zip에 빠져있던 문제** —
  `build_mod_package.py` packaging 단계에 `<locale>/credits.json`
  포함 단계가 누락되어 디스크에는 파일이 있어도 F9 Info 탭이
  Translation Updated를 "(unknown)" 으로 표시. locale 별 packaging
  loop에 step 7 추가로 해결.
- **`pull_from_crowdin.py`의 BCP-47 locale 폴더 매핑** — Crowdin이
  export한 zip은 `ko-KR`, `fr-FR`, `pt-BR` 같은 locale 코드를 폴더명
  으로 사용. SDK download 경로에서 프로젝트의 `targetLanguages`를 1회
  조회해 canonical 폴더명 (`Korean`, `French`, `Portuguese_BR`) 으로
  zip entry 경로 재작성.
- **DeepL pattern 행 처리** — pattern 행(`{str}` 같은 placeholder가
  들어간 `method=pattern`)이 DeepL import 후 translation이 비어있던
  문제. 이제 import 단계에서 source를 translation으로 복사하여 런타임이
  영어 템플릿을 반환하도록 처리 (substr 폴백으로 `In 5 Jours` 같은
  부분 번역이 발생하지 않음).
- **`100%` / `100kg`** ToolTip 행을 모든 locale에서 `untranslatable=1`
  로 표시 (untranslatable 의 의미를 숫자/단위 등 본질적 비번역 대상에
  한정하는 정책 정정).
- **문서의 브랜치명 정정** — `main`으로 잘못 표기된 모든 부분을
  실제 기본 브랜치명인 `master`로 정정.

### 제거

- **`Translation.xlsx`의 MetaData 시트** — Translator/번역 갱신일은
  Crowdin, mod_version은 `mod.txt`, target_game_version은 hand-edited
  `info.json`이 소스. canonical `Translations/<locale>/Translation/MetaData.tsv`
  파일들과 `_sheet_order.txt`의 MetaData 항목도 함께 제거.
- **Glossary xlsx 워크플로** —
  `Translations/<locale>/Glossary.xlsx`, canonical TSV 트리
  (`Translations/<locale>/Glossary/`), `tools/utils/rebuild_glossary_xlsx.py`,
  각 도구의 `CATEGORIES` 상수에서 Glossary 키, `make_glossary_id()`,
  `crowdin.yml`의 Glossary `files:` 항목 모두 삭제. 이제 Glossary 용어는
  Crowdin 네이티브 Glossary 리소스로 존재 (Editor 우측 패널 자동 매칭).
  1회성 마이그레이션 도구는 `tools/crowdin/migrate_glossary.py`에 보존.
- **`README/0_..._kr.md` ~ `README/5_..._kr.md`** 번호제 가이드 시리즈 —
  내용을 `docs/translator/kr/` 와 `docs/dev/kr/` 로 대상별 분리 이전.
  기존 `README/CONTRIBUTING.md`는 repo 루트 `CONTRIBUTING.md`로 이동.
- **`README_Translation.md`** — gdre_tools 설치 안내는 이미
  `docs/translator/kr/Setting_Environments.md §1`에 포함되어 중복.
- **`info.json[locales]` 필드** — locale 별 데이터를 각
  `credits.json`으로 이전.
- **`tools/utils/set_requirements.py`** (사이클 중간에 잠시 도입했다가
  머지 전 reverted).

### 내부 / 도구

- **`tools/configs/`** 가 모든 JSON 설정 파일을 모음 (이전엔 `tools/`와
  repo 루트에 흩어져 있음). 도구의 모든 Python `Path()` 상수 갱신.
- **`translator_ui.gd`** 에 `_load_locale_credits(locale)`,
  `_load_json_dict(path)` 헬퍼 + ISO 타임스탬프 표시용 `_date_only()`
  포매터 추가.
- **`tools/crowdin/api_client.py`** 의 `download_translations()` SDK
  헬퍼 — build + poll + zip 다운로드 + locale 경로 재매핑을 1회
  호출로 처리.
- **`tools/utils/build_mod_info.py`** 단순화 — 기존 `info.json` 읽기
  (target_game_version 보존용), mod.txt 파싱, AUTHORS.md 섹션 파싱,
  `locales` 필드 없이 작성.

## [0.5.1] — 2026-05-08 (패치 릴리스)

이번 릴리스는 신규 locale **Português (Brasil) / `Portuguese_BR`** 추가
(DeepL 1차 기계 번역, 텍스트만 — 텍스처 미적용), F9 UI 에 **Info 탭**
신설 (모드 버전 / 빌드 일자 / 게임 타깃 버전 / 역할별 기여자), 그리고
기여자용 한국어 가이드 시리즈를 `README/` 하위에 정리. 내부적으로는
ad-hoc xlsx 직접 편집 대신 **TSV-canonical xlsx rebuild 파이프라인**
도입, 모드 자체의 F9 UI 가 자기 자신에 의해 번역되지 않도록 격리.

### 추가

- **신규 locale: Português (Brasil) / `Portuguese_BR`** — DeepL `PT-BR`
  로 1차 기계 번역 (텍스트만, 텍스처는 추후). `2_Add_new_language_kr.md`
  표준 워크플로 따라 생성: Template TSV 복사 → `rebuild_xlsx.py` →
  DeepL 파이프라인 → `locale.json` 등록. `display: "Português (Brasil)"`,
  `message: "Selecione um idioma (Português Brasileiro)"`.

- **F9 UI Info 탭** 신설. Whitelist / Addons 탭과 동일 HBox 좌우 분할:
  - **좌측 (Mod Info)**: Mod Version (mod.txt), Built (UTC 날짜),
    Target Game Version (각 locale 의 Translation.xlsx MetaData
    "Game Version" — Korean 우선, 없으면 첫 발견 locale), Selected
    Locale + Translation Updated (locale 별 MetaData "Translation
    Updated Date").
  - **우측 (Contributors)**: 프로젝트 전역 — Lead Developer / Code
    Contributors / Acknowledgments (AUTHORS.md 섹션별); 그 다음
    현재 locale 기준 — Translators / Translation Contributors /
    Image Reworkers / Image Contributors (Translation.xlsx MetaData
    + Texture.xlsx 컬럼).
  - 빌드 시 생성되는 `<pkg_root>/info.json` 을 읽음. JSON 부재 /
    파싱 실패 / 타입 미스매치 모두 graceful fallback — `_safe_get_*`
    헬퍼로 모든 read 안전 처리. Info 탭의 어떤 오류도 다른 탭 /
    런타임에 전파되지 않음.

- **F9 UI 가 자기 자신에 의해 번역되지 않도록 격리**. Window 노드 생성 시
  `set_meta("_ttv_skip_translate", true)` 부여 → `translator.gd
  ._bind_node()` 가 부모 체인을 따라 올라가며 해당 메타 보유한 ancestor
  를 가진 노드는 binding 등록 자체 스킵. 이전엔 모드 자체 UI 텍스트가
  literal global / substr 룰에 매칭돼 타깃 언어로 치환되는 현상이
  있었음.

- **`tools/rebuild_xlsx.py`** + 카테고리별 utility (`tools/utils/
  rebuild_translation_xlsx.py` / `rebuild_glossary_xlsx.py` /
  `rebuild_texture_xlsx.py`). TSV → xlsx 빌드 시 현재 서식 / 컬럼
  너비 / 조건부 서식 정책을 일괄 적용. 기존의 xlsx 직접 편집 패턴을
  대체. 새 locale 워크플로의 핵심 — Template TSV 가 canonical 이라
  `rebuild_xlsx.py NewLocale` 한 줄로 DeepL 작업 준비된 fresh xlsx
  생성.

- **`tools/utils/build_mod_info.py`** — F9 Info 탭이 사용하는
  `info.json` 생성. 출처: `mod.txt` (mod_version), 오늘 (UTC,
  build_date), Translation.xlsx MetaData (target_game_version, locale
  별 translation_updated / translators), Texture.xlsx 데이터 시트
  (locale 별 texture_reworkers / contributors), AUTHORS.md
  (lead_developer / code_contributors / acknowledgments). 출처 누락
  / 포맷 이상 시 기본값으로 fallback — info.json 형태는 항상 보장.
  `build_mod_package.py` 의 step 4.5 (`build_authors_md` 후,
  packaging 전) 로 wired.

- **`README_USER.md`** — modworkshop description 페이지용 README
  분리 (Features / Install / Compat mods / Languages / Attribution /
  Screenshots, 영어 + 한국어 병기). 이미지 링크는 GitHub raw URL 로
  교체되어 외부 사이트에서도 렌더링됨. 저장소의 `README.md` 는
  repo / 개발자 entry point 로 재구성 (Quick Start 표 → README/
  가이드 시리즈 링크, 디렉토리 layout, 도구 표, 기술 구조, 라이선스,
  로드맵).

- **한국어 기여자 가이드 시리즈** (`README/`):
  - `0_Setting_Environments_kr.md` — Excel / Python / Git / VS Code
    / Fork & Clone 셋업; `main` 직접 commit 금지 경고 포함.
  - `1_unpack_and_decompile_game_kr.md` — gdre_tools 셋업 +
    `parse_translatables.py` 로 full validation 활성화. parsed_text
    부재 시 빌드가 막히지 않으므로 선택 단계로 표기.
  - `2_Add_new_language_kr.md` — Template (Korean → sync) →
    `rebuild_xlsx.py Template` → 새 locale 폴더 복사 → DeepL →
    `locale.json` → 빌드.
  - `3_How_to_Translate_kr.md` — 번역가용: MetaData 크레딧 필드,
    translation 컬럼 작업 흐름, 앞뒤 공백 / 줄바꿈 매칭 주의, 빌드
    → 게임 내 검증.
  - `3_How_to_Translate_kr(For Developers).md` — 확장판: 모든
    method 의미, 9-tier 런타임 우선순위 (substr Tier 9 포함 —
    `build_runtime_tsv.py` 헤더 주석에서 누락됐던 부분), Godot 식별자
    컬럼, 충돌 해결.
  - `4_How_to_Pull_Request_kr.md` — 브랜치 위생, 명명 컨벤션 (이름
    중복 회피 안내 포함), PR 템플릿.
  - `5_How_to_Update_from_MasterBranch_kr.md` — rebase 기반 upstream
    동기화 ("한 브랜치 = 한 기여자" 정책에 부합), xlsx binary 충돌은
    TSV-shadow 재빌드로 해결.

- **AUTHORS.md `## Acknowledgments`** 섹션 — **DIO-KAMI** 의 RTV
  [Korean Localization for DEMO](https://modworkshop.net/mod/55997)
  를 영감 출처로 명시. 자동 생성 마커 밖에 두어 `build_authors.py`
  실행 후에도 보존됨.

### 변경

- **`tools/validate_translation.py`** — `tsv_dir` 파라미터를
  `Optional[Path]` 로 변경. `None` 또는 폴더 부재 시 parsed_text
  의존 검사 (`check_tsv_match` / `check_tres_text` / `check_gd_text`)
  만 스킵하고 나머지 (`check_flags` / `check_method_fields` /
  `check_empty_method` / `check_whitespace` / `check_duplicates` /
  `check_duplicates_cross_sheet`) 는 계속 수행. `build_runtime_tsv.py`
  가 parsed_text 부재 자동 감지 → partial mode 메시지 출력 후 진행.
  `--ignore` 는 여전히 검증 전체 스킵. 외부 기여자가 gdre_tools 없이도
  빌드 가능.

- **`tools/machine_translation_deepl.py`** — `DEFAULT_DEEPL_LANG` 을
  11 → 약 50 entry 로 확장 (DeepL 모든 target 언어). 변종 코드
  (`EN-GB` / `EN-US`, `PT-BR` / `PT-PT`, `ES-419`, `ZH-HANS` /
  `ZH-HANT`) 는 camelCase (`EnglishGB`, `BrazilianPortuguese`) 와
  underscore-suffix (`English_GB`, `Portuguese_BR`) 양쪽 모두 alias
  로 등록. 이제 `Portuguese_BR` 도 `--deepl-lang` 명시 없이 동작.

- **README.md 분할** — repo (개발자 entry) + `README_USER.md`
  (modworkshop). Repo README 는 Quick Start 표로 시작 → `README/0~5_*.md`
  가이드 시리즈 링크.

- **`build_mod_package.py`** — `MOD_FILES` 에 `info.json` 추가. 새
  step 4.5 가 `build_authors_md` 가 AUTHORS.md 를 finalize 한 뒤,
  TSV-shadow refresh / packaging 전에 `build_mod_info.py` 호출.

- **LICENSE.md** — "Currently identified upstream sources include
  (non-exhaustive):" 표현을 "For example:" 로 완화. MML / Copernicus
  목록이 실제 사용 주장이 아닌 예시임을 명확화. (현재 출하 텍스처
  중 MML 출처 없음 — `Texture_Attribution.md` 검증 결과.)

### 수정

- **Items / Assets(Furniture) SUB 세분화**. 기존엔 같은 SUB 값을 다수
  행이 공유 (예: 모든 Armor 아이템에 `"Armor"`, 모든 컨테이너에
  `"Containers"`) — rebuilder 의 그룹 분리선 시각화 의미를 잃음.
  이제 filename 비어있지 않은 행에 한해 `SUB = <기존 SUB> +
  filename[filename.rfind('/'):]` 적용 (Items 1,570 / 1,611 행,
  Assets(Furniture) 265 / 267 행). filename 빈 행은 스킵
  (카테고리 헤더 의미 보존).

- **`build_runtime_tsv.py` 헤더 9-tier 목록**: 주석에 substr (Tier 9)
  가 누락돼 있었음. 런타임 우선순위 체인엔 존재. 헤더 주석을 9-tier
  완전 형태로 갱신.

### 제거

- **`git filter-repo` 로 디컴파일 헬퍼 스크립트들을 history 에서 완전
  제거**: `tools/a_decompile_pck.py`, `tools/decompile_gdc.bat`,
  `tools/unpack_and_decompile_pck.bat`,
  `tools/unpack_and_decompile_pck.py`,
  `tools/set_requirements.py`.

### 내부

- **TSV-canonical 워크플로 정착**. Korean 이 행 구조의 source-of-truth.
  Template TSV 는 Korean 에서 sync 받고 quality flag 는 0 으로 리셋,
  translation 비움. `Translation_TSV/Korean/Translation/Items.tsv`
  등이 diff 친화적 shadow 로 commit 됨; xlsx 는 `rebuild_xlsx.py`
  로 TSV 에서 빌드. 시트 간 이동 케이스를 위한 sheet-agnostic 키
  인덱스 도입 (sync_locale_to_korean 도구 — 현재 `d:/tmp/`, 안정화
  되면 `tools/utils/` 로 승격 예정).

- **`info.json` 스키마** (`_build_info_tab` 가 소비):
  ```
  {
    "mod_version": str,             // mod.txt
    "build_date": str,              // YYYY-MM-DD UTC
    "target_game_version": str,
    "lead_developer": [str, ...],
    "code_contributors": [str, ...],
    "acknowledgments": [str, ...],
    "locales": {
      "<locale>": {
        "translation_updated": str,
        "texture_updated": str,
        "translators": [str, ...],
        "translation_contributors": [str, ...],
        "texture_reworkers": [str, ...],
        "texture_contributors": [str, ...]
      }
    }
  }
  ```

---

## [0.5.0] — 2026-05-06 (마이너 릴리스)

이번 릴리스는 **모드 호환성 addon 시스템** 을 도입한다 — 다른 모드의
라벨 패턴을 처리하는 mod 별 런타임 helper 가 번역 엔진에 통합되며,
언어 UI 에 새 "Addons" 탭에서 ON/OFF 가능. 첫 addon 으로 ImmersiveXP
의 tooltip prefix 처리 구현.

### 추가

- **모드 호환성 addon 시스템 (`mod_addon.gd`)** — `translator.gd._apply_binding`
  에서 호출되는 런타임 helper. ModLoader 가 mount 한 mod 의 res:// 는
  Godot 의 컴파일 타임 class cache 에 등록 안 되어 `preload` / `class_name`
  사용 불가 — 따라서 mod zip 이 mount 된 후 `load("res://...")` 로 런타임
  동적 로드.

  첫 addon 으로 **ImmersiveXP prefix 처리** 구현. Oldman's Immersive
  Overhaul (modworkshop/50811) 의 `ImmersiveXP/HUD.gd:30,32` 가 매 10
  physics frame 마다 tooltip 라벨에 다음 중 하나를 prepend
  (`interactDot` 기능):
    - `"\n\n"` (조준 중)
    - `"\n.\n"` (기본, interact-dot 모드)

  Addon ON 시 `strip_immersivexp_prefix(text)` 가 prefix 를 (누적된
  형태 `"\n.\n\n.\nFire …"` 까지 포함) 모두 strip → inner text 로 9
  tier 매칭 (static / literal_scoped / pattern_scoped / literal_global
  / pattern_global / static-score / scoped-literal-score /
  scoped-pattern-score / substr) → 결과에 prefix 재부착해서 노드에 set.

- **UI Addons 탭** (F9 언어 창에 신규). Whitelist 탭과 같은 레이아웃
  — 좌측: addon 별 체크박스 + 설명 + `Used with: <mod>`, 우측:
  `Activate All` / `Deactivate All` 일괄 제어 버튼. 기본값은 모두 OFF
  — 사용자가 해당 mod 를 실제로 사용 중일 때만 활성화. addon 상태는
  `user://trans_to_vostok.cfg` 의 새 `[addons]` 섹션에 저장됨.

- **`CHANGELOG_user.md`** — 사용자용 간략 changelog (영어 + 한국어).
  사용자가 게임에서 직접 체감하는 변경만 담음. 내부 리팩터링 / 빌드
  파이프라인 / 라이선스 등은 개발자용 `CHANGELOG.md` 에만 유지. 상단
  **Known Issues** 섹션 추가 (현재: Select Language UI 자체가 일부
  번역되는 문제 — 수정 예정).

### 변경

- **개발자 CHANGELOG**: 0.4.5 substr boundary 항목 톤 정정. 이전
  표현은 "0.4 이후 번역 안 됨" 사용자 보고의 주요 원인으로 추정한 것
  — 측정 데이터 아닌 추정이었음. "안전장치 추가, 이론상 `Catalog →
  고양이alog` 같은 깨짐 발생 가능" 으로 재구성. 시뮬레이션 77 건
  결과는 실측 데이터로 유지.

### 제거

- **Whitelist 탭 "Reset to Defaults" 버튼** 제거. 모든 preset 기본값이
  `false` 라 reset 결과가 `Deactivate All` 과 동일 — redundant. 새
  Addons 탭에는 같은 판단으로 처음부터 안 둠.

### 내부

- `build_mod_package.py`: `MOD_FILES` 에 `mod_addon.gd` 추가. 그렇지
  않으면 새 모듈이 packaged mod zip 에 포함 안 되어 런타임 `load()`
  가 `File not found` 로 실패.
- `translator_ui.gd`: 신규 `_enabled_addons` 사전 + config `[addons]`
  섹션 + `_build_addons_tab(tabs)` 함수. addon 상태가 `_apply_locale`
  시점에 `translator_node.addon_*` 변수로 전달.
- `translator.gd`: 신규 `MOD_ADDON_SCRIPT` 상수 + `_mod_addon:
  GDScript` 참조 + `addon_immersivexp_prefix: bool` 플래그.
  `_initialize()` 가 addon 모듈을 런타임 로드. `_apply_binding()`
  이 `_lookup_cached()` 호출 전 prefix strip 후, 결과에 prefix
  재부착. Tier chain 자체는 변경 없음 — addon 처리는 chain **외부**
  (binding apply 레벨) 에서 발생.
- `mod.txt` 버전 `0.4.5 → 0.5.0` 업데이트.

---

## [0.4.5] — 2026-05-05 (핫픽스)

### 수정 (엔진)

- **`translator.gd`: substr 매칭에 단어 경계 안전장치 추가.**
  substr entry 614 개 중 짧은 토큰 (`Use`, `Cat`, `Day`, `Map`, `Rig`,
  `Can` 등) 다수가 `String.replace` 로 단어 한가운데에서도 매치되는
  구조 — `Catalog` 안의 `Cat`, `Daybreak` 안의 `Day`, `Fireplace`
  안의 `Fire`, `Hardware` 안의 `Hard` 같이 무관한 영어 단어 안에
  박힌 경우까지 매치 가능. 이론상 `Catalog` → `고양이alog`,
  `Daybreak` → `일break` 같은 깨진 출력 발생 가능.
  `_apply_substr` / `_replace_at_word_boundaries` 에 단어 경계 가드
  추가: 매치 위치 양 옆이 단어 문자 (`[A-Za-z0-9_]`) 가 아닐 때만
  변환. 콤마/공백으로 구분된 결합 라벨 (예:
  `Hybrid, OZ5, Leopard, Magazine`) 은 boundary 가 콤마/공백이라
  정상 변환됨. literal/static/scoped corpus 대상 시뮬레이션 결과 —
  가드 없는 동작과 가드 있는 동작이 다른 케이스 77 건 식별, **77 건
  모두 무관한 영어 단어 한가운데서 발생하는 부분 매치, 정상 매치를
  잘못 차단한 케이스 0 건**. 0.4.1 idempotency 가드는 boundary
  만으로 못 잡는 일부 사각지대용 backup 으로 유지 (예: 프랑스어
  `NVG → "Vision Nocturne (NVG)"` 처럼 괄호로 감싸진 약어 케이스).

- **`translator.gd`: `containerName` 을 `TRANSLATABLE_PROPS` 에서 제거.**
  `containerName` 은 게임 로직이 영어 문자열로 비교에 쓰는 데이터
  필드 (예: **Expanded Storage**
  [modworkshop/56126](https://modworkshop.net/mod/56126) 의
  `if container.containerName in ["Fridge", "Cabinet", ...]`). 번역된
  값을 set 하면 비교가 실패해 다른 모드의 효과가 silently 무력화됨.
  표시용 라벨은 일반 `text` 속성 변환으로 그대로 잡히므로 (예:
  `Interface.gd:408 — containerName.text = container.containerName`
  시점에 우리 binding 이 캐치) `containerName` 직접 변환이 불필요.

### 추가 (공통)

- **Trader / NPC 진영 이름 entry 등록 (substr)** — Trader, Generalist,
  Doctor, Gunsmith, Driver, Grandma, Shaman, Fisherman, Scientist
  (상인); Bandit, Guards, Military (적대 NPC 진영); Punisher (Elite
  NPC). Main 시트에 `method=substr` 로 등록 — 다른 모드가 라벨 앞에
  prefix 를 붙이는 경우에도 (예: ImmersiveXP 의 Trader UI
  `.\n\n{name}` 패턴) 변환되도록.
- Interface 시트에 있던 Doctor / Generalist / Gunsmith `literal`
  entry 는 Main 시트 substr entry 와 통합됨 (시트 간 중복 등록 제거).
- Events 시트의 일반 `Trader` 행은 `method=ignore` 로 변경 — 위 Main
  entry 와 충돌하지 않도록.

### 내부

- **`compatible_mode` → `substr_mode` 일괄 rename.** 이 플래그의 실제
  동작은 "literal + static 번역을 substr_entries 에도 추가해 substr
  fallback 매칭 범위를 넓힘" — 모드 호환성과는 무관. 동작에 맞게
  이름 정정.
  변경 범위: `translator.gd` (변수 `_compatible_mode` → `_substr_mode`,
  함수 `_apply_compatible_mode` → `_apply_substr_mode`),
  `translator_ui.gd` (변수 + UI 체크박스 라벨 + config 키),
  `locale.json` (키 `compatible` → `substr_mode_label`, 라벨 텍스트도
  한/영/프 모두 "Substr Mode" 표현으로 정비).
  **1회 마이그레이션**: 기존 `user://trans_to_vostok.cfg` 의 옛 키
  `compatible_mode` 는 다음 로드 시 자동으로 `substr_mode` 로 복사되고
  옛 키는 삭제됨. 옛 `locale.json` 의 `compatible` 키는 fallback 으로
  읽음. 사용자 측 조치 불필요.
- `mod.txt` 버전 `0.4.4 → 0.4.5` 업데이트.

---

## [0.4.4] — 2026-05-05 (Minor Fix)

### 추가 (공통)

- **Tutorial Exit** — `Modular/Doors/Transitions/Door_Tutorial_Exit`
  의 `nextZone = "Tutorial Exit"` 문자열을 등록. HUD 전환 오버레이
  (`Scripts/HUD.gd:94 — zone.text = transitionData.nextZone`) 가
  튜토리얼 맵 퇴장 시 표시하는 텍스트로, 그동안 로케일과 무관하게
  영어 그대로 노출되고 있었음.

### 내부

- `mod.txt` 버전 `0.4.3 → 0.4.4` 업데이트.

---

## [0.4.3] — 2026-05-05 (핫픽스)

### 수정 (엔진)

- **`translator.gd`: 게임 내 언어 전환 시 인벤토리 / 설정 / 이미
  생성되어 있던 UI 가 새 로케일로 갱신되지 않던 버그.** 0.4.1 / 0.4.2
  의 dedupe 가드가 도입한 `_ttv_bound_props` meta 가 `shutdown()` 에서
  제거되지 않아, 언어 전환 후 재구축 단계(`_bind_tree`) 가 meta 가
  남아 있는 모든 노드를 skip — 결과적으로 노드가 free 되고 다시
  생성될 때까지 UI 가 이전 로케일 상태로 남았음. `shutdown()` 이
  기존에 `_ttv_popup_originals` 및 `_ttv_orig_offset_*` 를 정리하던
  binding 복원 루프에서 함께 meta 를 제거하도록 수정.

### 내부

- `mod.txt` 버전 `0.4.2 → 0.4.3` 업데이트.

---

## [0.4.2] — 2026-05-05 (핫픽스)

### 수정 (엔진)

- **`translator.gd`: 0.4.1 dedupe 가드의 성능 회귀.** 0.4.1 에서 도입한
  `_bind_node` 중복 가드가 매 호출마다 `priority_bindings` 와
  `normal_bindings` 를 선형 순회 (시작 시점 약 1030 개) 하면서, 인벤토리
  / Trader UI 처럼 짧은 시간에 노드가 다수 추가되는 상황에서 실질
  O(N²) 가 되어 상자 열기 / Trader 상호작용 시 명확한 hitch 가
  발생했음. 노드별 `_ttv_bound_props` meta 조회로 교체 — O(1) 멤버십
  검사, meta 는 노드가 free 되면 자동으로 사라지므로 별도 cleanup 불필요.
  Dedupe 동작 자체는 동일.

### 내부

- `mod.txt` 버전 `0.4.1 → 0.4.2` 업데이트.

---

## [0.4.1] — 2026-05-05 (핫픽스)

### 수정 (엔진)

- **`translator.gd`: substr 번역 누적 버그.** substr 엔트리의 번역어가
  원어를 substring 으로 포함하는 경우 (예: 영어 `Hybrid` → 프랑스어
  `Hybride`), 같은 노드에 변환이 반복 적용되면서 결과가 무한 누적됨
  (`Hybride` → `Hybridee` → `Hybrideee` → …). 인벤토리에서 영향받는
  텍스트가 들어 있는 아이템 카드가 처음 등장하는 시점에 발생 — Godot
  의 `node_added` 시그널이 인벤토리 레이아웃 단계에서 reparent /
  re-attach 로 같은 노드에 대해 여러 번 fire 되며, `_bind_node` 에
  중복 가드가 없어 같은 `(node, prop)` 에 binding 이 여러 개 등록됨.
  각 binding 이 독립적으로 substr 를 재적용하면서 입력 텍스트 키
  기반 캐시를 우회한 것이 직접 원인. 두 단계로 차단:
  - **`_bind_node` dedupe** — 같은 `(node, prop)` 이 이미 등록되어
    있으면 새 binding 추가를 거부. `node_added` 가 몇 번 fire 되든
    binding 중복이 누적되지 않음.
  - **`_apply_substr` idempotency 가드** — `entry.text` 가
    `entry.translation` 의 substring 인 경우, 결과 안에 이미 변환된
    형태가 있는지 검사 (해당 occurrence 를 제거했을 때 원어가 더 이상
    안 남으면 이미 적용된 것으로 판단) 후 재적용을 거부.

### 수정 (언어: 프랑스어)

- **인트로 문단 줄바꿈 정렬** — `se déroulant` → `situé`. 한국어 / 영어
  인트로 패널과 줄바꿈을 맞추기 위해 7 자 단축 (의미는 동일).

### 내부

- `mod.txt` 버전 `0.4.0 → 0.4.1` 업데이트.

---

## [0.4.0] — 2026-05-05

이번 릴리스는 **첫 한국어 외 로케일로 프랑스어 지원**을 추가함.
내부적으로는 공개 저장소용 라이선스 / 기여 구조와 추가 언어
부트스트랩용 DeepL 기반 기계번역 파이프라인이 준비 / 테스트 중.

### 추가 (언어: 프랑스어)

- **프랑스어 번역** — DeepL 로 1차 기계번역 적용. `Translation.xlsx`
  (게임 텍스트), `Texture.xlsx` (이미지 라벨), `Glossary.xlsx`
  (번역자 참조) 모두 커버. _현재는 내부에서 관리 중이며, 커뮤니티
  검수/보정을 받기 위한 공개 저장소 및 기여 흐름은 준비 중 (아래
  추가사항 참조)._
- `Trans To Vostok/locale.json` 에 프랑스어 항목 등록 (게임 내
  언어 선택 메뉴에 노출).

### 수정 (언어: 한국어)

- 텍스트 번역의 일부 오번역 수정.
- **튜토리얼 빌보드 텍스처 오타 수정** — 접격지대 → 접경지대
  (빌보드 이미지에 표시되던 오타 라벨; 수정된 표기로 텍스처
  재출력).

### 수정 (엔진)

- **`_adjust_value_child_offset` (translator.gd): 게임 빌드 0.1.1.3
  부터 발생한 regression.** 함수가 `if value.layout_mode != 0: return`
  조건이라 `layout_mode=1` (ANCHORS) 인 Value 노드는 위치 조정 대상에서
  silently 제외되어 있었음 — Trader 패널 라벨 (`Tax:`, `Tasks:`,
  `Resupply:`) 및 게임 곳곳의 anchored Value 들 포함. 게임 빌드
  **0.1.0.0** 및 **0.1.1.1 beta** 에서는 이 Value 들이 `layout_mode=0`
  으로 출력되어 함수가 정상 동작했음. 빌드 **0.1.1.3** 부터 동일
  Value 들이 `layout_mode=1` 로 출력되며 가드에 막혀 silently 제외 —
  즉 0.1.1.3 환경에서 한국어, 프랑스어, 그리고 이 노드를 사용하는
  모든 로케일에서 위치 조정이 깨진 상태였음. 가드를 `layout_mode=0`
  (POSITION) 과 `1` (ANCHORS) 모두 허용하도록 수정 — `2` (CONTAINER)
  만 제외.

### 추가사항

- **공개 저장소 준비 진행 중** — license, NOTICE, AUTHORS, CONTRIBUTING,
  LICENSE-* 파일은 정리되었으나, 공개까지는 추가  작업 필요.

### 내부

#### 라이선스 & 기여 구조 (저장소 전용, 모드 zip 미포함)

- **`LICENSE.md`** — 마스터 라이선스 개요. 파생물(derivative)
  작성 시 보존해야 할 자료에 대한 가이드 ("fork / 재배포 시 유지할 것").
- **`LICENSE-CODE`** — 코드 (Python tools, GDScript, batch) 에 대한
  Apache License 2.0.
- **`LICENSE-TRANSLATION`** — 번역 텍스트 콘텐츠에 대한 CC BY 4.0.
  원작 영문 텍스트는 Road to Vostok 게임 개발자의 저작권으로
  남는다는 점 명시.
- **`LICENSE-TEXTURE`** — 텍스처/이미지 자산에 대한 CC BY 4.0.
  외부 데이터 출처 보존 의무 (Copernicus Sentinel-2, MML, Pixabay,
  Texturelabs 등) 와 무보증 면책 조항 포함.
- **`NOTICE`** — Apache 2.0 attribution notice (파생물에서 보존 의무).
- **`AUTHORS.md`** — 저자 / 번역자 / 기여자 명단. Translators
  섹션은 각 로케일의 xlsx 에서 자동 생성, 수동 섹션은 BEGIN/END
  마커로 보존.
- **`CONTRIBUTING.md`** — 기여 가이드. DeepL 파이프라인 워크스루,
  역할별 (번역자 / 텍스처 작업자 / 코드 기여자) credit 등록 절차 포함.

#### 도구 — DeepL 기계번역 파이프라인

- **`tools/machine_translation_deepl.py`** — DeepL 파이프라인 단일
  명령 오케스트레이터 (export → translate → import). `--limit`,
  `--dry-run`, `--deepl-lang` 옵션 지원.
- **`tools/utils/export_unique_text.py`** — `Translation.xlsx`,
  `Texture.xlsx`, `Glossary.xlsx` 에서 dedup 된 source 텍스트 추출.
  "번역 필요" 행만 (이미 번역된 행 자동 스킵 → quota 절약).
- **`tools/utils/translate_with_deepl.py`** — DeepL API 호출 도구.
  플레이스홀더 보호 (`{name}` → `<x>{name}</x>`), XML escape
  (`&`/`<`/`>`), text 기반 resume, error-row 재시도.
- **`tools/utils/import_translations.py`** — 번역 결과를 3개 로케일
  xlsx 모두에 반영. 각 행 처리: `untranslatable=1` (원문 복사),
  `method=ignore` (text 검색 + 폴백 복사), `Machine translated=1`
  플래그 세팅.

#### 도구 — credit / 메타 데이터 자동 생성

- **`tools/utils/build_translation_credit.py`** — `<locale>/Translation_Credit.md`
  자동 생성. MetaData (`Translator`, `Contributor (Translate)`) +
  Texture.xlsx (`Reworked by`, `Contributors`) 컬럼에서 집계.
- **`tools/utils/build_authors.py`** — 프로젝트 루트 `AUTHORS.md` 의
  Translators 섹션을 마커 기반으로 자동 갱신.
- **`tools/utils/build_translation_tsv.py`** — 각 로케일 xlsx 를 시트별
  TSV (`Translation_TSV/<locale>/<xlsx>/<sheet>.tsv`) 로 export. git
  diff 가독성 향상.

#### 도구 — 파서 통합

- **`tools/parse_translatables.py`** — `parse_tscn_text.py`,
  `parse_tres_text.py`, `parse_gd_text.py` 를 한 명령으로 순차 실행.

#### 도구 — 진단 통합

- **`check_untranslated.py`** 가 **`_diff_unique_id.py`** (삭제됨)
  기능 흡수 — 이제 xlsx 의 `unique_id` 가 현재 파싱된 TSV 와
  어긋난 행을 `DRIFTED` 로 보고. 이전에는 별도 도구 실행 필요했음.

#### 저장소 구조 & 파일 이동

- **도구 재배치** — `tools/` 루트는 사용자 진입점만 (`build_mod_package.py`,
  `machine_translation_deepl.py`, `parse_translatables.py`,
  `validate_translation.py`, `check_*.py`). 헬퍼는 `tools/utils/` 로 이동.
- **`Images.xlsx` → `Texture.xlsx`** — 다른 워크북(`Translation.xlsx`,
  `Glossary.xlsx`)과 일관된 단수 명사 명명.
- **`Attribution.md` → `Texture_Attribution.md`** — 범위 명확화
  (텍스처 소스 attribution 전용); 사람 credit 은 `Translation_Credit.md` 로
  분리.
- **`<locale>/runtime_tsv/`** — 런타임 TSV (translation_*.tsv,
  metadata.tsv) 를 로케일별 서브폴더로 통합.
- **Glossary** — 단일 `glossary.tsv` 큐레이션에서 로케일별
  `Glossary.xlsx` 로 이동 (Excel 친화적 편집). canonical TSV 는
  `Translation_TSV/<locale>/Glossary/` 로 자동 export.
- **`requirements.json` → `requirements.txt`** — 표준 pip 형식.
- **`set_requirements.py` 와 `unpack_and_decompile_pck.bat` 제거** —
  공개 배포 시 법적 명확성을 위함. `gdre_tools` 수동 설치 경로는
  README 에 안내.

#### 버전

- `mod.txt` 버전 `0.3.4 → 0.4.0`.

---

## [0.3.4] — 2026-04-26 (핫픽스)

### 수정 (언어: 한국어)

- **WorldMap 텍스처** — 잘못 그린 도로 가이드라인 수정.

### 내부

- `mod.txt` 버전 `0.3.3 → 0.3.4`.

---

## [0.3.3] — 2026-04-26

WorldMap 텍스처 번역 추가. 빌드 파이프라인에서 로케일별 출처 표기 문서를 자동 생성하도록 보강.

### 추가 (언어: 한국어)

- **WorldMap 텍스처 번역** — 게임 내 월드맵의 한국어 버전 (지명, 장식 오버레이 포함). 기반 이미지: 가공된 Copernicus Sentinel-2 데이터. 자산별 전체 출처는 모드 zip 의 `Trans To Vostok/Korean/Attribution.md` 위치.

### 추가사항

- **0.4.x 부터 다른 언어 지원 / 참가를 위한 레포지터리 배포 준비 중** (조금 걸릴 수도 있음).

### 내부

- **`build_attributions.py`** — `<locale>/Images.xlsx` (`File Name`, `Reworked by`, `Attribution` 컬럼) 를 읽어 `<locale>/Attribution.md` 를 생성하는 신규 도구. 이미지별 출처를 자동 정리.
- **`build_mod_package.py` 연동** — 각 로케일에 대해 attribution 생성을 자동 실행. 생성된 `Attribution.md` 가 모드 zip 안에 포함됨.
- **README** — 6번 "출처 표기 (Attribution)" 섹션 추가. 동봉된 `Attribution.md` 위치 안내.
- **진행 중 (v0.3.2 에서 이월)**: 공개 toolbox 리팩토링.
- `mod.txt` 버전 `0.3.2 → 0.3.3`.

---

## [0.3.2] — 2026-04-24

게임의 렌더링 파이프라인 개편(게임 빌드 v0.1.1.3)에 대응한 번역 업데이트.

### 추가 (공통)

- **Settings (Rendering) 엔트리 등록** — 새 렌더 해상도 버튼(`Low` / `Native`), `Image Sharpness` 라벨, `SMAA Off / On` 안티앨리어싱 토글을 xlsx 에 번역 대상 행으로 추가.
- **메인 메뉴 Compatibility 경고 등록** — Compatibility 렌더러로 실행 시 표시되는 빨간 숨김 라벨을 번역 대상 행으로 추가.
- **Killbox 메시지 번역 대상 추가** — 게임의 v0.1.1.3 업데이트에서 추가됨.

### 수정 (공통)

- **UI 속성 갱신** — 게임 업데이트로 속성이 바뀐 UI 노드의 xlsx 엔트리 갱신.

### 추가 (언어: 한국어)

- 위에서 새로 등록된 엔트리들에 대한 한국어 번역 채움 (예: `Native` → 네이티브, `Image Sharpness` → 이미지 선명도, Compatibility 경고 → 호환 모드, `Item Returned: {name}` → 아이템 회수, `Player Returned` → 플레이어 복귀).

### 수정 (언어: 한국어)

- **일부 오역 수정** — 예: 설정 / 음악 프리셋의 `Border` 는 접경 지역 BGM 을 가리키므로 국경 → 접경지대 로 수정 (그 외 문맥 기반 보정).

### 내부

- `mod.txt` 버전 `0.3.1 → 0.3.2`.
- **진행 중: 이미지 번역 템플릿 준비** — 다른 언어 기여자들이 번역 텍스처를 추가할 수 있도록 xlsx / 텍스처 교체 워크플로우 표준화 작업.
- **진행 중: 번역 toolbox 공개용 리팩토링** — 번역 toolbox 저장소 GitHub 공개를 위해 문제가 될 수 있는 부분 제거 중.
- **진행 중: 지도 한국어 번역** — 월드맵 텍스처(지명 · 범례)의 한국어 번역본 제작 중.

---

## [0.3.1] — 2026-04-22

사용자가 토글할 수 있는 **우선 순위 화이트리스트** 도입. 새로운 F9 UI 탭에서 특정 UI 영역(HUD 맵 이름, 인벤토리, 트레이더 등)을 매 프레임 번역으로 승격할지 선택 가능 — 다른 모드가 게임 텍스트를 주기적으로 덮어쓰는 경우(예: ImmersiveXP 의 HUD.gd `_physics_process` 오버라이드)에 발생하는 깜빡임에 대응.

### 추가 (엔진)

- **`translator.gd` 의 `WHITELIST_PRESETS` 시스템** — 경로 키워드 프리셋을 정의하는 const Dictionary. 각 프리셋은 `nickname`, `description`, `mod_list`, `default` 메타데이터 포함. `_is_priority_node` 가 기본 하드코딩 키워드에 더해 활성화된 프리셋도 체크. 초기 프리셋 7개: HUD Info Area (Broad), HUD Map Label, Context Menu, Container / Inventory / Equipment / Trader UI — 모두 기본 OFF.
- **런타임 필드 `enabled_whitelist`** — `translator_ui.gd` 가 초기화 시 `translator.gd` 에 전달.

### 추가 (UI)

- **F9 신규 "Whitelist" 탭** — `TabContainer` 로 기존 설정을 "General" 탭으로 래핑하고 두 번째 "Whitelist" 탭 추가. 왼쪽은 스크롤 가능한 프리셋 체크박스 리스트(설명, 연관 모드 이름(예: "Used with: ImmersiveXP"), 내부 키워드 표시). 오른쪽은 향후 사용자 커스텀 키워드 입력용으로 예약.
- **`user://trans_to_vostok.cfg` 의 `[whitelist]` 섹션** — 프리셋별 `true/false` 상태 저장. 구 버전 config 에 이름이 바뀌거나 제거된 키가 있으면 안전하게 무시(프리셋 기본값으로 복귀, crash 없음).

### 추가 (언어: 한국어)

- **`[Open]` / `[Locked]` substr 엔트리** — 다른 모드가 툴팁 텍스트 앞에 prefix 를 붙이는 경우(예: ImmersiveXP 의 `\n.\n` aim 표시로 `{containerName} [Open]` 패턴 매치 실패)에도 상태 태그가 번역되도록 독립 substr 로 추가.

### 수정 (언어: 한국어)

- **Task 설명의 `Outpost` 오역 수정** — 기존에는 음역인 "아웃포스트"로 번역되어 있었음. 게임 내 용어 의미 및 다른 등장 위치들과의 일관성을 위해 의역 "전초기지" 로 정정.

### 수정

- **ImmersiveXP 환경에서 HUD 맵 이름 깜빡임** — 원인 규명: `ImmersiveXP/HUD.gd._physics_process` 가 10 물리 프레임마다 `UpdateMap()` 호출하여 `map.text` 를 덮어씌워 translator 의 normal 배치와 경쟁. 대응: `hud/info/map` 화이트리스트 프리셋 추가(기본 OFF; 영향 받는 플레이어는 F9 → Whitelist 에서 활성화).

### 내부

- `mod.txt` 버전 `0.3.0 → 0.3.1`.
- TODO: 확인되지 않은 모드에 대응할 수 있도록 사용자 커스텀 whitelist 키워드 입력 지원 (Whitelist 탭의 오른쪽 패널).

---

## [0.3.0] — 2026-04-22

이번 릴리스는 **이미지 / 텍스처 번역** 파이프라인을 도입함. 기존 텍스트 번역 파이프라인과 별개로, 게임 내 텍스처(스프라이트, Sprite3D, MeshInstance3D 셰이더 파라미터)를 로케일별 번역본으로 교체 가능. 첫 번째 적용 대상은 한국어 튜토리얼 빌보드.

### 추가 (언어: 한국어)

- **튜토리얼 빌보드 텍스처** (17장) — `TX_Tutorial_AI / Ammo / Armor / Attachments / Equipment / Grenades / Interface / Items / Maps / Medical / Settings / Shelters / Traders / Vostok / Weapons / World` 의 한글 번역본 추가 + 타이포그래피 보정 패스. 원본 저작권 이미지는 **포함하지 않음** — 번역 레이어만 포함.
  - **참고**: 번역 텍스처는 수작업으로 재구성(hand-crafted)되었으며, 직접 그린 작업물(hand-drawing) 또는 저작권이 없는 애셋이 포함될 수 있어 일부 아이콘이 원본과 조금 다를 수 있음 (예: 튜토리얼 빌보드의 Performance 아이콘, Permadeath 해골 아이콘 등).
- **`Korean/Images.xlsx`** — 번역 이미지 자산 메타데이터 워크북 신규 (경로 / 출처 / 번역자 / 메모).

### 추가 (엔진)

- **`texture_loader.gd`** — 런타임 텍스처 교체 엔진 신규 (~287 줄). `res://Trans To Vostok/<locale>/textures/` 재귀 스캔 후 씬 트리 순회 + `node_added` 시그널로 다음 노드들을 교체:
  - `TextureRect` / `Sprite2D` / `Sprite3D` 의 `.texture`
  - `MeshInstance3D` ShaderMaterial 의 `sampler2D` 파라미터 (`shader_parameter/*`)
  
  원본 참조는 `_bindings` 에 보관되어 `shutdown()` 시 언어 전환 전 텍스처로 복원. 번역 파일이 없으면 조용히 스킵 — 크래시 없이 원본 유지.
- **`translator_ui.gd` 라이프사이클 연동** — 언어 전환 시 텍스처 로더도 shutdown → 새 로케일로 재초기화 (기존 translator 처리 방식과 동일).

### 추가 (도구)

- **`build_mod_package.py`** — 각 로케일의 `textures/` 폴더를 모드 zip 에 포함하도록 확장. (텍스처 검증 / 메타데이터 리스트 생성은 TODO 로 남겨 다음 릴리스 예정.)

### 내부

- `mod.txt` 버전 `0.2.3 → 0.3.0`.

---

## [0.2.3] — 2026-04-21

### 변경 (언어: 한국어)

- **`Kilju` 번역 조정** — 기존에는 이해를 쉽게 하기 위해 킬유(Kilju) **밀주** 로 옮겼으나, 고유 명사로서의 뉘앙스를 살리기 위해 핀란드어 원어의 음차인 **킬유** 로 변경. 대신 제너럴리스트 트레이더의 의뢰 대사에 "킬유라고 내가 젊던 시절에 집에서 담궈먹던 밀주인데…" 라는 설명을 추가하여 한국 플레이어가 "킬유" 가 어떤 술인지 맥락에서 바로 이해할 수 있도록 함. (Kilju: 핀란드식 술)
- **대사 다듬기** — 트레이더 의뢰 설명 및 이벤트 텍스트 몇 곳의 어조/표현을 자연스럽게 보정.

### 내부

- `mod.txt` 버전 `0.2.2 → 0.2.3`.

---

## [0.2.2] — 2026-04-20 (핫픽스)

### 추가

- **ModWorkshop 업데이트 연동** — `mod.txt` 에 `[updates] modworkshop=56214` 섹션 추가. MetroModLoader 의 "Check for Updates" 탭에서 ModWorkshop 에 올라간 최신 버전을 감지하고 최신 zip 을 바로 다운로드 받을 수 있게 됨.

### 내부

- `mod.txt` 버전 `0.2.1 → 0.2.2`.

---

## [0.2.1] — 2026-04-20 (핫픽스)

### 수정

- **카세트 테이프 수록곡 이름 부분 번역** — `OST - Daybreak`, `Junna - Haavakko` 같은 곡명이 xlsx 에 `method=ignore` 로 등록되어 런타임 TSV 에서 제외되어 있었고, 그 결과 Tier 9 substr 에까지 도달해 "Day" 같은 부분 문자열이 고유명사 안에서 번역되는 문제가 있었음. 원문과 동일한 값을 번역으로 두는 **pass-through literal** 로 재등록하여 Tier 4 (literal global) 에서 먼저 hit → substr 이 아예 도달하지 않도록 수정.

### 내부

- `mod.txt` 버전 `0.2.0 → 0.2.1`.
- TODO: 명시적 pass-through 용 `preserve` / `ban` method 도입 검토 (xlsx 에서 의도를 명확히 표시하기 위함).

---

## [0.2.0] — 2026-04-20

### 추가

- **F9 UI 성능 옵션 패널** — `Batch Size` / `Batch Interval` 을 런타임에 조정 가능. `user://trans_to_vostok.cfg` 에 저장됨.
- **OptionButton / PopupMenu 드롭다운 항목 번역** — 설정 창 등의 드롭다운 항목(예: 창 크기)을 `get_item_text` / `set_item_text` 로 번역. 원본은 PopupMenu meta 에 보존되어 shutdown 시 복원.
- **DEBUG_STATS 성능 계측** — 10초 주기로 apply 호출 수, 캐시 히트율, 정규식 시도 수, 바인딩 개수를 덤프 (기본 비활성).
- **`check_duplicate.py`** — 빌드 전 중복 키 사전 검사 도구. TSV 추출 없이 xlsx 만으로 빠르게 검사.
- **시트 간 중복 검사** — `validate_translation.py` 가 서로 다른 시트에 걸쳐 같은 런타임 키가 존재하는 경우를 탐지 (예: Main ↔ Interface).
- **`Languages` 서브 타이틀** — F9 UI 왼쪽에 추가.

### 수정

- **언어 전환 시 signal 중복 연결 에러** — `_initialized` 가드 추가로 `node_added` 시그널 이중 연결 방지.
- **언어 전환 시 상태 초기화 누락** — shutdown 에서 `_reset_state()` 호출로 인덱스/캐시/바인딩 전부 비움, 누적 방지.
- **번역 누락 항목** — Trader Event Descriptions 등 몇몇 누락되어 있던 한국어 번역.

### 제거

- **중복 번역 항목** (`Knife`, `Bandit` 등) — 여러 시트에 걸쳐 일관성 없이 등록되어 있던 행.

### 내부

- `mod.txt` 버전 `0.1.0 → 0.2.0`.
- `NORMAL_BATCH_INTERVAL` / `NORMAL_BATCH_SIZE` 를 `const` → `var` 로 변경하여 UI 에서 재로드 없이 즉시 조정 가능.

---

## [0.1.0] — 2026-04-17

최초 공개 테스트 버전.

### 추가

- **런타임 번역 엔진** (`translator.gd`) — N-tier (9단계) fallback 체인: static exact → scoped literal → scoped pattern → global literal → global pattern → score 기반 → substr.
- **언어 선택 UI** (`translator_ui.gd`) — 모드 로드 시 표시, `F9` 로 런타임 전환. 선택은 `user://trans_to_vostok.cfg` 에 저장.
- **호환성 모드** — 게임 업데이트로 정밀 매칭이 깨질 때를 대비한 substr 전용 fallback. F9 UI 체크박스로 on/off.
- **문자 위치 재정렬** — `Label + Value` 수동 레이아웃의 offset 을 번역 텍스트 너비에 맞춰 자동 조정 (예: Tooltip 의 "Weight: 0.8kg" 패턴).
- **한국어 번역** — UI, 툴팁, 아이템, 작업, 이벤트, 트레이더를 커버하는 초기 번역.
- **개발자 ToolBox** (Python 파이프라인):
  - `a_decompile_pck.py` — 게임 PCK 디컴파일
  - `b_extract_tscn_text.py` — `.tscn` 에서 텍스트 추출
  - `c_extract_tres_text.py` — `.tres` 에서 텍스트 추출
  - `d_check_untranslated.py` — 커버리지 리포트
  - `e_validate_translation.py` — xlsx 스키마 / 중복 / 매칭 검증
  - `f_build_runtime_tsv.py` — xlsx → 런타임 TSV 빌드
  - `g_build_mod_package.py` — 최종 모드 zip 빌드
  - `check_conflict.py` — 동일 원문 다른 번역 충돌 검사
  - `check_old_translation.py` — 옛 번역 감지
