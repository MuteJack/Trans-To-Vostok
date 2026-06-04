# Trans To Vostok — Repository

A multilingual translation mod for **Road to Vostok**, with a Python-based translation pipeline (xlsx ↔ TSV ↔ runtime TSV) and a GDScript runtime that hooks into the game via Metro's ModLoader.

> The user-facing / modworkshop description README is [docs/README_USER.md](docs/README_USER.md) (Features / Install / Compatible mods / Languages / Attribution / Screenshots).

---

## Quick Start (Contributors)

Step-by-step guides live under `docs/translator/kr/` (translators) and `docs/dev/kr/` (developers / maintainers).

| Audience | Guide |
| --- | --- |
| Setup (everyone with local repo) | [docs/translator/kr/Setting_Environments.md](docs/translator/kr/Setting_Environments.md) |
| Translator (Crowdin web only) | [docs/translator/kr/Translating_using_crowdin.md](docs/translator/kr/Translating_using_crowdin.md) |
| Translator + in-game testing | [docs/translator/kr/Translating_on_Local.md](docs/translator/kr/Translating_on_Local.md) |
| Pull Request workflow | [docs/dev/kr/How_to_Pull_Request.md](docs/dev/kr/How_to_Pull_Request.md) |
| Upstream `master` sync (rebase) | [docs/dev/kr/Sync_from_Master.md](docs/dev/kr/Sync_from_Master.md) |
| Developer — Crowdin → repo sync | [docs/dev/kr/Pull_from_Crowdin.md](docs/dev/kr/Pull_from_Crowdin.md) |
| Developer — adding a new language (DeepL seed) | [docs/dev/kr/Add_new_language.md](docs/dev/kr/Add_new_language.md) |
| Developer — translation method details | [docs/dev/kr/Translation_Methods.md](docs/dev/kr/Translation_Methods.md) |
| Developer — game PCK extraction & decompile | [docs/dev/kr/Unpack_and_Decompile_Game.md](docs/dev/kr/Unpack_and_Decompile_Game.md) |
| Crediting / code contributions | [CONTRIBUTING.md](CONTRIBUTING.md) |

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

docs/translator/kr/                           # Korean translator-facing guides
├── Setting_Environments.md
├── Translating_using_crowdin.md   # Crowdin web only
├── Translating_on_Local.md        # Local clone + Crowdin (in-game testing)
├── How_to_Pull_Request.md
└── Sync_from_Master.md

docs/dev/kr/                       # Korean developer / maintainer guides
├── Pull_from_Crowdin.md           # Crowdin → repo sync (maintainer)
├── Add_new_language.md            # DeepL seed pipeline
├── Translation_Methods.md         # method semantics + matching debug
└── Unpack_and_Decompile_Game.md   # gdre_tools + parse_translatables

README/
└── image/                         # Screenshots referenced by README_USER.md via raw URL
```

---

## Tools (`tools/`)

### Entry-point orchestrators (run directly)

| Tool | Role |
| --- | --- |
| `validate_Template.py` | Phase 0 — Template validation pipeline (9 checks) |
| `validate_translation.py` | Phase 2 — locale validation pipeline (10 checks, per locale or `all`) |
| `build_mod_package.py` | Phase 3 — mod ZIP build (clear staging → dry build → ZIP → promote runtime_tsv) |
| `parse_translatables.py` | Run all 3 text-extraction parsers (`parse_tscn` / `parse_tres` / `parse_gd`) sequentially |
| `validate_texture.py` | Texture canonical TSV vs PCK extraction validation |
| `rebuild_xlsx.py` | Canonical TSV → xlsx wrapper (Translation + Texture) |
| `build_canonical_tsv.py` | xlsx → canonical TSV wrapper (Translation + Texture) |
| `push_to_crowdin.py` / `pull_from_crowdin.py` / `push_source_to_crowdin.py` | Crowdin sync |
| `translator/machine_translation_deepl.py` | DeepL pipeline for a target locale (export → translate → import) |

### Tool categories (sub-steps invoked by the orchestrators above)

| Folder | Role |
| --- | --- |
| `tools/build/` | Phase 3 build sub-steps (`build_runtime_tsv`, `check_runtime_tsv_conflict`, `build_*`, `get_texture_credits`, `pack_mod_zip`) + staging helpers (`clear_temp_build`, `copy_runtime_tsv_from_temp`) |
| `tools/validation/` | Phase 0/2 check tools (`check_required_cols`, `check_duplicates`, `check_whitespace_text`, `check_whitespace_translated`, `check_diff_with_Template`, `check_deprecated`, `check_missing`, `check_flag`, `check_method`, `check_conflict`) |
| `tools/translation/` | Per-category xlsx ↔ canonical TSV builders (`rebuild_translation_xlsx`, `rebuild_texture_xlsx`, `build_translation_tsv`, `build_texture_tsv`) + `sync_texture_schema` |
| `tools/translator/` | DeepL pipeline (`translate_with_deepl`, `import_translations`) + `helper/export_unique_text` |
| `tools/parse/` | Godot source / PCK parsers (`parse_tscn_text`, `parse_tres_text`, `parse_gd_text`, `parse_textures`, `hash_textures`) |
| `tools/helper/` | Shared utility modules (`helper_translation_common`, `helper_locale_config`, `helper_secrets`) |
| `tools/crowdin/` | Crowdin API helpers |
| `tools/configs/` | Config files (languages.json, width.json, secrets.json, parse_list_*.json) |

---

## Technical Structure

- **Runtime text engine**: `translator.gd` (GDScript autoload) — 9-tier fallback matching (static / scoped literal / scoped pattern / literal / pattern / score variants / substr)
- **Runtime texture engine**: `texture_loader.gd` (lifecycle managed by `translator_ui.gd`)
- **UI**: `translator_ui.gd` (F9 hotkey)
- **Text data**: `<locale>/runtime_tsv/translation_*.tsv` (6 buckets + metadata, built from xlsx)
- **Image data**: `<locale>/textures/**` (mirrors the original `res://` layout)
- **Matching approach**: 1:1 mapping based on Godot node structure — see the header comment in [`translator.gd`](Trans%20To%20Vostok/translator.gd) and [docs/dev/kr/Translation_Methods.md](docs/dev/kr/Translation_Methods.md) for details.

---

## License

> **Status**: License terms are still being finalized as the public release is being prepared. The structure below reflects current intent; specific wording may change.

This repository uses different licenses by asset type. See [`LICENSE.md`](LICENSE.md) for the master overview.

| Asset | License | File |
| --- | --- | --- |
| Code (Python tools, GDScript, batch) | Apache 2.0 | [`LICENSE-CODE`](LICENSE-CODE) |
| Translation text | CC BY 4.0 | [`LICENSE-TRANSLATION`](LICENSE-TRANSLATION) |
| Texture / image assets | CC BY 4.0 | [`LICENSE-TEXTURE`](LICENSE-TEXTURE) |

Attribution preserved per Apache 2.0 §4(d) is in [`NOTICE`](NOTICE); the contributor list referenced by `NOTICE` and the CC BY 4.0 licenses is in [`AUTHORS.md`](AUTHORS.md). The original Road to Vostok game's English source text and original assets remain the copyright of the game developers and are NOT licensed by this repository.

---

## Contributing

> **Status**: The contribution flow is being prepared. The links below describe the intended workflow.

- **Translators (Crowdin web)** → [docs/translator/kr/Translating_using_crowdin.md](docs/translator/kr/Translating_using_crowdin.md)
- **Translators with in-game testing** → [docs/translator/kr/Translating_on_Local.md](docs/translator/kr/Translating_on_Local.md)
- **Adding a new language** → [docs/dev/kr/Add_new_language.md](docs/dev/kr/Add_new_language.md)
- **Pull Request workflow** → [docs/dev/kr/How_to_Pull_Request.md](docs/dev/kr/How_to_Pull_Request.md)
- **Upstream sync** → [docs/dev/kr/Sync_from_Master.md](docs/dev/kr/Sync_from_Master.md)
- **Crediting / code contribution** → [CONTRIBUTING.md](CONTRIBUTING.md)

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

> 사용자 / modworkshop 페이지용 README 는 [docs/README_USER.md](docs/README_USER.md) 참조 (Features / Install / Compatible mods / Languages / Attribution / Screenshots).

---

## Quick Start (기여자용)

세부 가이드는 `docs/translator/kr/` (번역가) 와 `docs/dev/kr/` (개발자/메인테이너) 에 있습니다.

| 대상 | 가이드 |
| --- | --- |
| 셋업 (로컬 저장소 쓰는 모두) | [docs/translator/kr/Setting_Environments.md](docs/translator/kr/Setting_Environments.md) |
| 번역가 (Crowdin 웹만) | [docs/translator/kr/Translating_using_crowdin.md](docs/translator/kr/Translating_using_crowdin.md) |
| 번역가 + 인게임 테스트 | [docs/translator/kr/Translating_on_Local.md](docs/translator/kr/Translating_on_Local.md) |
| Pull Request 워크플로 | [docs/dev/kr/How_to_Pull_Request.md](docs/dev/kr/How_to_Pull_Request.md) |
| upstream `master` 동기화 (rebase) | [docs/dev/kr/Sync_from_Master.md](docs/dev/kr/Sync_from_Master.md) |
| 개발자 — Crowdin → 저장소 sync | [docs/dev/kr/Pull_from_Crowdin.md](docs/dev/kr/Pull_from_Crowdin.md) |
| 개발자 — 새 언어 추가 (DeepL 시드) | [docs/dev/kr/Add_new_language.md](docs/dev/kr/Add_new_language.md) |
| 개발자 — 번역 method 상세 | [docs/dev/kr/Translation_Methods.md](docs/dev/kr/Translation_Methods.md) |
| 개발자 — 게임 PCK 추출 & 디컴파일 | [docs/dev/kr/Unpack_and_Decompile_Game.md](docs/dev/kr/Unpack_and_Decompile_Game.md) |
| 크레딧 등록 / 코드 기여 | [CONTRIBUTING.md](CONTRIBUTING.md) |

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
├── rebuild_xlsx.py               # TSV → xlsx 재빌드 (Translation/Texture 일괄)
├── check_*.py                    # 중복 / 충돌 / 미번역 / drift 검사
└── utils/                        # 위 도구들이 호출하는 유틸리티

docs/translator/kr/                           # 한국어 번역가용 가이드
├── Setting_Environments.md
├── Translating_using_crowdin.md   # Crowdin 웹만 사용
├── Translating_on_Local.md        # 로컬 클론 + Crowdin (인게임 테스트)
├── How_to_Pull_Request.md
└── Sync_from_Master.md

docs/dev/kr/                       # 한국어 개발자/메인테이너 가이드
├── Pull_from_Crowdin.md           # Crowdin → 저장소 sync (메인테이너)
├── Add_new_language.md            # DeepL 시드 파이프라인
├── Translation_Methods.md         # method 의미 + 매칭 디버깅
└── Unpack_and_Decompile_Game.md   # gdre_tools + parse_translatables

README/
└── image/                         # README_USER.md 가 raw URL 로 참조하는 스크린샷
```

---

## 도구 (`tools/`)

### 진입점 orchestrator (직접 실행)

| 도구 | 역할 |
| --- | --- |
| `validate_Template.py` | Phase 0 — Template 검증 파이프라인 (9개 check) |
| `validate_translation.py` | Phase 2 — locale 검증 파이프라인 (10개 check, locale 단위 또는 `all`) |
| `build_mod_package.py` | Phase 3 — 모드 ZIP 빌드 (staging 정리 → dry build → ZIP → runtime_tsv promote) |
| `parse_translatables.py` | 텍스트 추출 파서 3종 (`parse_tscn` / `parse_tres` / `parse_gd`) 일괄 실행 |
| `validate_texture.py` | Texture canonical TSV vs PCK 추출 결과 검증 |
| `rebuild_xlsx.py` | canonical TSV → xlsx wrapper (Translation + Texture) |
| `build_canonical_tsv.py` | xlsx → canonical TSV wrapper (Translation + Texture) |
| `push_to_crowdin.py` / `pull_from_crowdin.py` / `push_source_to_crowdin.py` | Crowdin 동기화 |
| `translator/machine_translation_deepl.py` | 대상 locale 의 DeepL 파이프라인 (export → translate → import) |

### 도구 카테고리 (위 orchestrator 가 호출)

| 폴더 | 역할 |
| --- | --- |
| `tools/build/` | Phase 3 빌드 sub-step (`build_runtime_tsv`, `check_runtime_tsv_conflict`, `build_*`, `get_texture_credits`, `pack_mod_zip`) + staging helper (`clear_temp_build`, `copy_runtime_tsv_from_temp`) |
| `tools/validation/` | Phase 0/2 검증 도구 (`check_required_cols`, `check_duplicates`, `check_whitespace_text`, `check_whitespace_translated`, `check_diff_with_Template`, `check_deprecated`, `check_missing`, `check_flag`, `check_method`, `check_conflict`) |
| `tools/translation/` | 카테고리별 xlsx ↔ canonical TSV 빌더 (`rebuild_translation_xlsx`, `rebuild_texture_xlsx`, `build_translation_tsv`, `build_texture_tsv`) + `sync_texture_schema` |
| `tools/translator/` | DeepL 파이프라인 (`translate_with_deepl`, `import_translations`) + `helper/export_unique_text` |
| `tools/parse/` | Godot 소스 / PCK 파서 (`parse_tscn_text`, `parse_tres_text`, `parse_gd_text`, `parse_textures`, `hash_textures`) |
| `tools/helper/` | 공통 utility module (`helper_translation_common`, `helper_locale_config`, `helper_secrets`) |
| `tools/crowdin/` | Crowdin API helper |
| `tools/configs/` | 설정 파일 (languages.json, width.json, secrets.json, parse_list_*.json) |

---

## 기술 구조

- **런타임 텍스트 엔진**: `translator.gd` (GDScript autoload) — 9-tier fallback 매칭 (static / scoped literal / scoped pattern / literal / pattern / score variants / substr)
- **런타임 텍스처 엔진**: `texture_loader.gd` (라이프사이클은 `translator_ui.gd` 가 관리)
- **UI**: `translator_ui.gd` (F9 단축키)
- **텍스트 데이터**: `<locale>/runtime_tsv/translation_*.tsv` (xlsx 에서 빌드된 6개 버킷 + metadata)
- **이미지 데이터**: `<locale>/textures/**` (원본 `res://` 구조 미러링)
- **매칭 방식**: Godot 노드 구조 기반 1:1 매핑 — 자세한 동작은 [`translator.gd`](Trans%20To%20Vostok/translator.gd) 상단 주석 + [docs/dev/kr/Translation_Methods.md](docs/dev/kr/Translation_Methods.md) 참조

---

## 라이선스

> **상태**: 저장소가 아직 공개 전이라 라이선스 내용은 정리 중. 아래 구조는 현재 의도이며, 공개 시점에 표현 / 구체 라이선스가 수정될 수 있음.

자산 유형별로 라이선스가 다릅니다. 마스터 개요는 [`LICENSE.md`](LICENSE.md).

| 자산 | 라이선스 | 파일 |
| --- | --- | --- |
| 코드 (Python tools, GDScript, batch) | Apache 2.0 | [`LICENSE-CODE`](LICENSE-CODE) |
| 번역 텍스트 | CC BY 4.0 | [`LICENSE-TRANSLATION`](LICENSE-TRANSLATION) |
| 텍스처 / 이미지 자산 | CC BY 4.0 | [`LICENSE-TEXTURE`](LICENSE-TEXTURE) |

Apache 2.0 §4(d) 의 attribution 보존 대상은 [`NOTICE`](NOTICE) 에 있고, `NOTICE` 와 CC BY 4.0 라이선스가 참조하는 기여자 명단은 [`AUTHORS.md`](AUTHORS.md). 원작 Road to Vostok 게임의 영문 텍스트와 원본 자산은 게임 개발사의 저작권으로 남으며 본 저장소의 라이선스 대상이 아님.

---

## 기여하기

> **상태**: 기여 흐름은 아직 개방 전 — 공개 저장소 준비 중. 아래 안내는 의도된 워크플로.

- **번역가 (Crowdin 웹)** → [docs/translator/kr/Translating_using_crowdin.md](docs/translator/kr/Translating_using_crowdin.md)
- **번역가 + 인게임 테스트** → [docs/translator/kr/Translating_on_Local.md](docs/translator/kr/Translating_on_Local.md)
- **새 언어 추가** → [docs/dev/kr/Add_new_language.md](docs/dev/kr/Add_new_language.md)
- **Pull Request 흐름** → [docs/dev/kr/How_to_Pull_Request.md](docs/dev/kr/How_to_Pull_Request.md)
- **upstream 동기화** → [docs/dev/kr/Sync_from_Master.md](docs/dev/kr/Sync_from_Master.md)
- **크레딧 등록 / 코드 기여** → [CONTRIBUTING.md](CONTRIBUTING.md)

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
