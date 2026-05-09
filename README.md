# Trans To Vostok — Repository

A multilingual translation mod for **Road to Vostok**, with a Python-based translation pipeline (xlsx ↔ TSV ↔ runtime TSV) and a GDScript runtime that hooks into the game via Metro's ModLoader.

> The user-facing / modworkshop description README is [README_USER.md](README_USER.md) (Features / Install / Compatible mods / Languages / Attribution / Screenshots).

---

## Quick Start (Contributors)

Step-by-step guides live under `README/` (Korean).

| Step | Guide |
| --- | --- |
| 0 | Environment setup (Excel / Python / Git / Fork & Clone) — [README/0_Setting_Environments_kr.md](README/0_Setting_Environments_kr.md) |
| 1 | (Optional) Game PCK extraction & decompile — [README/1_unpack_and_decompile_game_kr.md](README/1_unpack_and_decompile_game_kr.md) |
| 2 | Adding a new language (DeepL initial pass) — [README/2_Add_new_language_kr.md](README/2_Add_new_language_kr.md) |
| 3 | How to translate (general) — [README/3_How_to_Translate_kr.md](README/3_How_to_Translate_kr.md) |
| 3+ | How to translate (developer / method details) — [README/3_How_to_Translate_kr(For Developers).md](README/3_How_to_Translate_kr%28For%20Developers%29.md) |
| 4 | Pull Request workflow — [README/4_How_to_Pull_Request_kr.md](README/4_How_to_Pull_Request_kr.md) |
| 5 | Upstream `master` sync (rebase) — [README/5_How_to_Update_from_MasterBranch_kr.md](README/5_How_to_Update_from_MasterBranch_kr.md) |
| general | Crediting / code contributions — [README/CONTRIBUTING.md](README/CONTRIBUTING.md) |

Basic build commands:

```powershell
pip install -r tools/requirements.txt
python tools/build_mod_package.py Korean         # specify locale
```

If `parsed_text/` is absent, validation steps that depend on it are auto-skipped (see §1 guide for full validation setup).

---

## Repository Layout

```
Translations/                     # Authoring + canonical translation data
└── <locale>/                     # Each locale (Korean, French, Template, …)
    ├── Translation.xlsx          # Text translations (human-edited, gitignored)
    ├── Glossary.xlsx             # Glossary (manually curated, gitignored)
    ├── Texture.xlsx              # Texture metadata + attribution (gitignored)
    └── <category>/*.tsv          # Canonical TSV (committed, git-diff-friendly)

Trans To Vostok/                  # Mod package root (this is what goes into the zip)
├── translator.gd                 # Runtime text engine (GDScript autoload)
├── translator_ui.gd              # F9 language selection UI
├── texture_loader.gd             # Runtime texture replacement engine
├── mod_addon.gd                  # Mod compatibility helper
├── locale.json                   # Registered locale list
└── <locale>/                     # Per-locale runtime artifacts
    ├── runtime_tsv/              # Build output (loaded by translator.gd)
    ├── textures/                 # Translated textures (optional)
    ├── Translation_Credit.md     # Generated credits
    └── Texture_Attribution.md    # Generated attribution

tools/                             # Python build / validation / helper tools
├── build_mod_package.py          # Main build (validate + package)
├── validate_translation.py       # xlsx validation (parsed_text-dependent and -independent)
├── parse_translatables.py        # Parse PCK extract → parsed_text/
├── machine_translation_deepl.py  # DeepL initial-pass pipeline
├── rebuild_xlsx.py               # TSV → xlsx rebuild (3 categories at once)
├── check_*.py                    # Duplicate / conflict / coverage / drift checks
└── utils/                        # Utilities invoked by the above

README/                            # Korean contributor guide series (see Quick Start)
├── 0_Setting_Environments_kr.md
├── 1_unpack_and_decompile_game_kr.md
├── 2_Add_new_language_kr.md
├── 3_How_to_Translate_kr.md
├── 3_How_to_Translate_kr(For Developers).md
├── 4_How_to_Pull_Request_kr.md
├── 5_How_to_Update_from_MasterBranch_kr.md
├── CONTRIBUTING.md                # Crediting / new-language DeepL guide (English)
└── image/                         # Screenshots used by README_USER.md
```

---

## Tools (`tools/`)

### Entry-point tools (run directly)

| Tool | Role |
| --- | --- |
| `build_mod_package.py` | Build final mod zip (validate + textures + runtime_tsv) |
| `parse_translatables.py` | Run all 3 text-extraction parsers (`parse_tscn` / `parse_tres` / `parse_gd`) sequentially |
| `machine_translation_deepl.py` | DeepL pipeline for a target locale (export → translate → import) |
| `validate_translation.py` | xlsx schema / duplicate / match validation (partial mode if parsed_text is absent) |
| `check_untranslated.py` | Translation gap / coverage report (incl. `DRIFTED` rows) |
| `check_duplicate.py` | Pre-build duplicate-key detector (xlsx-only) |
| `check_conflict.py` | Conflict detection (same source text, different translations) |
| `check_old_translation.py` | Detect stale translations from removed game content |
| `rebuild_xlsx.py` | TSV → xlsx for a locale (Translation / Glossary / Texture batch) |

### Utilities (`tools/utils/` — invoked by the above)

| Tool | Role |
| --- | --- |
| `utils/parse_tscn_text.py` | Parse `.tscn` scenes for translatable text |
| `utils/parse_tres_text.py` | Parse `.tres` resources for translatable text |
| `utils/parse_gd_text.py` | Parse `.gd` scripts for UI strings |
| `utils/export_unique_text.py` | Extract deduplicated source texts from a locale's xlsx |
| `utils/translate_with_deepl.py` | DeepL API caller (placeholder protection + XML escape) |
| `utils/import_translations.py` | Write DeepL results back into the locale's xlsx files |
| `utils/build_runtime_tsv.py` | xlsx → runtime TSV (after validation passes) |
| `utils/build_attributions.py` | `Texture.xlsx` → `Texture_Attribution.md` |
| `utils/build_translation_credit.py` | Per-locale `Translation_Credit.md` |
| `utils/build_authors.py` | Update the auto-generated Translators section of `AUTHORS.md` |
| `utils/build_translation_tsv.py` | Locale xlsx → per-sheet TSV under `Translations/<locale>/<file>/` (git-diff visibility) |
| `utils/build_mod_info.py` | Generate `<pkg_root>/info.json` (version + build date + contributors) for the F9 Info tab |
| `utils/rebuild_translation_xlsx.py` | TSV → Translation.xlsx (formatting / widths / conditional formatting applied) |
| `utils/rebuild_glossary_xlsx.py` | TSV → Glossary.xlsx |
| `utils/rebuild_texture_xlsx.py` | TSV → Texture.xlsx |

---

## Technical Structure

- **Runtime text engine**: `translator.gd` (GDScript autoload) — 9-tier fallback matching (static / scoped literal / scoped pattern / literal / pattern / score variants / substr)
- **Runtime texture engine**: `texture_loader.gd` (lifecycle managed by `translator_ui.gd`)
- **UI**: `translator_ui.gd` (F9 hotkey)
- **Text data**: `<locale>/runtime_tsv/translation_*.tsv` (6 buckets + metadata, built from xlsx)
- **Image data**: `<locale>/textures/**` (mirrors the original `res://` layout)
- **Matching approach**: 1:1 mapping based on Godot node structure — see the header comment in [`translator.gd`](Trans%20To%20Vostok/translator.gd) and [README/3_How_to_Translate_kr(For Developers).md](README/3_How_to_Translate_kr%28For%20Developers%29.md) for details.

---

## License

> **Status**: License terms are still being finalized as the public release is being prepared. The structure below reflects current intent; specific wording may change.

This repository uses different licenses by asset type. See [`LICENSE.md`](LICENSE.md) for the master overview.

| Asset | License | File |
| --- | --- | --- |
| Code (Python tools, GDScript, batch) | Apache 2.0 | [`LICENSE-CODE`](LICENSE-CODE) |
| Translation text (Translation, Glossary) | CC BY 4.0 | [`LICENSE-TRANSLATION`](LICENSE-TRANSLATION) |
| Texture / image assets | CC BY 4.0 | [`LICENSE-TEXTURE`](LICENSE-TEXTURE) |

Attribution preserved per Apache 2.0 §4(d) is in [`NOTICE`](NOTICE); the contributor list referenced by `NOTICE` and the CC BY 4.0 licenses is in [`AUTHORS.md`](AUTHORS.md). The original Road to Vostok game's English source text and original assets remain the copyright of the game developers and are NOT licensed by this repository.

---

## Contributing

> **Status**: The contribution flow is being prepared. The links below describe the intended workflow.

- **Translators (Excel editing)** → [README/3_How_to_Translate_kr.md](README/3_How_to_Translate_kr.md)
- **Adding a new language** → [README/2_Add_new_language_kr.md](README/2_Add_new_language_kr.md)
- **Pull Request workflow** → [README/4_How_to_Pull_Request_kr.md](README/4_How_to_Pull_Request_kr.md)
- **Upstream sync** → [README/5_How_to_Update_from_MasterBranch_kr.md](README/5_How_to_Update_from_MasterBranch_kr.md)
- **Crediting / code contribution / DeepL pipeline** → [README/CONTRIBUTING.md](README/CONTRIBUTING.md)

---

## Roadmap

### Feature Implementation

* [X] Runtime translation engine prototype (N-tier fallback)
* [X] Translation mod prototype targeting game version 1.0.0
* [X] Language selection UI
* [X] Text position realignment
* [X] UI performance options (v0.2.0)
* [X] Partial image replacement — runtime texture loader + Korean tutorial billboards (v0.3.0)
* [X] Priority whitelist — per-frame translation presets for mod compatibility (v0.3.1)
* [X] Tested against game 1.0.0
* [X] Tested against game 0.1.1.3
* [ ] Additional language prototypes + game 0.1.1.3 testing
* [ ] Texture metadata list + validation tooling (v0.3.0 carry-over)
* [X] User-custom whitelist keyword input (v0.3.1 carry-over)
* [ ] Translator optimization
* [ ] Debug mode

### Translation Support

* [X] Korean translation template complete
* [X] DeepL pipeline + French initial pass (v0.4.0)
* [X] Translation ToolBox prototype published on GitHub
* [ ] Translator recruitment / GitHub collaboration (repository pending)
* [ ] ToolBox / manual prototype publication
* [ ] Additional languages (Japanese, Chinese, German, …)
* [ ] Translation workflow for stable / beta game branches (per-version diff, release tagging)

---

========================================

# Trans To Vostok — 저장소

**Road to Vostok** 의 다국어 번역 모드. Python 기반 번역 파이프라인 (xlsx ↔ TSV ↔ runtime TSV) 과 Metro's ModLoader 를 통해 게임에 후킹되는 GDScript 런타임으로 구성.

> 사용자 / modworkshop 페이지용 README 는 [README_USER.md](README_USER.md) 참조 (Features / Install / Compatible mods / Languages / Attribution / Screenshots).

---

## Quick Start (기여자용)

세부 가이드는 `README/` 폴더의 한국어 매뉴얼 시리즈 참조.

| 단계 | 가이드 |
| --- | --- |
| 0 | 환경 셋업 (Excel / Python / Git / Fork & Clone) — [README/0_Setting_Environments_kr.md](README/0_Setting_Environments_kr.md) |
| 1 | (선택) 게임 PCK 추출 & 디컴파일 — [README/1_unpack_and_decompile_game_kr.md](README/1_unpack_and_decompile_game_kr.md) |
| 2 | 새 언어 추가 (DeepL 1차 기계번역) — [README/2_Add_new_language_kr.md](README/2_Add_new_language_kr.md) |
| 3 | 번역 작업 (일반) — [README/3_How_to_Translate_kr.md](README/3_How_to_Translate_kr.md) |
| 3+ | 번역 작업 (개발자 / method 상세) — [README/3_How_to_Translate_kr(For Developers).md](README/3_How_to_Translate_kr%28For%20Developers%29.md) |
| 4 | Pull Request 워크플로 — [README/4_How_to_Pull_Request_kr.md](README/4_How_to_Pull_Request_kr.md) |
| 5 | upstream `master` 동기화 (rebase) — [README/5_How_to_Update_from_MasterBranch_kr.md](README/5_How_to_Update_from_MasterBranch_kr.md) |
| 일반 | 크레딧 등록 / 코드 기여 — [README/CONTRIBUTING.md](README/CONTRIBUTING.md) |

기본 빌드 명령:

```powershell
pip install -r tools/requirements.txt
python tools/build_mod_package.py Korean         # locale 지정
```

`parsed_text/` 가 없으면 일부 검증이 자동 스킵됨. 전체 validation 활성화는 §1 가이드 참조.

---

## 저장소 구조

```
Translations/                     # 번역 작업 데이터 (authoring + canonical)
└── <locale>/                     # 각 locale (Korean, French, Template, …)
    ├── Translation.xlsx          # 텍스트 번역 (사람 편집 대상, gitignored)
    ├── Glossary.xlsx             # 용어집 (수동 큐레이트, gitignored)
    ├── Texture.xlsx              # 텍스처 metadata + attribution (gitignored)
    └── <category>/*.tsv          # canonical TSV (committed, git diff 친화적)

Trans To Vostok/                  # 모드 패키지 루트 (zip에 들어가는 부분)
├── translator.gd                 # 런타임 텍스트 엔진 (GDScript autoload)
├── translator_ui.gd              # F9 언어 선택 UI
├── texture_loader.gd             # 런타임 텍스처 교체 엔진
├── mod_addon.gd                  # mod 호환성 helper
├── locale.json                   # 등록된 locale 목록
└── <locale>/                     # locale별 런타임 산출물
    ├── runtime_tsv/              # 빌드 산출물 (translator.gd 가 로드)
    ├── textures/                 # 번역 텍스처 (선택)
    ├── Translation_Credit.md     # 자동 생성 크레딧
    └── Texture_Attribution.md    # 자동 생성 attribution

tools/                             # Python 빌드 / 검증 / 보조 도구
├── build_mod_package.py          # 메인 빌드 (검증 + 패키징)
├── validate_translation.py       # xlsx 검증 (parsed_text 의존 / 비의존 모두)
├── parse_translatables.py        # PCK 추출본을 파싱 → parsed_text/
├── machine_translation_deepl.py  # DeepL 1차 번역 파이프라인
├── rebuild_xlsx.py               # TSV → xlsx 재빌드 (3개 카테고리 일괄)
├── check_*.py                    # 중복 / 충돌 / 미번역 / drift 검사
└── utils/                        # 위 도구들이 호출하는 유틸리티

README/                            # 한국어 매뉴얼 시리즈 (위 Quick Start 표)
├── 0_Setting_Environments_kr.md
├── 1_unpack_and_decompile_game_kr.md
├── 2_Add_new_language_kr.md
├── 3_How_to_Translate_kr.md
├── 3_How_to_Translate_kr(For Developers).md
├── 4_How_to_Pull_Request_kr.md
├── 5_How_to_Update_from_MasterBranch_kr.md
├── CONTRIBUTING.md                # 크레딧 등록 / 새 언어 DeepL 가이드 (영문)
└── image/                         # README_USER.md 의 스크린샷
```

---

## 도구 (`tools/`)

### 진입점 도구 (직접 실행)

| 도구 | 역할 |
| --- | --- |
| `build_mod_package.py` | 최종 모드 zip 패키지 빌드 (검증 + textures + runtime_tsv) |
| `parse_translatables.py` | 텍스트 추출 파서 3 종 (`parse_tscn` / `parse_tres` / `parse_gd`) 일괄 실행 |
| `machine_translation_deepl.py` | 대상 locale 의 DeepL 파이프라인 (export → translate → import) |
| `validate_translation.py` | xlsx 스키마 / 중복 / 매칭 검증 (parsed_text 부재 시 partial mode) |
| `check_untranslated.py` | 번역 누락 / 커버리지 리포트 (`DRIFTED` 행 포함) |
| `check_duplicate.py` | 빌드 전 중복 키 사전 검사 (xlsx 단독) |
| `check_conflict.py` | 번역 충돌 검사 (같은 원문, 다른 번역) |
| `check_old_translation.py` | 게임 업데이트로 사라진 옛 번역 감지 |
| `rebuild_xlsx.py` | locale 의 TSV → xlsx 일괄 재빌드 (Translation/Glossary/Texture) |

### 유틸리티 (`tools/utils/` — 위 도구가 호출)

| 도구 | 역할 |
| --- | --- |
| `utils/parse_tscn_text.py` | `.tscn` 씬 파일 → 번역 대상 텍스트 추출 |
| `utils/parse_tres_text.py` | `.tres` 리소스 → 번역 대상 텍스트 추출 |
| `utils/parse_gd_text.py` | `.gd` 스크립트 → UI 문자열 추출 |
| `utils/export_unique_text.py` | locale xlsx 에서 중복 제거된 source 텍스트 추출 |
| `utils/translate_with_deepl.py` | DeepL API 호출 (placeholder 보호 + XML escape) |
| `utils/import_translations.py` | DeepL 결과를 locale xlsx 에 반영 |
| `utils/build_runtime_tsv.py` | xlsx → 런타임 TSV 빌드 (검증 통과 시) |
| `utils/build_attributions.py` | `Texture.xlsx` → `Texture_Attribution.md` 자동 생성 |
| `utils/build_translation_credit.py` | locale 별 `Translation_Credit.md` 생성 |
| `utils/build_authors.py` | `AUTHORS.md` 의 자동 생성 Translators 섹션 갱신 |
| `utils/build_translation_tsv.py` | locale xlsx → 시트별 TSV (`Translations/<locale>/<file>/`) — git diff 가독성 |
| `utils/build_mod_info.py` | F9 Info 탭이 사용하는 `<pkg_root>/info.json` 생성 (version + build date + contributors) |
| `utils/rebuild_translation_xlsx.py` | TSV → Translation.xlsx (서식 / 너비 / 조건부 서식 일괄 적용) |
| `utils/rebuild_glossary_xlsx.py` | TSV → Glossary.xlsx |
| `utils/rebuild_texture_xlsx.py` | TSV → Texture.xlsx |

---

## 기술 구조

- **런타임 텍스트 엔진**: `translator.gd` (GDScript autoload) — 9-tier fallback 매칭 (static / scoped literal / scoped pattern / literal / pattern / score variants / substr)
- **런타임 텍스처 엔진**: `texture_loader.gd` (라이프사이클은 `translator_ui.gd` 가 관리)
- **UI**: `translator_ui.gd` (F9 단축키)
- **텍스트 데이터**: `<locale>/runtime_tsv/translation_*.tsv` (xlsx 에서 빌드된 6개 버킷 + metadata)
- **이미지 데이터**: `<locale>/textures/**` (원본 `res://` 구조 미러링)
- **매칭 방식**: Godot 노드 구조 기반 1:1 매핑 — 자세한 동작은 [`translator.gd`](Trans%20To%20Vostok/translator.gd) 상단 주석 + [README/3_How_to_Translate_kr(For Developers).md](README/3_How_to_Translate_kr%28For%20Developers%29.md) 참조

---

## 라이선스

> **상태**: 저장소가 아직 공개 전이라 라이선스 내용은 정리 중. 아래 구조는 현재 의도이며, 공개 시점에 표현 / 구체 라이선스가 수정될 수 있음.

자산 유형별로 라이선스가 다릅니다. 마스터 개요는 [`LICENSE.md`](LICENSE.md).

| 자산 | 라이선스 | 파일 |
| --- | --- | --- |
| 코드 (Python tools, GDScript, batch) | Apache 2.0 | [`LICENSE-CODE`](LICENSE-CODE) |
| 번역 텍스트 (Translation, Glossary) | CC BY 4.0 | [`LICENSE-TRANSLATION`](LICENSE-TRANSLATION) |
| 텍스처 / 이미지 자산 | CC BY 4.0 | [`LICENSE-TEXTURE`](LICENSE-TEXTURE) |

Apache 2.0 §4(d) 의 attribution 보존 대상은 [`NOTICE`](NOTICE) 에 있고, `NOTICE` 와 CC BY 4.0 라이선스가 참조하는 기여자 명단은 [`AUTHORS.md`](AUTHORS.md). 원작 Road to Vostok 게임의 영문 텍스트와 원본 자산은 게임 개발사의 저작권으로 남으며 본 저장소의 라이선스 대상이 아님.

---

## 기여하기

> **상태**: 기여 흐름은 아직 개방 전 — 공개 저장소 준비 중. 아래 안내는 의도된 워크플로.

- **번역가 (Excel 편집)** → [README/3_How_to_Translate_kr.md](README/3_How_to_Translate_kr.md)
- **새 언어 추가** → [README/2_Add_new_language_kr.md](README/2_Add_new_language_kr.md)
- **Pull Request 흐름** → [README/4_How_to_Pull_Request_kr.md](README/4_How_to_Pull_Request_kr.md)
- **upstream 동기화** → [README/5_How_to_Update_from_MasterBranch_kr.md](README/5_How_to_Update_from_MasterBranch_kr.md)
- **크레딧 등록 / 코드 기여 / DeepL 파이프라인** → [README/CONTRIBUTING.md](README/CONTRIBUTING.md)

---

## 로드맵

### 기능 구현

* [X] 런타임 번역 엔진 프로토타입 (N-tier fallback)
* [X] 1.0.0 버전을 대상으로 번역 모드 prototype 개발
* [X] 언어 선택 UI 추가
* [X] 문자 위치 재정렬 기능
* [X] UI 성능 옵션 (v0.2.0)
* [X] 일부 이미지 교체 기능 — 런타임 텍스처 로더 + 한국어 튜토리얼 빌보드 (v0.3.0)
* [X] 우선 순위 화이트리스트 — 모드 호환용 매 프레임 번역 프리셋 (v0.3.1)
* [X] 게임 1.0.0 대상 테스트
* [X] 게임 0.1.1.3 테스트
* [ ] 기타 언어 prototype + 게임 0.1.1.3 테스트
* [ ] 텍스처 metadata 리스트 + 검증 도구 보강 (v0.3.0 carry-over)
* [X] 사용자 커스텀 whitelist 키워드 입력 (v0.3.1 carry-over)
* [ ] Translator 최적화
* [ ] 디버그 모드

### 번역 지원

* [X] Korean 번역 기준 template 완성
* [X] DeepL 파이프라인 + French 1차 번역 (v0.4.0)
* [X] 번역 ToolBox prototype GitHub 공개
* [ ] 번역가 모집 / GitHub 협업 (Repository 정비중)
* [ ] ToolBox / 매뉴얼 prototype 완성 후 GitHub 공개
* [ ] 추가 언어 (Japanese, Chinese, German, …)
* [ ] 정식 / 베타 버전에 대한 번역 workflow (버전별 diff, 릴리스 태깅)
