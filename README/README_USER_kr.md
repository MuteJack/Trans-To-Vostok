**지원 언어**

- **English** (게임 기본언어)
- **Korean / 한국어** (개발자로부터 번역 관리중, 텍스처 작업 완료)
- **French / Français** (프로토타입, 텍스처 프로토타입)
- **Português (Brasil)** (프로토타입, 텍스처 미적용)
- **Deutsch** (프로토타입, 텍스처 미적용)
- **Español (LatAm)** (프로토타입, 텍스처 미적용)
- **日本語** (프로토타입, 텍스처 미적용)
- **简体中文** (프로토타입, 텍스처 미적용)
- **繁體中文** (프로토타입, 텍스처 미적용)
- **Русский / 러시아어** (프로토타입, 텍스처 미적용)

> 한국어 외 대부분의 언어는 DeepL/Claude API로 기계번역된 초안 상태입니다.
> 번역 참여는 [Crowdin](https://crowdin.com/project/trans-to-vostok)을 통해 진행되며, 커뮤니티 검수/개선 참여는 언제나 환영입니다.

**호환 모드** (테스트 됨 - 호환성이 항상 보장되지는 않을 수 있음)

- *Expanded Storage* by jakiepoo — [https://modworkshop.net/mod/56126](https://modworkshop.net/mod/56126)
- *Oldman's Immersive Overhaul* (ImmersiveXP) — [https://modworkshop.net/mod/50811](https://modworkshop.net/mod/50811)
- *Trader Refresh Hotkey* (metro 의 임시 fix) — [https://modworkshop.net/mod/55933](https://modworkshop.net/mod/55933)

---

# Trans To Vostok

Road to Vostok의 다국어 번역 지원 모드.

> **NOTE:** *해당 모드, 번역 ToolBox ([GitHub](https://github.com/MuteJack/Trans-to-Vostok))는 현재 개발중에 있습니다.*

> **번역 기여는 [Crowdin](https://crowdin.com/project/trans-to-vostok)을 통해 받고 있습니다.**
> 별도 셋업 없이 브라우저를 통해 바로 참여할 수 있습니다. [Trans to Vostok on Crowdin](https://crowdin.com/project/trans-to-vostok).
> [GitHub](https://github.com/MuteJack/Trans-to-Vostok)의 번역만 변경한 Pull Request는 더 이상 받지 않으니, Crowdin을 이용해 주세요. 
> 개발자가 주기적으로 Crowdin → 저장소로 sync하며 다음 모드 릴리스부터 반영됩니다.

![3_Trans2Vostok_Main_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/3_Trans2Vostok_Main_Korean.png)

## 1. 소개

**Trans To Vostok**는 Road to Vostok의 다국어 지원을 위해 개발 중인 모드입니다.
UI, 아이템, 퀘스트, 상호작용 등 **게임 내 번역 가능한 부분을 누락 없이 최대한 무결성 번역**하는 것을 목표로 합니다.

## 2. 주요 기능

### 메인 기능

1. 게임 번역 (기본 기능)
   - 게임 내 UI, 툴팁, 아이템 이름, 이벤트 설명, 트레이더 대사 등을 번역.
2. 이미지 / 텍스처 번역 (v0.3.0에서 추가)
   - 게임 텍스처를 로케일별 번역본으로 런타임에 교체 (예: Tutorial Billboard)
   - 게임 텍스처를 번역된 일부와 런타임에서 합성 (예: 게임의 원본/수정된 에셋을 포함하기 곤란한 Road Sign 등)
   - **참고**: 번역 텍스처는 수작업으로 재구성(hand-crafted)되었으며, 직접 그린 작업물(hand-drawing) 또는 저작권이 없는 애셋이 포함될 수 있어 일부 아이콘이 원본과 조금 다를 수 있습니다 (예: 튜토리얼 빌보드의 Performance 아이콘, Permadeath 해골 아이콘 등).
![9_Trans2Vostok_Texture_TutorialBillBoard2.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/9_Trans2Vostok_Texture_TutorialBillBoard2.png)
3. UI 지원
   - **단축키 `F9`** 로 언어 선택 UI 표시.
   - 게임 재시작 없이 런타임에 언어 전환 가능.
   - 성능 옵션 (배치 크기 / 간격), Whitelist 토글, Mod 호환성 addon 토글, 그리고 옵션인 Substr Mode 모두 이 UI 에서 설정.
   ![2_Trans2Vostok_Lang_Sel.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/2_Trans2Vostok_Lang_Sel.png)
4. 우선 순위 화이트리스트 (v0.3.1에서 추가)
   - 특정 UI 영역(HUD 맵 이름, 인벤토리, 트레이더 UI 등)을 매 프레임 번역본으로 갱신시킬 경로 키워드 프리셋.
   - 다른 모드가 게임 텍스트를 매 프레임마다 새로고침되어 기본 batch cycle 이 따라잡지 못하는 경우 (예: 깜빡임), 
   - F9키를 눌러, UI 의 **Whitelist** 탭을 통해 Toggle 할 수 있습니다. (모든 프리셋에 대한 기본값은 OFF입니다.)
5. Mod 호환성 Addons (v0.5.0에서 추가)
   - 다른 모드가 도입한 label 패턴 (예: tooltip 마다 prepend 되는 prefix) 을 처리하는 mod 별 런타임 helper.
   - F9 UI 의 **Addons** 탭에서 해당 모드에 대한 기능을 Toggle.
   - 예: **ImmersiveXP** (Oldman's Immersive Overhaul) — 화면 가운데에 .을 찍는 기능이 `{text}` -> `\n.\n{text}`로 구현되므로, 번역이 적용되지 않음.

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
     - 예: NVG (Night Vision Goggle) — 설정에서는 풀네임, 그 외에는 줄임말인 NVG 로 표시.
8. N-Tier Fallback 매칭

   - 구체적 컨텍스트부터 일반 치환까지 9 단계로 조회:

   | Tier | 매칭 방식                                    | 비고                             |
   | ---- | -------------------------------------------- | -------------------------------- |
   | 1    | **static exact** — 5개 필드 완전 일치 | 모든 필드가 완벽하게 일치        |
   | 2    | **scoped literal exact**               | 동적 텍스트 (코드 할당)          |
   | 3    | **scoped pattern exact**               | 정규식 + 씬 컨텍스트             |
   | 4    | **literal global**                     | 텍스트 완전 일치 (전역)          |
   | 5    | **pattern global**                     | 정규식 (전역)                    |
   | 6    | **static score**                       | 부분 컨텍스트 매칭 (+8/+4/+2/+1) |
   | 7    | **scoped literal score**               | 동적 텍스트 부분 컨텍스트        |
   | 8    | **scoped pattern score**               | 정규식 + 부분 컨텍스트           |
   | 9    | **substr**                             | 부분 문자열 치환 (최후 fallback) |
9. Substr Mode (일반 사용에는 권장되지 않음)

   - 게임 업데이트 후 다수 텍스트가 번역되지 않을 때, 모드 업데이트 전까지의 임시 사용 용도.
   (모든 literal/static entry 를 substr 로 취급)
   - F9 UI 의 체크박스로 on/off 가능.

## 3. 설치

> **NOTE:** 해당 모드는 MetroMoadLoader 등의 모드로더를 요구합니다.

1. Godot용 **MetroModLoader** 또는 **VostokMods**가 설치되어 있어야 합니다. 
[https://modworkshop.net/mod/55623](https://modworkshop.net/mod/55623)
![1776508272457](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/1.Metro_MoadLoader.png)
1. `Trans To Vostok.zip` 파일을 다운로드 받은 후, 게임의 `mods/` 폴더에 복사합니다.
   예: `C:\Program Files (x86)\Steam\steamapps\common\Road to Vostok\mods\`
   또는: `D:\SteamLibrary\steamapps\common\Road to Vostok\mods\`
2. 게임을 실행하면 기본 언어(English)로 시작됩니다.
3. **F9** 키로 언어 선택 UI를 열어 원하는 언어로 전환합니다.
4. 다른 모드와 함께 사용 중 **일부 텍스트가 깜빡거린다면**, F9 → **Whitelist** 탭에서 해당 프리셋 활성화 (예: ImmersiveXP 의 경우 *HUD Map Label*).
   - 이는 해당 모드가 특정 텍스트 라벨을 매 프레임마다 갱신하는 문제에서 비롯됩니다.
   - **Whitelist** 는 매 프레임 갱신되는 항목에 대해 "매 프레임마다 계속 재번역"해야 할 대상을 표시하는 체크리스트입니다. (=깜빡임 문제 해소)
5. 다른 모드와 함께 사용 중 **일부 텍스트가 제대로 번역되지 않는다면**, F9 → **Addons** 탭에서 해당 addon 활성화 (예: *ImmersiveXP* — `\n.\n` / `\n\n` tooltip prefix 처리).

## 4. 지원 언어

1. **English**: 게임의 기본 언어입니다.
2. **한국어 (Korean)**: 개발자에 의해 직접 번역/검수되며, 게임 버전이 변경될 경우 가장 먼저 번역 및 텍스처 재작업이 진행됩니다. (개발자의 모국어입니다.)
3. **프랑스어 (Français)**: v0.4.0 추가 — DeepL 1차 기계번역 (텍스트만, 텍스처 미적용).
4. **포르투갈어 (Português / Brasil)**: v0.5.1 추가
5. **독일어 (Deutsch) / 스페인어 LatAm (Español) / 일본어 (日本語) / 중국어 간체 (简体中文) / 중국어 번체 (繁體中文)**: v0.5.3 추가
6. **러시아어 (Русский)**: v0.6.1 추가
7. **이탈리아어 (Italiano) / 헝가리어 (Hungarian)** : 추가 예정
8. 그 외 언어: 모드 개발 진행도 / 커뮤니티 언어 추가 요청에 따라 점진적으로 추가 예정.

### 4.1. 텍스트 번역 / 검수 참여 (Crowdin 환경)

모든 번역은 [Crowdin](https://crowdin.com/project/trans-to-vostok)을 중심으로 진행됩니다. 
- 번역 기여: [Crowdin](https://crowdin.com/project/trans-to-vostok)에서 가입 후 브라우저에서 바로 작업 (별도 셋업 불필요).
- ToolBox ([GitHub Repo](https://github.com/MuteJack/Trans-to-Vostok))를 통한 번역 지원은 아직 개발중에 있습니다.
- Credit은 Crowdin에서 설정된 이름으로 자동 추가됩니다.
- 새 언어 요청 / 일반 피드백: [GitHub 이슈](https://github.com/MuteJack/Trans-to-Vostok/issues)로 요청해 주세요 (차후 공개 예정).

### 4.2. 텍스트 번역 (Local 환경, 준비중)
이것은 개발 지식이 있는 사람들을 위한 환경입니다. ([GitHub Repository](https://github.com/MuteJack/Trans-to-Vostok))
이것을 이용한 workflow는 현재 보완/docs 작성이 완료되는 대로 업데이트될 예정입니다.

### 4.3. 텍스처 번역
현재 텍스처는 모두 개발자가 수작업(hand-craft)를 통해 제작되고 있습니다.
- 텍스처에 들어가게 될 텍스트는 Crowdin에서 Texture/{sheetname}.tsv 를 통해 관리됩니다.
- 수작업이므로, 길이 문제 등으로 인해 제작 과정에서 텍스트가 crowdin과는 조금 다르게 반영될 수 있습니다.
- 번역된 텍스처 제작에 직접 참여하고 싶으신 분은, 해당 workflow에 대해 docs 제작 및 보완중에 있습니다. 
  - 현재로서는 Credit에 남길 이름과 함께 파일을 coldman1224@outlook.com으로 보내주시면 수동으로 Repo에 반영해드리겠습니다.
  - 또는, 개발 지식 (Git, [GitHub](https://github.com/MuteJack/Trans-to-Vostok))이 있으신 분은 PR (Pull Request)을 통해 제출해주세요.

## 5. 출처 표기 (Attribution)

번역된 텍스처(이미지) 에셋은 직접 작업물 / 라이선스-프리 애셋 / 제3자 데이터 출처가 혼합되어 있을 수 있습니다. 각 파일별 출처는 모드 zip 안의 **`Trans To Vostok/<locale>/Texture_Attribution.md`** 에 정리되어 있습니다.

locale별 credit (텍스트 + 텍스처) 는 **`Trans To Vostok/<locale>/Translation_Credit.md`** 에 정리되어 있습니다. 

프로젝트 전체 저자 / 번역자 / 기여자 명단은 저장소 루트의 `AUTHORS.md` 에 정리되어 있습니다.

위 3가지 파일은 Repository의 Toolbox를 통해 자동생성/수정됩니다.

========================================

# ScreenShots

**Trans to Vostok**
![4_Trans2Vostok_New_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/4_Trans2Vostok_New_Korean.png)

![5_Trans2Vostok_Cabin_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/5_Trans2Vostok_Cabin_Korean.png)

![6_Trans2Vostok_Settings_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/6_Trans2Vostok_Settings_Korean.png)

![7_Trans2Vostok_Tutorial_Crate.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/7_Trans2Vostok_Tutorial_Crate.png)

![8_Trans2Vostok_Texture_TutorialBillBoard1.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/8_Trans2Vostok_Texture_TutorialBillBoard1.png)

![10_Trans2Vostok_UI_WorldMap_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/10_Trans2Vostok_UI_WorldMap_Korean.png)


