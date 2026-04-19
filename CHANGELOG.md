# Changelog — Trans To Vostok

All notable changes to this mod will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

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
