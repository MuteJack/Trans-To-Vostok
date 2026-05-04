# Changelog — Trans To Vostok

All notable changes to this mod will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

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
