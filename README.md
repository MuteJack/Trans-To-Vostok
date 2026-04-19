# Trans To Vostok

A multilingual translation mod for Road to Vostok.

> **NOTE:** *This mode is currently under development. .*

- Currently supported languages: **English** (game default), **Korean** (in development)
- Development is focused on Korean translation and the ToolBox first.
- Detailed manuals and the ToolBox will be published on GitHub once development reaches a sufficient milestone.

## 1. Introduction

**Trans To Vostok** is a mod under development to support multilingual localization for Road to Vostok.
It aims to deliver **complete, non-missing translation** across all translatable game content — UI, items, quests, interactions, and more.

## 2. Key Features

1. **Game Translation** (core feature)
   - Translates in-game UI, tooltips, item names, event descriptions, trader dialogue, and more.
2. **UI Support**
   - Opens a language selection UI via **`F9`** hotkey when the mod is loaded.
   - Switch languages at runtime without restarting the game.
   - Compatibility mode toggle provided (see below).
3. **Text Position Realignment**
   - When translation changes text length, **on-screen layout can shift** (e.g., `A: B` layouts like tooltip's "Weight: 0.8kg").
   - This mod measures the translated label's actual font width and auto-adjusts the Value node's offset.
     - Targets: `Label` nodes with a child `Value` Label (manual positioning)
     - Auto-aligns "label: [value]" patterns in Tooltip, inventory stats, etc.
     - **Disabled in Compatibility Mode** — avoids interfering with game scene structure.
4. **1:1 Property-Based Translation** (Precision Matching)
   - Instead of simple text substitution, translation targets are specified directly via **Godot node structural identifiers**:
   - ``(location, parent, name, type, text) → translation``
     - `location`: Scene file path (e.g., `UI/Interface`)
     - `parent`: Parent node path within the scene (e.g., `Tools/Notes`)
     - `name`: Node name (e.g., `Hint`)
     - `type`: Godot node class (e.g., `Label`)
     - `text`: Original source text
   - **The same word can be translated differently depending on which UI/node it appears in** — prevents mismatches, enables context-aware translation.
     - Example: NVG (Night Vision Goggle) can show the full name in settings but "NVG" everywhere else.
5. **N-Tier Fallback Matching**
   - Looks up translations through 9 tiers, from specific context to generic substitution:
   - Current implementation (subject to change):
     | Tier | Match Method                                 | Notes                                |
     | ---- | -------------------------------------------- | ------------------------------------ |
     | 1    | **static exact** — all 5 fields match | All fields match exactly             |
     | 2    | **scoped literal exact**               | Dynamic text (runtime assignment)    |
     | 3    | **scoped pattern exact**               | Regex + scene context                |
     | 4    | **literal global**                     | Full text match (global)             |
     | 5    | **pattern global**                     | Regex (global)                       |
     | 6    | **static score**                       | Partial context match (+8/+4/+2/+1)  |
     | 7    | **scoped literal score**               | Dynamic text, partial context        |
     | 8    | **scoped pattern score**               | Regex + partial context              |
     | 9    | **substr**                             | Substring substitution (last resort) |
6. **Compatibility Mode**
   - **Temporary fallback when game updates break matching structure.**
   - Treats all translation data as **sub-strings (dictionary)** via substring substitution.
   - Lower precision, but largely unaffected by scene structure changes.
   - Lets players keep using translations until the mod is updated.
   - Toggle on/off via checkbox in the F9 UI.

## 3. Installation

> **NOTE:** This mod requires a mod loader such as MetroModLoader.

1. Install **MetroModLoader** or **VostokMods** for Godot: https://modworkshop.net/mod/55623
2. Download `Trans To Vostok.zip` and copy it into the game's `mods/` folder.
   e.g., `C:\Program Files (x86)\Steam\steamapps\common\Road to Vostok\mods\`
   or: `D:\SteamLibrary\steamapps\common\Road to Vostok\mods\`
3. Launch the game — it starts in the default language (English).
4. Press **F9** to open the language selection UI and switch to your preferred language.

## 4. Supported Languages

1. **English**: The game's default language.
2. **Korean (한국어)**: Currently in development/testing.
3. Other languages will be supported gradually after the ToolBox development is complete.

To request additional languages, please submit a GitHub issue (to be published).

## 5. TODO (Roadmap)

### 5.1. Feature Implementation

* [X] Runtime translation engine prototype (N-tier fallback)
* [X] Prototype development targeting game version 1.0.0
* [X] Language selection UI added
* [X] Text position realignment added
* [X] Compatibility mode added
* [X] Performance options added to UI (added in v0.2.0)
* [ ] Testing current mod build against game 1.0.0 (in progress)
* [ ] Partial image replacement support (e.g., Tutorial billboards)
* [ ] Translator optimization
* [ ] Debug mode (planned)

### 5.2. Translation Support

* [X] Complete translation template based on Korean
* [ ] After template cleanup, provide temporary machine-translated support for other languages
* [ ] Publish translation ToolBox prototype on GitHub
* [ ] Recruit translators or collaborate via GitHub
* [ ] Publish ToolBox and manual prototype on GitHub
* [ ] Create branches for additional languages (Japanese, Chinese, German, etc.)

---

## Developer/Translator's ToolBox (Not released yet)

The mod repository includes **Python tools** for the translation pipeline:

| Tool                          | Role                                                      |
| ----------------------------- | --------------------------------------------------------- |
| `a_decompile_pck.py`        | Decompile the game PCK file                               |
| `b_extract_tscn_text.py`    | Extract translatable text from `.tscn` scene files      |
| `c_extract_tres_text.py`    | Extract text from `.tres` resource files                |
| `d_check_untranslated.py`   | Translation gap / coverage report                         |
| `e_validate_translation.py` | xlsx schema / duplicate / match validation                |
| `f_build_runtime_tsv.py`    | Build runtime TSV from xlsx                               |
| `g_build_mod_package.py`    | Build final mod zip package                               |
| `check_conflict.py`         | Conflict check (same source text, different translations) |
| `check_old_translation.py`  | Detect stale translations from removed game content       |

**Detailed ToolBox manual will be published on GitHub after development is complete.**

---

## Technical Structure

- **Runtime engine**: `translator.gd` (GDScript autoload)
- **UI**: `translator_ui.gd` (language selection UI triggered by F9)
- **Translation data**: `<locale>/translation_*.tsv` (built from xlsx)
- **Matching approach**: 1:1 mapping based on Godot node structure (see the header comment in [`translator.gd`](translator.gd) for details)

## License

To be specified upon GitHub publication.

## Contact

Please reach out via GitHub issues (to be published) or the mod distribution channel.

========================================

# Trans To Vostok

Road to Vostok의 다국어 번역 지원 모드.

> **NOTE:** *해당 모드는 현재 개발중에 있습니다.*

- 현재 지원 언어: **English** (게임 기본언어), **Korean** (개발 중)
- 한국어를 대상으로 개발 및 ToolBox를 우선 개발 중입니다.
- 개발이 어느 정도 완료되면 GitHub에 자세한 메뉴얼과 ToolBox 등을 공개할 예정입니다.

## 1. 소개

**Trans To Vostok**는 Road to Vostok의 다국어 지원을 위해 개발 중인 모드입니다.
UI, 아이템, 퀘스트, 상호작용 등 **게임 내 번역 가능한 부분을 누락 없이 최대한 무결성 번역**하는 것을 목표로 합니다.

## 2. 주요 기능

1. 게임 번역 (기본 기능)
   - 게임 내 UI, 툴팁, 아이템 이름, 이벤트 설명, 트레이더 대사 등을 번역합니다.
2. UI 지원
   - 모드 로드 시 **단축키 `F9`** 로 언어 선택 UI 표시
   - 게임 재시작 없이 런타임에 언어 전환 가능
   - 호환성 모드 토글 제공 (아래 참고)
3. 문자 위치 재정렬
   - 번역으로 텍스트 길이가 달라질 경우 **실제 화면 위치가 어긋날 수 있습니다** (예: 툴팁의 "Weight: 0.8kg" 같은 `A: B` 레이아웃).
   - 해당 모드는 번역된 라벨의 실제 폰트 너비를 측정하여 Value 노드의 offset을 자동 재조정을 지원합니다.
     - 대상: `Label` 노드 + 자식 `Value` Label (수동 위치)
     - Tooltip, 인벤토리 스탯 등의 "라벨: [값]" 패턴 자동 정렬
     - **호환성 모드에서는 비활성** — 게임 씬 구조에 간섭하지 않음
4. 게임 내 property와 1대1 매칭 번역 (정밀 매칭)
   - 단순 text 치환이 아니라 **Godot 노드의 구조적 식별자**로 번역 대상을 직접 지정합니다:
   - ``(location, parent, name, type, text) → translation``
     - `location`: 씬 파일 경로 (예: `UI/Interface`)
     - `parent`: 씬 내 부모 노드 경로 (예: `Tools/Notes`)
     - `name`: 노드 이름 (예: `Hint`)
     - `type`: Godot 노드 클래스 (예: `Label`)
     - `text`: 원문
   - **같은 단어라도 어느 UI의 어느 노드에 있는지에 따라 다르게 번역** 가능 — 오매칭 방지, 문맥별 번역 지원.
     - 예: NVG(Night Vision Goggle의 경우, 설정에서는 Full Name을, 그 외에는 NVG을 표시)
5. N-Tier Fallback 매칭
   - 구체적인 컨텍스트부터 일반 치환까지 9단계로 조회합니다:
   - 현재 구현 방식 (수정될 수 있음)| Tier | 매칭 방식                                 | 비고                             |
     | ---- | ----------------------------------------- | -------------------------------- |
     | 1    | **static exact** — 5개 필드 완전 일치 | 모든 필드가 완벽하게 일치        |
     | 2    | **scoped literal exact**            | 동적 텍스트 (코드 할당)          |
     | 3    | **scoped pattern exact**            | 정규식 + 씬 컨텍스트             |
     | 4    | **literal global**                  | 텍스트 완전 일치 (전역)          |
     | 5    | **pattern global**                  | 정규식 (전역)                    |
     | 6    | **static score**                    | 부분 컨텍스트 매칭 (+8/+4/+2/+1) |
     | 7    | **scoped literal score**            | 동적 텍스트 부분 컨텍스트        |
     | 8    | **scoped pattern score**            | 정규식 + 부분 컨텍스트           |
     | 9    | **substr**                          | 부분 문자열 치환 (최후 fallback) |
6. 호환성 모드 (Compatibility Mode)
   - **게임 업데이트로 매칭 구조가 깨졌을 때 임시 대응용.**
   - 모든 번역 데이터를 **sub-string(사전) 취급**하여 부분 문자열 치환으로 동작
   - 정밀도는 낮지만 씬 구조 변경에 크게 영향받지 않음
   - 개발자가 모드를 업데이트하기 전까지 플레이어가 번역을 계속 사용할 수 있음
   - F9 단축키를 통해 UI에서 체크박스로 on/off 가능

## 3. 설치

> **NOTE:** 해당 모드는 MetroMoadLoader 등의 모드로더를 요구합니다.

1. Godot용 **MetroModLoader** 또는 **VostokMods**가 설치되어 있어야 합니다. https://modworkshop.net/mod/55623
2. `Trans To Vostok.zip` 파일을 다운로드 받은 후, 게임의 `mods/` 폴더에 복사합니다.
   예: `` C:\Program Files (x86)\Steam\steamapps\common\Road to VostokTrans To Vostok\mods\``
   또는: ``D:\SteamLibrary\steamapps\common\Road to Vostok\mods\``
3. 게임을 실행하면 기본 언어(English)로 시작됩니다.
4. **F9** 키로 언어 선택 UI를 열어 원하는 언어로 전환합니다.

## 4. 지원 언어

1. English: 게임의 기본 언어입니다.
2. 한국어(Korean): 현재 개발/테스트 중인 언어입니다.
3. 그 외 다른 언어는 ToolBox에 대한 개발이 완료된 후, 천천히 지원해 나갈 계획입니다.

추가 언어 지원을 원하시면 GitHub 이슈로 요청해 주세요. (차후 공개 예정)

## 5. TODO (로드맵)

### 5.1. 기능 구현

* [X] 런타임 번역 엔진 프로토타입 임시 구현 (N-tier fallback)
* [X] 1.0.0 버전을 대상으로 번역 모드 Prototype 개발
* [X] 언어 선택 UI 추가
* [X] 문자 위치 재정렬 기능 추가
* [X] 호환성 모드 추가
* [X] UI에 성능 옵션 추가 (v0.2.0에 추가됨)
* [ ] 현재 개발된 모드를 게임 1.0.0 버전에 대한 테스트 (진행 중)
* [ ] 일부 이미지 교체기능 추가 (예: Tutorial의 BillBoard 등)
* [ ] 번역기 최적화
* [ ] 디버그 모드 추가 (예상)

### 5.2. 번역 지원

* [X] Korean 번역을 기준으로 번역 템플릿 완성
* [ ] 번역 Template 정리 후, 기계번역 등을 이용해 다른 언어에 대한 임시 지원 추가
* [ ] 번역 ToolBox 프로토타입 GitHub 공개 및 관리
* [ ] 번역가 모집 또는 GitHub를 통한 협업
* [ ] ToolBox 및 메뉴얼 Prototype 완성 후 GitHub 공개
* [ ] 추가 언어 지원  Branch 생성 (일본어, 중국어, 독일어 등)

---

## 개발자/번역가용 ToolBox (아직 공개 안됨)

모드 저장소에는 번역 파이프라인 구축용 **Python 도구**가 포함되어 있습니다:

| 도구                          | 역할                                        |
| ----------------------------- | ------------------------------------------- |
| `a_decompile_pck.py`        | 게임 PCK 파일 디컴파일                      |
| `b_extract_tscn_text.py`    | `.tscn` 씬 파일에서 번역 대상 텍스트 추출 |
| `c_extract_tres_text.py`    | `.tres` 리소스 파일에서 텍스트 추출       |
| `d_check_untranslated.py`   | 번역 누락/커버리지 리포트                   |
| `e_validate_translation.py` | xlsx 스키마/중복/매칭 검증                  |
| `f_build_runtime_tsv.py`    | xlsx → 런타임 TSV 빌드                     |
| `g_build_mod_package.py`    | 최종 모드 zip 패키지 빌드                   |
| `check_conflict.py`         | 번역 충돌 검사 (같은 원문 다른 번역)        |
| `check_old_translation.py`  | 게임 업데이트로 사라진 옛 번역 감지         |

**ToolBox 상세 매뉴얼은 개발 완료 후 GitHub에 공개됩니다.**

---

## 기술 구조

- **런타임 엔진**: `translator.gd` (GDScript autoload)
- **UI**: `translator_ui.gd` (F9 단축키로 표시되는 언어 선택 UI)
- **번역 데이터**: `<locale>/translation_*.tsv` (xlsx에서 빌드)
- **매칭 방식**: Godot 노드 구조 기반 1:1 매핑 (자세한 내용은 [`translator.gd`](translator.gd) 상단 주석 참고)

## 라이선스

추후 GitHub 공개 시 명시 예정.

## 문의

GitHub 이슈(추후 공개) 또는 모드 배포 채널을 통해 문의해 주세요.

# ScreenShots

**Trans to Vostok**
![1776508455196](image/README/3_Trans2Vostok_Main_Korean.png)

![1776508352445](image/README/2_Trans2Vostok_Lang_Sel.png)

![1776508495450](image/README/4_Trans2Vostok_New_Korean.png)

![1776508536327](image/README/5_Trans2Vostok_Cabin_Korean.png)

![1776508589318](image/README/6_Trans2Vostok_Settings_Korean.png)

![1776508751998](image/README/7_Trans2Vostok_Tutorial_Crate.png)

**MetroModLoaderUI**
![1776508272457](image/README/1.Metro_MoadLoader.png)
