# Changelog (User) — Trans To Vostok

A short, user-facing summary of changes you may notice in-game.
For full developer-level details (code paths, refactors, internal
tooling), see [`CHANGELOG.md`](CHANGELOG.md). 

---

## Known Issues

- _(none currently)_

---

## [0.6.2] — 2026-06-10

- **Added**: **Hungarian** (*Magyar*) added to the mod.
  - Translation provided by: Papp Csaba
  - 16 Tutorial Billboard textures translated. (Original artwork by Papp Csaba, revised by MuteJack)
- **Fixed — Korean**:
  - Translation typo and expression fixes
  (Gunsmith: 총잡이 → 건스미스; assorted UI / dialog / item text / incorrect line breaks)
  - Some wording unified (e.g. strings where Task (의뢰) was translated as 임무)
- **Fixed — Japanese**: Some translation expression fixes. (Fixed by: Nineblood)

---

## [0.6.1] — 2026-06-06

- **Added**: **Russian** (*Русский*) language is now available in the F9
  language list. Initial machine-translated pass (text only; texture
  translation pending).

---

## [0.6.0] — 2026-05-31

- **Added — New rendering path (composite-on-original)**: Beyond the
  existing full-texture replacement used for Tutorial Billboards, this
  release adds a second method where only the translated text is
  replaced while the original sign's weathering, paint scratches, and
  lighting integration remain untouched. Distance LOD also keeps the
  translated text (proper mipmaps for the composite). All 16 new
  texture translations below use this path.
- **Added — 16 translated textures (Korean)** — road signs and building
  signage now display in Korean while preserving the original weathered,
  photo-real look:
  - Road signs: *Mines*, *Public Road*, *VT7 / Highway directional*,
    *Border Zone* (4 variants), *School*, *Speedbump*, *Village Crossroads*
  - *Canteen* sign (Sotilaskoti / KASSA — Finnish military canteen)
  - *Board_Message*, *Booth_Ticket*, *Box_Electric*, *Box_Transformer*
  - Inventory icon for *Sign (Border Zone)* furniture item
- **Improved — Japanese**: 83 strings refined via Crowdin (contributor:
  Nineblood).
- **Community**: All other active languages (French, German, Spanish LatAm,
  Simplified/Traditional Chinese, Portuguese-BR) now have the full Sign +
  Structure string set available on
  [Crowdin](https://crowdin.com/project/trans-to-vostok) for community
  translation. Once a language's text translations land, image workers
  can produce the per-locale overlay PNGs.

---

## [0.5.3] — 2026-05-30

- **Added**: **5 new languages** — *Deutsch*, *Español (LatAm)*,
  *日本語*, *简体中文*, *繁體中文*. Each is an initial DeepL
  machine-translated pass (text only; texture translation pending).
- **Added (disabled)**: **Russian** (*Русский*) — partial DeepL pass
  (~23%) before the monthly translation quota was exhausted. The
  locale ships disabled and will become selectable once the quota
  resets and the remaining strings are translated.
- **Improved — Korean**: Translation refinements + QA across Tasks
  (*의뢰*), Tutorial Billboard textures, and assorted UI strings
  (contributor: gap tal).

---

## [0.5.2] — 2026-05-27

- **Fixed**: **Portuguese (Brazil)** translations were not loading
  in-game. The language is now displayed correctly when selected
  from the F9 language list.
- **Fixed**: F9 → Info tab now shows the actual Translation Updated
  date per language (previously stuck at `(unknown)`).
- **Changed**: F9 → Info tab gains a new contributor section structure
  — separate **Translators** (project leads + proofreaders),
  **Translation Contributors**, and **Image Reworkers** rows per
  language, sourced automatically from Crowdin contributor activity.
- **Community**: All translation contributions are now collected
  through the Crowdin web platform — anyone can join, translate in
  the browser, and the maintainer periodically syncs to the next
  mod release. (Translation-only Pull Requests are no longer accepted
  on GitHub; use Crowdin instead.)

---

## [0.5.1] — 2026-05-08

- **Added**: **Portuguese (Brazil)** language support — initial pass
  via DeepL machine translation (text only; texture translation
  not yet shipped). Available in the F9 language list as
  *Português (Brasil)*. Community refinement is welcome through the
  upcoming public repository.
- **Added**: New "Info" tab in the language window (F9) — shows mod
  version, build date, target game version, and contributors broken
  down by role (Lead Developer / Code Contributors /
  Acknowledgments / Translators / Image Reworkers). Per-locale data
  follows the currently selected language.
- **Fixed**: Select Language UI (F9) is no longer affected by
  translation rules — its own labels stay in their source text.
  This was the only Known Issue listed under 0.5.0.

---

## [0.5.0] — 2026-05-06

- **Added**: New "Addons" tab in the language window (F9). Toggle
  per-mod compatibility helpers. First entry: **ImmersiveXP**
  (Oldman's Immersive Overhaul). When enabled, tooltip labels that
  ImmersiveXP prepends with `\n.\n` or `\n\n` (interact-dot mode) are
  translated through all match stages, not just word-level fallback.
- **Added**: User-facing changelog (`CHANGELOG_user.md`, this file)
  with a Known Issues section.
- **Removed**: "Reset to Defaults" button on the Whitelist tab — was
  identical to "Deactivate All" since all defaults are off.

---

## [0.4.5] — 2026-05-05

- **Safeguard**: Added a guard against accidental partial-word
  substitution. When a short English token registered for translation
  happens to appear inside another English word (e.g. `Cat` inside
  `Catalog`, `Day` inside `Daybreak`, `Fire` inside `Fireplace`,
  `Hard` inside `Hardware`), the translator now refuses the match.
  Without this guard, such cases could in theory produce garbled
  output like `Catalog` → `고양이alog`.
- **Fixed**: Compatibility with the **Expanded Storage**
  ([modworkshop/56126](https://modworkshop.net/mod/56126)) mod —
  expanded container sizes (Fridge / Cabinet / Office Cabinet /
  Nightstand / Medical Cabinet) now apply correctly when this mod is
  installed alongside Trans To Vostok.
- **Added**: Trader names (Generalist / Doctor / Gunsmith / Driver /
  Grandma / Shaman / Fisherman / Scientist) and hostile-faction names
  (Bandit / Guards / Military / Punisher) now translate even when
  other mods (e.g. ImmersiveXP) prepend a prefix to the label.
- **Renamed**: "Compatible Mode" checkbox is now called "Substr Mode"
  (more accurate name; existing setting is migrated automatically, no
  user action needed).

## [0.4.4] — 2026-05-05

- **Added**: "Tutorial Exit" label shown when leaving the tutorial map
  is now translated (was English-only previously).

## [0.4.3] — 2026-05-05

- **Fixed**: Switching language mid-game now refreshes inventory /
  settings / other already-open UI properly. Previously some labels
  stayed in the previous language until you closed and reopened the
  game.

## [0.4.2] — 2026-05-05

- **Fixed**: Short freeze / hitch when opening crates or interacting
  with traders.

## [0.4.1] — 2026-05-05

- **Fixed**: Item names like `Hybrid` accumulating extra letters
  (`Hybride`, `Hybridee`, `Hybrideee`, …) on first inventory open.
- **Fixed**: French intro paragraph wrapping aligned with other locales.

## [0.4.0] — 2026-05-05

- **Added**: **French language support** (initial machine-translated
  pass via DeepL; community refinement is planned once the public
  repository is ready).
- **Fixed (Korean)**: Minor mistranslations + tutorial billboard
  texture typo (접격지대 → 접경지대).
- **Fixed**: Trader panel labels (Tax / Tasks / Resupply) and other
  anchored labels were misaligned in game build 0.1.1.3 — now
  positioned correctly.

## [0.3.4] — 2026-04-26

- **Fixed (Korean)**: Wrongly drawn road guidelines on the world map
  texture.

## [0.3.3] — 2026-04-26

- **Added (Korean)**: Korean world map texture (place names,
  decorative overlays).

## [0.3.2] — 2026-04-24

- **Added**: Translations for new text introduced in game build
  0.1.1.3 (`Native` resolution, `Image Sharpness`, SMAA toggle,
  Compatibility-renderer warning, killbox messages).
- **Fixed (Korean)**: Context-based mistranslation fixes (e.g.
  `Border` → 접경지대, music preset-specific corrections).

## [0.3.1] — 2026-04-22

- **Improved**: Compatibility with other mods — some labels that other
  mods rewrite every frame can now be set to translate every frame
  via the Whitelist tab in the language UI (press F9).

## [0.3.0] — 2026-04-22

- **Added**: Texture translation system — in-game images can now be
  replaced per-locale. First application: Korean tutorial billboards.

## [0.2.3] — 2026-04-21

- **Improved (Korean)**: Translation polish across various UI / item
  texts.

## [0.2.2] — 2026-04-20

- Hotfix.

## [0.2.1] — 2026-04-20

- Hotfix.

## [0.2.0] — 2026-04-20

- **Fixed (Korean)**: Missing translations for Trader Event
  Descriptions and other gaps.

## [0.1.0] — 2026-04-17

- **Added (Korean)**: Initial Korean translation covering UI,
  tooltips, items, tasks, events, and traders.

---

# 변경 이력 (사용자용) — Trans To Vostok

게임에서 직접 체감할 수 있는 변경사항만 짧게 정리한 문서입니다.
코드 경로 / 내부 리팩터링 등 개발자용 상세 내용은
[`CHANGELOG.md`](CHANGELOG.md) 를 참고하세요.

---

## 알려진 문제

- _(현재 없음)_

---

## [0.6.2] — 2026-06-10

- **추가**: **헝가리어** (*Magyar*)가 모드에 추가되었습니다.
  - 번역 제공: Papp Csaba
  - Tutorial Billboard 텍스처 16개 번역 추가. (Papp Csaba 원본 제공, MuteJack 수정)
- **수정 — 한국어**: 
  - 번역 오타 및 표현 수정
  (Gunsmith: 총잡이 → 건스미스; 일부 UI / 대사 / 아이템 텍스트 / 잘못된 줄바꿈)
  - 일부 번역 표현 통일 (예: Task (의뢰)가 임무와 같은 단어로 번역된 string 수정)
- **수정 — 일본어**: 일부 번역 표현 수정. (수정: Nineblood)

---

## [0.6.1] — 2026-06-06

- **추가**: **러시아어** (*Русский*)가 F9 언어 선택 목록에 추가되었습니다.
  DeepL 1차 기계번역 (텍스트만; 텍스처는 추후 작업 예정).

---

## [0.6.0] — 2026-05-31

- **추가 — 신규 렌더링 방식 (원본 위에 합성)**: 기존 Tutorial Billboards
  등에 쓰이던 전체 텍스처 교체 (replace) 방식 외에, 번역된 텍스트 부분만
  덮어쓰고 원본 표지판의 weathering / 긁힘 / 조명 통합을 그대로 유지하는
  방식이 추가되었습니다. 거리감 LOD 에서도 번역된 텍스트 유지 (합성
  결과에 대한 mipmap 생성). 아래 16개의 신규 텍스처가 모두 이 방식을
  사용합니다.
- **추가 — 한국어 텍스처 16개** — 도로 표지판과 건물 간판이 원본
  weathering / 조명을 유지한 채 한국어로 합성됩니다:
  - 도로 표지판: *지뢰 지대*, *공도 종점*, *VT7 / 도로 안내판*, *접경
    지대* (4개 variation), *학교*, *과속방지턱*, *마을 교차로*
  - *Canteen 간판* (Sotilaskoti / KASSA — 핀란드군 매점으로 추정)
  - *Board_Message*, *Booth_Ticket*, *Box_Electric*, *Box_Transformer*
  - 인벤토리 아이콘 (*Sign (Border Zone)* 가구 아이템용)
- **개선 — 일본어**: Crowdin 을 통해 83개 string 다듬어짐 (기여자:
  Nineblood).
- **커뮤니티**: 다른 active 언어 (프랑스어, 독일어, 스페인어 LatAm,
  중국어 간/번체, 포르투갈어 BR) 모두 표지판 / 구조물 텍스트 번역이
  [Crowdin](https://crowdin.com/project/trans-to-vostok) 에 등록됨.
  텍스트 번역 완료 후 이미지 작업자가 locale 별 overlay PNG 작업 가능.

---

## [0.5.3] — 2026-05-30

- **추가**: **새로운 5개 언어** — *Deutsch*, *Español (LatAm)*,
  *日本語*, *简体中文*, *繁體中文*. 각 언어는 DeepL 1차 기계번역
  (텍스트만, 텍스처는 추후 작업 예정).
- **추가 (비활성)**: **러시아어** (*Русский*) — DeepL 번역 부분
  완료 (~23%) 후 월간 quota 한도 도달로 일시 중단.
  현재는 비활성 상태로 출시하며, quota 리셋 후 잔여 분량이 완료되면
  활성화될 예정입니다.
- **개선 — 한국어**: Task (*의뢰*), Tutorial Billboard 텍스처 등에
  대한 번역 개선 및 QA 진행 (기여자: gap tal).

---

## [0.5.2] — 2026-05-27

- **수정**: **포르투갈어 (브라질)** 번역이 인게임에서 적용되지 않던 문제 해결.
  F9 언어 선택에서 선택 시 정상적으로 표시됩니다.
- **수정**: F9 → Info 탭의 Translation Updated 가 `(unknown)` 으로 표시되던
  문제 해결. 이제 언어별 마지막 번역 시점이 정상 표시됩니다.
- **변경**: F9 → Info 탭의 기여자 섹션 구조 개편 — 언어별로 **Translators**
  (프로젝트 리더 + Proofreader), **Translation Contributors**,
  **Image Reworkers** 항목이 분리되어 표시됩니다. Crowdin 활동 기록에서
  자동 추출.
- **커뮤니티**: 모든 번역 기여를 **Crowdin 웹**으로 일원화. 누구나 가입 후
  브라우저에서 번역 가능하며, 관리자가 주기적으로 다음 모드 빌드에 반영
  합니다. (번역만 변경한 GitHub Pull Request는 더 이상 받지 않습니다 —
  Crowdin을 이용해 주세요.)

---

## [0.5.1] — 2026-05-08

- **추가**: **포르투갈어 (브라질)** 지원 — DeepL 1차 기계번역 (텍스트
  만, 텍스처는 추후). F9 언어 선택 목록에 *Português (Brasil)* 로
  표시됨. 공개 저장소 준비 후 커뮤니티 검수 환영.
- **추가**: 언어 창 (F9) 에 새 "Info" 탭 — 모드 버전, 빌드 일자,
  타깃 게임 버전, 기여자 (Lead Developer / Code Contributors /
  Acknowledgments / Translators / Image Reworkers) 표시. locale 별
  정보는 현재 선택된 언어 기준으로 표시.
- **수정**: 언어 선택 UI (F9) 자체가 번역되지 않도록 격리. 0.5.0
  의 Known Issues 에 등재된 유일한 항목 해결.

---

## [0.5.0] — 2026-05-06

- **추가**: 언어 창 (F9) 에 새 "Addons" 탭. mod 별 호환성 헬퍼 ON/OFF.
  첫 항목: **ImmersiveXP** (Oldman's Immersive Overhaul). 활성화 시
  ImmersiveXP 가 라벨 앞에 prepend 하는 `\n.\n` 또는 `\n\n` prefix
  (interact-dot 모드) 가 적용된 tooltip 라벨이 단어 단위 폴백뿐 아니라
  **모든 매칭 단계** 에서 변환됨.
- **추가**: 사용자용 changelog (`CHANGELOG_user.md`, 이 문서) + Known
  Issues 섹션.
- **제거**: Whitelist 탭의 "Reset to Defaults" 버튼 — 모든 기본값이
  OFF 라 "Deactivate All" 과 동일한 결과를 내던 redundant 버튼.

---

## [0.4.5] — 2026-05-05

- **안전장치 추가**: 짧은 영어 단어가 다른 영어 단어 중간에 박혀
  있을 때 (예: `Catalog` 안의 `Cat`, `Daybreak` 안의 `Day`,
  `Fireplace` 안의 `Fire`, `Hardware` 안의 `Hard`) 의도치 않은 부분
  매치로 잘못 변환될 수 있는 케이스를 차단. 이런 안전장치가 없으면
  이론상 `Catalog` → `고양이alog` 같은 깨진 출력이 발생 가능.
- **수정**: **Expanded Storage**
  ([modworkshop/56126](https://modworkshop.net/mod/56126)) 모드와의
  호환성 — 같이 사용 시 컨테이너 크기 확장 효과 (Fridge / Cabinet /
  Office Cabinet / Nightstand / Medical Cabinet) 가 정상 적용됨.
- **추가**: 상인 이름 (Generalist / Doctor / Gunsmith / Driver /
  Grandma / Shaman / Fisherman / Scientist) 과 적대 진영 이름
  (Bandit / Guards / Military / Punisher) 이 다른 모드 (예:
  ImmersiveXP) 가 라벨 앞에 prefix 를 붙이는 경우에도 번역되도록
  처리.
- **이름 정비**: "Compatible Mode" 체크박스 명칭을 "Substr Mode"
  로 변경 (실제 동작에 맞춘 이름 정정. 기존 설정은 자동 이전되며
  사용자 측 조치 불필요).

## [0.4.4] — 2026-05-05

- **추가**: 튜토리얼 퇴장 시 표시되는 "Tutorial Exit" 텍스트가
  로케일에 맞게 번역됨 (이전엔 영어로 노출).

## [0.4.3] — 2026-05-05

- **수정**: 게임 도중 언어 변경 시 인벤토리 / 설정 / 이미 열려
  있던 UI 가 새 언어로 갱신됨. 이전엔 일부 라벨이 게임 재시작
  전까지 이전 언어로 남아 있었음.

## [0.4.2] — 2026-05-05

- **수정**: 상자 열기 / Trader 상호작용 시 짧은 끊김 (hitch) 해결.

## [0.4.1] — 2026-05-05

- **수정**: 인벤토리 처음 열 때 `Hybrid` 같은 일부 아이템 이름이
  글자가 누적되어 (`Hybride` → `Hybridee` → `Hybrideee` ...) 깨지던
  버그.
- **수정**: 프랑스어 인트로 문구 줄바꿈을 다른 로케일과 정렬.

## [0.4.0] — 2026-05-05

- **추가**: **프랑스어 지원** (DeepL 1차 기계번역. 공개 저장소 준비
  완료 후 커뮤니티 검수 예정).
- **수정 (한국어)**: 텍스트 일부 오번역 + 튜토리얼 빌보드 텍스처
  오타 (접격지대 → 접경지대).
- **수정**: 게임 빌드 0.1.1.3 에서 Trader 패널 라벨 (Tax / Tasks
  / Resupply) 및 일부 anchored 라벨 위치가 어긋나던 현상 해결.

## [0.3.4] — 2026-04-26

- **수정 (한국어)**: 월드맵 텍스처의 잘못 그려진 도로 안내선.

## [0.3.3] — 2026-04-26

- **추가 (한국어)**: 한국어 월드맵 텍스처 (지명, 장식 오버레이).

## [0.3.2] — 2026-04-24

- **추가**: 게임 빌드 0.1.1.3 에 새로 도입된 텍스트 번역
  (해상도 `Native`, `Image Sharpness`, SMAA 토글, 호환 렌더러
  경고, killbox 메시지 등).
- **수정 (한국어)**: 컨텍스트별 오번역 보정 (예: `Border` →
  접경지대, 음악 프리셋 관련 수정).

## [0.3.1] — 2026-04-22

- **개선**: 모드 호환성 향상 — 다른 모드가 매 프레임 라벨을 영어로
  덮어쓰는 케이스에 대해, 언어 UI (F9) 의 Whitelist 탭에서 해당
  라벨을 매 프레임 변환되도록 켤 수 있음.

## [0.3.0] — 2026-04-22

- **추가**: 텍스처 번역 시스템 — 게임 내 이미지를 로케일별 번역본
  으로 교체. 첫 적용: 한국어 튜토리얼 빌보드.

## [0.2.3] — 2026-04-21

- **개선 (한국어)**: UI / 아이템 텍스트 번역 다듬기.

## [0.2.2] — 2026-04-20

- 핫픽스.

## [0.2.1] — 2026-04-20

- 핫픽스.

## [0.2.0] — 2026-04-20

- **수정 (한국어)**: Trader Event Descriptions 등 누락 번역 보완.

## [0.1.0] — 2026-04-17

- **추가 (한국어)**: UI / 툴팁 / 아이템 / 작업 / 이벤트 / 트레이더
  를 커버하는 초기 한국어 번역 출시.
