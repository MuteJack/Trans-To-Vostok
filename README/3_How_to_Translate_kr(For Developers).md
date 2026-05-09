# 3. 번역 작업 가이드 — 개발자용 (한국어)

[3_How_to_Translate_kr.md](3_How_to_Translate_kr.md) 의 **확장판**입니다. 일반 번역 작업이 아닌, 새 행 추가 / method 선택 / 매칭 디버깅이 필요한 코드 기여자 / 메인테이너 대상.

---

## 1. 데이터 모델 개요

### xlsx 시트 구조

- **MetaData** — 번역자 / 기여자 정보. 빌드 시 `Translation_Credit.md` 등에 반영
- **번역 시트들** (Main / Interface / Items / Tasks / ToolTips 등) — 동일 스키마

### 한 행이 나타내는 것

"게임의 어떤 위치/패턴에서 등장하는 어떤 원문 (`text`) 을 어떻게 번역 (`translation`) 할 것인가" 에 대한 **하나의 매칭 규칙**.

행은 빌드 시 method + location 조합에 따라 6개 runtime 버킷으로 분류돼서 `runtime_tsv/translation_*.tsv` 로 출력됨.

### 빌드 시 제외 조건

- `method = ignore`
- `untranslatable = 1`
- `translation` 빈 값

위 셋 중 하나라도 해당하면 runtime TSV에 포함 안 됨 (게임 내 번역 미적용).

---

## 2. method — 매칭 전략

| method                            | 의미                                                                                                                                                                         | 매칭 컨텍스트 | 예시                                                               |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------ |
| **static**                  | 게임 소스의 정확한 5-tuple (`location`/`parent`/`name`/`type`/`property`) + `unique_id` 에 결합된 고정 매칭. 같은 `text`도 위치별로 다른 `translation` 가능. | 위치 기반     | UI label `Items/...:Label.text = "NVG"` → "야투경"              |
| **literal** + location      | 특정 소스 위치 안에서만 동작하는 정확 일치 ("scoped literal"). 동적 텍스트 처리.                                                                                             | 위치 기반     | `Health: {value}` 라벨이 `Items/HUD/Health` 에서만 등장        |
| **literal** (location 없음) | 전역 정확 일치 ("literal global").`text == 게임에서 발생한 문자열` 일 때 매칭.                                                                                             | 전역          | "Inventory" → "인벤토리" 어디에 등장하든 동일                     |
| **pattern** + location      | 위치 한정 정규식 ("scoped pattern").                                                                                                                                         | 위치 기반     | 특정 라벨에서 `^\\d+%$` 형식만 매칭                              |
| **pattern** (location 없음) | 전역 정규식 ("pattern global").                                                                                                                                              | 전역          | `^Round (\\d+)$` → `라운드 \\1`                               |
| **substr**                  | 부분 문자열 치환. 다른 method가 매칭 안 됐을 때의 fallback.<br />번역 작업 시, 가장 기본이 되는 method.                                                                      | 전역          | "Open" 이 `[Open] Locked Door` 안에 있으면 "[열림] 잠긴 문" 으로 |
| **ignore**                  | 빌드 시 제외. runtime에 안 나감.                                                                                                                                             | —            | 게임 제목 "Road to Vostok"처럼 의도적으로 번역 안 함               |

### Runtime 매칭 우선순위 (translator.gd)

게임에서 텍스트 치환 시도는 다음 순서로 진행됨 (먼저 매칭되면 끝):

1. **static exact** — 5-tuple TSV-validated 정확 매칭
2. **scoped literal exact** — 5-tuple + 동적 텍스트
3. **scoped pattern exact** — 5-tuple + regex
4. **literal global** — text 전역 정확 일치
5. **pattern global** — 전역 regex
6. **static score** — 부분 컨텍스트 매칭 (게임 업데이트로 5-tuple 변경 시 fallback)
7. **scoped literal score** — 부분 컨텍스트 + 동적 텍스트
8. **scoped pattern score** — 부분 컨텍스트 + regex
9. **substr** — 부분 문자열 치환 (텍스트 길이 내림차순 정렬, 마지막 fallback)

> static이 최우선이라, 같은 text를 가지는 literal global이 있어도 static이 먼저 잡으면 그쪽이 적용됨. 행 충돌이 의심되면 우선순위 위쪽 method부터 검토.

> **substr 모드** (`_substr_mode = true` 시): literal_global / static_exact 항목들이 substr_entries 에도 자동 등록됨. 노드 컨텍스트 매칭이 미스 나도 substr fallback으로 부분 매칭 가능 — 모드 호환성 케이스 (예: ImmersiveXP가 라벨에 prefix 추가) 대응용.

---

## 3. 식별자 컬럼 (Godot 소스 결합)

이 컬럼들은 RTV 게임의 `.tscn` / `.tres` / `.gd` 에서 자동 추출됨. 일반적으로 **자동 생성된 값을 그대로 두고 변경하지 않음**.

| 컬럼          | 의미                                                                | 예시                           |
| ------------- | ------------------------------------------------------------------- | ------------------------------ |
| `filename`  | 소스 파일의 가상 경로 (확장자 없이)                                 | `Items/Armor/Armor_Plate_II` |
| `filetype`  | 소스 파일 타입                                                      | `tscn`, `tres`, `gd`     |
| `location`  | 파일 안의 위치 마커 (line / 노드 path 등). 비어있으면 "global" 취급 | `node_3` 또는 line number    |
| `parent`    | Godot 노드 트리의 부모 경로                                         | `Content/Panel/Margin/VBox`  |
| `name`      | 노드 이름                                                           | `Title`                      |
| `type`      | 노드 타입 (Label, Button 등)                                        | `Label`, `RichTextLabel`   |
| `property`  | 노드의 어떤 프로퍼티에 들어있는 텍스트인지                          | `text`, `placeholder_text` |
| `unique_id` | 위 5-tuple로부터 파생된 고유 식별자                                 | (해시 또는 직접 부여된 값)     |

### 새 행을 추가할 때

- **`method=substr`**: 위 식별자 컬럼들은 비워둠. 전역 부분 문자열 치환만 동작.
- **`method=literal global`** (literal + location 없음): `text`만 채우면 됨.
- **`method=static / literal_scoped / pattern_scoped`**: 게임 소스에 정확히 매칭하는 식별자가 필요. 잘못 적으면 매칭 실패. **자동 추출된 행을 활용**하는 게 안전.

---

## 4. WHERE / SUB / KIND — 분류 메타데이터

매칭과 무관, 순수히 xlsx 정리/시각화용:

- **WHERE** — 게임 화면 / 영역 (`UI`, `Inventory`, `Trader` 등)
- **SUB** — WHERE 내 하위 분류 (예: `Armor/Armor_Plate_II` — Korean 작업에선 filename의 마지막 segment를 SUB에 부착하는 정책 사용)
- **KIND** — 항목 종류 (`Label`, `Button`, `Tooltip` 등)

빌드 도구의 영향:

- 빌드 시 검증의 duplicate 체크는 (method, text, 위치 식별자) 기반 — WHERE/SUB/KIND 자체는 매칭에 안 들어감
- xlsx의 그룹 분리선 (굵은/얇은 가로선) 이 WHERE / SUB 변경 지점에서 자동 생성 (rebuild_xlsx.py 정책)

### 일관성 권장 사항

- 같은 영역의 행은 WHERE 일치
- SUB는 filename 또는 의미 기반으로 묶어 유지
- 새 행 추가 시 인접 행의 WHERE/SUB/KIND 패턴 따라감

---

## 5. Quality flag 운영 가이드라인

xlsx에는 단일 status flag만 유지:

| Flag             | 1로 두는 기준                                                               |
| ---------------- | --------------------------------------------------------------------------- |
| `untranslatable` | 번역 자체가 불가능 / 무의미한 항목 (코드 식별자, 숫자 등). 빌드/Crowdin push에서 제외됨 |

검수 상태 (이 번역이 검수 완료인지 / MT 잔재인지) 는 **Crowdin이 관리**:
- Crowdin Editor에서 **Approve (✓)** 버튼 = 검수 완료
- 미승인 상태 = 검토 필요 (구 `Machine translated=1` / `Confused=1` 통합)

`Comments` 컬럼은 **자유 메모 + DeepL 출처 마커** (`#Machine Translated`) 용도. 직접 검수 플래그로 쓰지는 않음 (Crowdin과 동기화 안 됨).

### Korean 작업 정책 (참고)

- DeepL 초기 패스 → `Comments`에 자동 `#Machine Translated` 마커 추가
- 사람 검수 → Crowdin에서 Approve 누르면 검수 완료 표시
- 모호한 번역: Crowdin **Issue** 기능으로 표시하거나 `Comments`에 자유 메모

---

## 6. DESCRIPTION — 번역가 메모

자동 생성되지 않는 자유 형식. 다음 케이스에 적극 활용:

- "왜 이 행을 추가했는가" (특히 method=substr)
- 모드 호환성 케이스의 출처 (예: "ImmersiveXP의 prefix `\\n\\n{x}` 처리용")
- 번역 선택의 이유 (예: "야투경 vs 야간투시경 — 길이 제한으로 야투경 선택")
- 다른 행과의 우선순위 / 충돌 메모

빌드 시 무시되며 게임에는 들어가지 않음.

---

## 7. 충돌 해결

### 같은 text + 다른 translation

가능한 시나리오:

- **의도적**: 위치별로 다른 번역 → `method=static` 사용 (가장 우선)
- **실수**: literal global 두 행 모두 동일 text 가짐 → duplicate 검증에서 ERROR

### Duplicate 검증

빌드 시 `check_duplicates` (intra-sheet) + `check_duplicates_cross_sheet` 가 다음 키 기반으로 중복 검출:

- 위치 컬럼이 다 있는 경우 (static / scoped) — `(method, location, parent, name, type, property, unique_id, text)`
- 위치 없는 경우 (literal global / pattern global / substr) — `(method, text)`

같은 키에 다른 translation이 등록되어 있으면 ERROR. 의도적으로 다르게 하려면 method를 static / scoped 로 승격.

### Method 우선순위 충돌

같은 text를 가진 두 행이 method가 다르면, runtime 우선순위에 따라 위쪽 method가 이김 (위 [§2의 8단계 우선순위](#runtime-매칭-우선순위-translatorgd)). 의도와 다르게 동작하면 우선순위 우선 검토.

---

## 8. 빌드 / 검증 흐름

### 검증 (`tools/validate_translation.py`)

- **parsed_text 의존 (RTV 게임 소스 추출 필요)**
  - check_tsv_match (method=static의 5-tuple TSV-validated 매칭)
  - check_tres_text (.tres 원문 존재 검증)
  - check_gd_text (.gd 원문 존재 검증)
- **xlsx 자체 검증 (parsed_text 부재 시도 동작)**
  - check_flags (quality flag 0/1 값 검증)
  - check_method_fields (method별 필수 필드)
  - check_empty_method (empty method + unique_id 채워짐 → static 권장)
  - check_whitespace (text ↔ translation 앞뒤 공백/줄바꿈 매칭)
  - check_duplicates / check_duplicates_cross_sheet

### Runtime TSV 분류 (`tools/utils/build_runtime_tsv.py`)

빌드 결과는 6개 TSV로 분리:

```
runtime_tsv/
├── metadata.tsv
├── translation_static.tsv          (5-tuple + text + translation)
├── translation_literal_scoped.tsv  (5-tuple + text + translation)
├── translation_pattern_scoped.tsv  (5-tuple + text + translation)
├── translation_literal.tsv         (text + translation only)
├── translation_pattern.tsv         (text + translation only)
└── translation_substr.tsv          (text + translation only)
```

`translator.gd` 가 이 파일들을 읽어서 위 §2의 우선순위로 매칭.

---

## 9. 새 method를 사용하는 행 추가 워크플로

1. xlsx에 행 추가
2. method 결정:
   - "이 영문이 게임 어디에 등장하든 동일하게 번역" → `literal` (location 비움)
   - "특정 위치에서만 / 다른 위치엔 다른 번역" → `static` 또는 `literal` + location
   - "정규식이 필요" → `pattern`
   - "다른 게 안 맞으면 부분 문자열 치환" → `substr`
3. method = static / scoped 인 경우: 게임 소스에서 정확한 5-tuple 추출 필요 → [1_unpack_and_decompile_game_kr.md](1_unpack_and_decompile_game_kr.md) 참조
4. 추가 후 `python tools/validate_translation.py <locale>` 로 검증
5. duplicate / TSV match 에러 없으면 빌드 → 게임 테스트

---

## 10. 다음 단계

- 일반 번역 가이드 → [3_How_to_Translate_kr.md](3_How_to_Translate_kr.md)
- 셋업 → [0_Setting_Environments_kr.md](0_Setting_Environments_kr.md)
- 게임 소스 추출 → [1_unpack_and_decompile_game_kr.md](1_unpack_and_decompile_game_kr.md)
- 새 언어 추가 → [2_Add_new_language_kr.md](2_Add_new_language_kr.md)
- 크레딧 / 코드 기여 → `CONTRIBUTING.md`
