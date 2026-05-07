**Supported languages**

- **English** (game default)
- **Korean** (primary target)
- **French** (prototype — under testing)
- Additional languages will be added once Korean and French are
  fully validated. Languages that mix the Latin alphabet with diacritics
  (French, Português, …) need extra checks first, and the toolbox
  refactor is still ongoing.

**Compatible mods** (tested — but compatibility may not always be guaranteed)

- *Expanded Storage* by jakiepoo — <https://modworkshop.net/mod/56126>
- *Oldman's Immersive Overhaul* (ImmersiveXP) — <https://modworkshop.net/mod/50811>
- *Trader Refresh Hotkey* (temporary fix by metro) — <https://modworkshop.net/mod/55933>

---

# Trans To Vostok

A multilingual translation mod for Road to Vostok.

> **NOTE:** *This mode is currently under development. .*

- Currently supported languages: **English** (game default), **Korean**, **French** (initial machine-translated pass, in testing)
- The first development iteration based on Korean is complete; ToolBox refactoring is currently in progress alongside the addition of French and other languages.
- Detailed manuals and the ToolBox will be published on GitHub once development reaches a sufficient milestone.

## 1. Introduction

**Trans To Vostok** is a mod under development to support multilingual localization for Road to Vostok.
It aims to deliver **complete, non-missing translation** across all translatable game content — UI, items, quests, interactions, and more.

## 2. Key Features

### Main features

1. **Game Translation** (core feature)
   - Translates in-game UI, tooltips, item names, event descriptions, trader dialogue, and more.
2. **Image / Texture Translation** (added in v0.3.0)
   - Game textures replaced with localized versions at runtime — sprites, Sprite3D, and MeshInstance3D ShaderMaterial `sampler2D` parameters.
   - Scans `<locale>/textures/` recursively; paths mirror the original `res://` layout.
   - Missing files are silently skipped — original texture is kept, no crash.
   - Originals are restored on language switch (mirrors the text translator lifecycle).
   - First shipped set: Korean **Tutorial Billboard** textures (17 images).
   - **Note**: Translated textures were hand-crafted (reconstructed), and may include hand-drawn work and/or copyright-free assets, so some icons may differ slightly from the originals (e.g., Performance icon, Permadeath skull icon on the Tutorial Billboards).
3. **UI Support**
   - Opens a language selection UI via the **`F9`** hotkey.
   - Switch languages at runtime without restarting the game.
   - Performance options (batch size / interval), Whitelist toggles, Mod-compatibility addon toggles, and the optional Substr Mode are all configured here.
4. **Priority Whitelist** (added in v0.3.1)
   - Optional path-keyword presets that force per-frame priority translation for specific UI areas (HUD map label, inventory, trader UI, etc.).
   - Intended for mod compatibility — when another mod periodically overwrites in-game text and the default batch cycle can't keep up (e.g. flicker), enabling the relevant preset eliminates it.
   - All presets default OFF. Toggle via the **Whitelist** tab in the F9 UI. Per-preset state persists to `user://trans_to_vostok.cfg`.
5. **Mod Compatibility Addons** (added in v0.5.0)
   - Per-mod runtime helpers that handle label patterns introduced by other mods (e.g. prefixes prepended to every tooltip).
   - First addon: **ImmersiveXP** (Oldman's Immersive Overhaul) — strips the `\n.\n` / `\n\n` interact-dot prefix before lookup so the inner text is translated through all match tiers, then reattaches the prefix to the result.
   - Toggle in the **Addons** tab of the F9 UI. Default all OFF — enable only for mods you actually have installed. State persists to `user://trans_to_vostok.cfg`.

### Internal mechanics

6. **Text Position Realignment**
   - When translation changes text length, **on-screen layout can shift** (e.g., `A: B` layouts like tooltip's "Weight: 0.8kg").
   - This mod measures the translated label's actual font width and auto-adjusts the Value node's offset.
     - Targets: `Label` nodes with a child `Value` Label (manual positioning)
     - Auto-aligns "label: [value]" patterns in Tooltip, inventory stats, etc.
     - **Disabled in Substr Mode** — avoids interfering with game scene structure.
7. **1:1 Property-Based Translation** (Precision Matching)
   - Instead of simple text substitution, translation targets are specified directly via **Godot node structural identifiers**:
   - ``(location, parent, name, type, text) → translation``
     - `location`: Scene file path (e.g., `UI/Interface`)
     - `parent`: Parent node path within the scene (e.g., `Tools/Notes`)
     - `name`: Node name (e.g., `Hint`)
     - `type`: Godot node class (e.g., `Label`)
     - `text`: Original source text
   - **The same word can be translated differently depending on which UI/node it appears in** — prevents mismatches, enables context-aware translation.
     - Example: NVG (Night Vision Goggle) can show the full name in settings but "NVG" everywhere else.
8. **N-Tier Fallback Matching**
   - Looks up translations through 9 tiers, from specific context to generic substitution:

   | Tier | Match Method                          | Notes                                |
   | ---- | ------------------------------------- | ------------------------------------ |
   | 1    | **static exact** — all 5 fields match | All fields match exactly             |
   | 2    | **scoped literal exact**              | Dynamic text (runtime assignment)    |
   | 3    | **scoped pattern exact**              | Regex + scene context                |
   | 4    | **literal global**                    | Full text match (global)             |
   | 5    | **pattern global**                    | Regex (global)                       |
   | 6    | **static score**                      | Partial context match (+8/+4/+2/+1)  |
   | 7    | **scoped literal score**              | Dynamic text, partial context        |
   | 8    | **scoped pattern score**              | Regex + partial context              |
   | 9    | **substr**                            | Substring substitution (last resort) |
9. **Substr Mode** (renamed from "Compatibility Mode" in v0.5.0; not recommended for normal use)
   - Temporary fallback when a game update breaks the structural matching used by tiers 1–8.
   - Promotes every literal/static entry to substr fallback so partial-match coverage is wider.
   - Lower precision (false positives possible) — only enable if many texts go untranslated after a game update, while waiting for the mod to be updated.
   - Toggle on/off via checkbox in the F9 UI.

## 3. Installation

> **NOTE:** This mod requires a mod loader such as MetroModLoader.

1. Install **MetroModLoader** or **VostokMods** for Godot: <https://modworkshop.net/mod/55623>
2. Download `Trans To Vostok.zip` and copy it into the game's `mods/` folder.
   e.g., `C:\Program Files (x86)\Steam\steamapps\common\Road to Vostok\mods\`
   or: `D:\SteamLibrary\steamapps\common\Road to Vostok\mods\`
3. Launch the game — it starts in the default language (English).
4. Press **F9** to open the language selection UI and switch to your preferred language.
5. If some text **flickers** while another mod is active, open F9 → **Whitelist** tab and enable the relevant preset (e.g., *HUD Map Label* for ImmersiveXP).
   - This stems from the other mod refreshing a specific label every frame.
   - The **Whitelist** is a checklist that marks specific UI areas as "always re-translate every frame", so flicker no longer occurs on those areas.
6. If some text **isn't translating properly** while another mod is active, open F9 → **Addons** tab and enable the relevant addon (e.g., *ImmersiveXP* — handles the `\n.\n` / `\n\n` tooltip prefix).

## 4. Supported Languages

1. **English**: The game's default language.
2. **Korean (한국어)**: First development iteration complete. Both text and texture translation included.
3. **French (Français)**: Added in v0.4.0 — initial pass via DeepL machine translation (text only; texture translation not yet shipped). Currently maintained internally; the public repository and contribution flow for community refinement are still being prepared.
4. Other languages will be supported gradually as the ToolBox refactor finishes.

To request additional languages, please submit a GitHub issue (to be published).

## 5. Attribution

Translated texture assets (images) are made from a mix of hand-crafted work, license-free assets, and third-party data sources. Per-file source credits are listed in **`Trans To Vostok/<locale>/Texture_Attribution.md`** inside the mod zip — auto-generated from each locale's `Texture.xlsx` on every build.

Per-locale translator credit (text + texture) is in **`Trans To Vostok/<locale>/Translation_Credit.md`**. The project-wide author / translator / contributor list is in `AUTHORS.md` at the repository root.

========================================

**지원 언어**

- **English** (게임 기본언어)
- **Korean** (메인 타깃)
- **French** (프로토타입 — 테스트 중)
- 한국어/프랑스어 검증 완료 후 다른 언어를 점진적으로 추가할 예정.
  라틴 알파벳에 발음 부호가 섞이는 언어 (French, Português 등) 의
  사전 점검과 ToolBox 리팩토링이 함께 진행 중.

**호환 모드** (테스트 됨 — 호환성이 항상 보장되지는 않을 수 있음)

- *Expanded Storage* by jakiepoo — <https://modworkshop.net/mod/56126>
- *Oldman's Immersive Overhaul* (ImmersiveXP) — <https://modworkshop.net/mod/50811>
- *Trader Refresh Hotkey* (metro 의 임시 fix) — <https://modworkshop.net/mod/55933>

---

# Trans To Vostok

Road to Vostok의 다국어 번역 지원 모드.

> **NOTE:** *해당 모드는 현재 개발중에 있습니다.*

- 현재 지원 언어: **English** (게임 기본언어), **Korean**, **French** (DeepL 1차 기계번역, 테스트 중)
- 한국어를 기준으로 1차 개발이 완료되었으며, French 등 다른 언어 추가와 ToolBox 리팩토링이 함께 진행 중.
- 개발이 어느 정도 완료되면 GitHub에 자세한 메뉴얼과 ToolBox 등을 공개할 예정입니다.

## 1. 소개

**Trans To Vostok**는 Road to Vostok의 다국어 지원을 위해 개발 중인 모드입니다.
UI, 아이템, 퀘스트, 상호작용 등 **게임 내 번역 가능한 부분을 누락 없이 최대한 무결성 번역**하는 것을 목표로 합니다.

## 2. 주요 기능

### 메인 기능

1. 게임 번역 (기본 기능)
   - 게임 내 UI, 툴팁, 아이템 이름, 이벤트 설명, 트레이더 대사 등을 번역.
2. 이미지 / 텍스처 번역 (v0.3.0에서 추가)
   - 게임 텍스처를 로케일별 번역본으로 런타임에 교체 — 스프라이트, Sprite3D, MeshInstance3D 의 ShaderMaterial `sampler2D` 파라미터 지원.
   - `<locale>/textures/` 디렉토리를 재귀 스캔. 경로는 원본 `res://` 구조를 그대로 미러링.
   - 번역 파일이 없으면 조용히 스킵 — 크래시 없이 원본 텍스처 유지.
   - 언어 전환 시 원본 복원 (텍스트 translator 와 동일한 라이프사이클).
   - 최초 적용: 한국어 **튜토리얼 빌보드** 텍스처 17장.
   - **참고**: 번역 텍스처는 수작업으로 재구성(hand-crafted)되었으며, 직접 그린 작업물(hand-drawing) 또는 저작권이 없는 애셋이 포함될 수 있어 일부 아이콘이 원본과 조금 다를 수 있음 (예: 튜토리얼 빌보드의 Performance 아이콘, Permadeath 해골 아이콘 등).
3. UI 지원
   - **단축키 `F9`** 로 언어 선택 UI 표시.
   - 게임 재시작 없이 런타임에 언어 전환 가능.
   - 성능 옵션 (배치 크기 / 간격), Whitelist 토글, Mod 호환성 addon 토글, 그리고 옵션인 Substr Mode 모두 이 UI 에서 설정.
4. 우선 순위 화이트리스트 (v0.3.1에서 추가)
   - 특정 UI 영역(HUD 맵 이름, 인벤토리, 트레이더 UI 등)을 매 프레임 번역으로 승격시키는 경로 키워드 프리셋.
   - 모드 호환성을 위한 기능 — 다른 모드가 게임 텍스트를 주기적으로 덮어써 기본 batch cycle 이 따라잡지 못하는 경우 (예: 깜빡임), 해당 프리셋을 활성화하면 사라짐.
   - 모든 프리셋은 기본 OFF. F9 UI 의 **Whitelist** 탭에서 토글하며, 상태는 `user://trans_to_vostok.cfg` 에 저장됨.
5. Mod 호환성 Addons (v0.5.0에서 추가)
   - 다른 모드가 도입한 라벨 패턴 (예: tooltip 마다 prepend 되는 prefix) 을 처리하는 mod 별 런타임 helper.
   - 첫 addon: **ImmersiveXP** (Oldman's Immersive Overhaul) — `\n.\n` / `\n\n` interact-dot prefix 를 lookup 전에 strip → inner text 가 모든 매칭 tier 를 통과 → 결과에 prefix 재부착.
   - F9 UI 의 **Addons** 탭에서 토글. 기본 모두 OFF — 사용자가 실제로 사용 중인 mod 만 활성화. 상태는 `user://trans_to_vostok.cfg` 에 저장됨.

### 내부 동작

6. 문자 위치 재정렬
   - 번역으로 텍스트 길이가 달라질 경우 **실제 화면 위치가 어긋날 수 있음** (예: 툴팁의 "Weight: 0.8kg" 같은 `A: B` 레이아웃).
   - 번역된 라벨의 실제 폰트 너비를 측정하여 Value 노드의 offset 을 자동 재조정.
     - 대상: `Label` 노드 + 자식 `Value` Label (수동 위치)
     - Tooltip, 인벤토리 스탯 등의 "라벨: [값]" 패턴 자동 정렬
     - **Substr Mode 에서는 비활성** — 게임 씬 구조에 간섭하지 않음.
7. 게임 내 property 와 1대1 매칭 번역 (정밀 매칭)
   - 단순 text 치환이 아니라 **Godot 노드의 구조적 식별자**로 번역 대상을 직접 지정:
   - ``(location, parent, name, type, text) → translation``
     - `location`: 씬 파일 경로 (예: `UI/Interface`)
     - `parent`: 씬 내 부모 노드 경로 (예: `Tools/Notes`)
     - `name`: 노드 이름 (예: `Hint`)
     - `type`: Godot 노드 클래스 (예: `Label`)
     - `text`: 원문
   - **같은 단어라도 어느 UI 의 어느 노드에 있는지에 따라 다르게 번역** 가능 — 오매칭 방지, 문맥별 번역 지원.
     - 예: NVG (Night Vision Goggle) — 설정에서는 풀네임, 그 외에는 NVG 로 표시.
8. N-Tier Fallback 매칭
   - 구체적 컨텍스트부터 일반 치환까지 9 단계로 조회:

   | Tier | 매칭 방식                             | 비고                             |
   | ---- | ------------------------------------- | -------------------------------- |
   | 1    | **static exact** — 5개 필드 완전 일치 | 모든 필드가 완벽하게 일치        |
   | 2    | **scoped literal exact**              | 동적 텍스트 (코드 할당)          |
   | 3    | **scoped pattern exact**              | 정규식 + 씬 컨텍스트             |
   | 4    | **literal global**                    | 텍스트 완전 일치 (전역)          |
   | 5    | **pattern global**                    | 정규식 (전역)                    |
   | 6    | **static score**                      | 부분 컨텍스트 매칭 (+8/+4/+2/+1) |
   | 7    | **scoped literal score**              | 동적 텍스트 부분 컨텍스트        |
   | 8    | **scoped pattern score**              | 정규식 + 부분 컨텍스트           |
   | 9    | **substr**                            | 부분 문자열 치환 (최후 fallback) |
9. Substr Mode (v0.5.0 에서 "Compatibility Mode" 에서 rename; 일반 사용에는 권장되지 않음)
   - 게임 업데이트로 tier 1~8 의 구조 매칭이 깨졌을 때의 임시 fallback.
   - 모든 literal/static entry 를 substr fallback 에도 추가해 부분 매치 적용 범위 확장.
   - 정밀도가 낮음 (false positive 가능) — 게임 업데이트 후 다수 텍스트가 번역되지 않을 때, 모드 업데이트 전까지의 임시 사용용.
   - F9 UI 의 체크박스로 on/off.

## 3. 설치

> **NOTE:** 해당 모드는 MetroMoadLoader 등의 모드로더를 요구합니다.

1. Godot용 **MetroModLoader** 또는 **VostokMods**가 설치되어 있어야 합니다. <https://modworkshop.net/mod/55623>
2. `Trans To Vostok.zip` 파일을 다운로드 받은 후, 게임의 `mods/` 폴더에 복사합니다.
   예: `C:\Program Files (x86)\Steam\steamapps\common\Road to Vostok\mods\`
   또는: `D:\SteamLibrary\steamapps\common\Road to Vostok\mods\`
3. 게임을 실행하면 기본 언어(English)로 시작됩니다.
4. **F9** 키로 언어 선택 UI를 열어 원하는 언어로 전환합니다.
5. 다른 모드와 함께 사용 중 **일부 텍스트가 깜빡거린다면**, F9 → **Whitelist** 탭에서 해당 프리셋 활성화 (예: ImmersiveXP 의 경우 *HUD Map Label*).
   - 이는 해당 모드가 특정 텍스트 라벨을 매 프레임마다 갱신하는 문제에서 비롯됩니다.
   - **Whitelist** 는 매 프레임 갱신되는 항목에 대해 "매 프레임마다 계속 재번역"해야 할 대상을 표시하는 체크리스트입니다. (=깜빡임 문제 해소)
6. 다른 모드와 함께 사용 중 **일부 텍스트가 제대로 번역되지 않는다면**, F9 → **Addons** 탭에서 해당 addon 활성화 (예: *ImmersiveXP* — `\n.\n` / `\n\n` tooltip prefix 처리).

## 4. 지원 언어

1. English: 게임의 기본 언어입니다.
2. 한국어 (Korean): 1차 개발 완료. 텍스트 + 텍스처 번역 모두 포함.
3. 프랑스어 (French / Français): v0.4.0 에 추가됨 — DeepL 로 1차 기계번역 (텍스트만 적용; 텍스처 번역은 아직 미포함). 현재 내부에서 관리 중이며, 커뮤니티 검수/보정용 공개 저장소 및 기여 흐름은 준비 중.
4. 그 외 다른 언어는 ToolBox 정리가 마무리되는 대로 점진적으로 지원해 나갈 계획입니다.

추가 언어 지원을 원하시면 GitHub 이슈로 요청해 주세요. (차후 공개 예정)

## 5. 출처 표기 (Attribution)

번역된 텍스처(이미지) 에셋은 직접 작업물 / 라이선스-프리 애셋 / 제3자 데이터 출처가 혼합되어 있습니다. 각 파일별 출처는 모드 zip 안의 **`Trans To Vostok/<locale>/Texture_Attribution.md`** 에 정리되어 있으며, 빌드 시 각 로케일의 `Texture.xlsx` 에서 자동 생성됩니다.

로케일별 번역자 credit (텍스트 + 텍스처) 는 **`Trans To Vostok/<locale>/Translation_Credit.md`** 에 정리되어 있습니다. 프로젝트 전체 저자 / 번역자 / 기여자 명단은 저장소 루트의 `AUTHORS.md` 입니다.

========================================

# ScreenShots

**Trans to Vostok**
![3_Trans2Vostok_Main_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/3_Trans2Vostok_Main_Korean.png)

![2_Trans2Vostok_Lang_Sel.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/2_Trans2Vostok_Lang_Sel.png)

![4_Trans2Vostok_New_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/4_Trans2Vostok_New_Korean.png)

![5_Trans2Vostok_Cabin_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/5_Trans2Vostok_Cabin_Korean.png)

![6_Trans2Vostok_Settings_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/6_Trans2Vostok_Settings_Korean.png)

![7_Trans2Vostok_Tutorial_Crate.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/7_Trans2Vostok_Tutorial_Crate.png)

![8_Trans2Vostok_Texture_TutorialBillBoard1.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/8_Trans2Vostok_Texture_TutorialBillBoard1.png)

![9_Trans2Vostok_Texture_TutorialBillBoard2.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/9_Trans2Vostok_Texture_TutorialBillBoard2.png)

![10_Trans2Vostok_UI_WorldMap_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/10_Trans2Vostok_UI_WorldMap_Korean.png)

**MetroModLoaderUI**
![1776508272457](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/1.Metro_MoadLoader.png)
