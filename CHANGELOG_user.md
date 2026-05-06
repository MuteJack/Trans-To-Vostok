# Changelog (User) — Trans To Vostok

A short, user-facing summary of changes you may notice in-game.
For full developer-level details (code paths, refactors, internal
tooling), see [`CHANGELOG.md`](CHANGELOG.md).

---

## Known Issues

- **Select Language UI (F9)** — some labels in the language-selection
  window are themselves being translated when they should remain in
  their source text. Fix planned.

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

- **Select Language UI (F9)** — 언어 선택 창의 일부 라벨이 의도와
  다르게 번역됨 (해당 UI 는 항상 원본 텍스트로 유지되어야 함).
  수정 예정.

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
