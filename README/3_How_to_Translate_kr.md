# 3. 번역 작업 가이드 (한국어)

`Trans To Vostok/<locale>/Translation.xlsx` 를 직접 편집해서 번역하는 흐름입니다. 새 locale 추가는 [2_Add_new_language_kr.md](2_Add_new_language_kr.md) 참조.

---

## 1. 사전 준비

- [0_Setting_Environments_kr.md](0_Setting_Environments_kr.md) 의 셋업 (Excel / Python / Git / Fork & Clone) 완료
- 작업할 locale의 xlsx 파일 위치 확인:
  ```
  Trans To Vostok/<locale>/Translation.xlsx
  Trans To Vostok/<locale>/Glossary.xlsx
  Trans To Vostok/<locale>/Texture.xlsx
  ```

---

## 2. MetaData 시트 — 본인 정보 등록

각 xlsx 파일의 **MetaData** 시트에서 번역 담당자 / 기여자 정보를 갱신합니다. 빌드 시 이 정보가 `Translation_Credit.md` / `AUTHORS.md` 에 자동 반영됨.

| 역할                           | MetaData 의 Field                             |
| ------------------------------ | --------------------------------------------- |
| 메인 번역자                    | `Translator`                                |
| 보조 기여자                    | `Contributor (Translate)`                   |
| 텍스처 / 이미지 작업 (Primary) | `Reworked by` (Texture.xlsx의 각 시트에서)  |
| 텍스처 / 이미지 작업 (보조)    | `Contributors` (Texture.xlsx의 각 시트에서) |

여러 명을 한 셀에 적을 때는 **셀 안에서 줄바꿈** (`Alt+Enter`).

> 자세한 크레딧 규칙은 `CONTRIBUTING.md` 의 "How to be credited" 섹션 참조. `AUTHORS.md` 직접 편집은 금지 (자동 생성 영역이 덮어써짐).

---

## 3. 번역 시트의 컬럼 의미

`Translation.xlsx` 의 각 시트 (Main / Interface / Items / Tasks / ToolTips 등) 컬럼:

| 컬럼                                                                         | 의미                                                         | 번역가가 건드릴까?                                    |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------- |
| **WHERE**                                                              | 게임 화면 / 영역 분류 (예:`UI`, `Inventory`, `Trader`) | ❌ 분류용 메타데이터                                  |
| **SUB**                                                                | WHERE 안에서의 하위 분류 (예:`Armor/Armor_Plate_II`)       | ❌ 분류용 메타데이터                                  |
| **KIND**                                                               | 항목 종류 (예:`Label`, `Button`)                         | ❌ 분류용 메타데이터                                  |
| Transliteration                                                              | 음역 사용 여부 (1/0)                                         | 필요 시 ✅                                            |
| Transcreation                                                                | 의역 / 창작 번역 여부 (1/0)                                  | 필요 시 ✅                                            |
| Machine translated                                                           | 기계 번역 여부 (1/0) — DeepL 결과면 1                       | 검토 후 ✅                                            |
| Confused                                                                     | 번역 모호 / 확신 부족 표시 (1/0)                             | 필요 시 ✅                                            |
| untranslatable                                                               | 번역 불가 (예: 코드 식별자)                                  | ❌ 구조적, 변경 금지                                  |
| **method**                                                             | 매칭 방식 (substr / literal / static / pattern / ignore)     | 일반적으로 ❌ ([4. 새 행 추가](#4-새-행-추가-선택) 참조) |
| filename / filetype / location / parent / name / type / property / unique_id | RTV 게임 소스의 식별자                                       | ❌ 자동 생성, 변경 금지                               |
| **text**                                                               | **원문 (영어)**                                        | ❌ 절대 변경 금지                                     |
| **translation**                                                        | **번역문** — 여기에 번역 입력                         | ✅ 작업 대상                                          |
| DESCRIPTION                                                                  | 번역가용 메모 / 컨텍스트                                     | 필요 시 ✅                                            |

### WHERE / SUB / KIND 는 무엇인가

번역 내용을 게임 내 화면 / 영역별로 **분류**하기 위한 메타데이터입니다. 시트 내 그룹 분리선 (Excel에서 굵은/얇은 가로선) 도 이 컬럼 변경 지점에서 자동 생성. 번역 작업 시에는 **읽기 전용**으로 취급.

### Quality flag (Transliteration / Transcreation / Machine translated / Confused)

번역 품질 / 방식을 표시하는 플래그입니다 (0 또는 1). 본인이 번역한 내용에 대해 정직하게 표시:

- **DeepL 같은 기계 번역 결과를 그대로 두면 → `Machine translated=1`**
- **검토 후 다듬은 결과 → `Machine translated=0`** (사람의 번역으로 간주)
- 음역 (예: "Vostok" → "보스토크") → `Transliteration=1`
- 창작 의역 → `Transcreation=1`
- 확신 안 서서 다른 사람 검토 필요 → `Confused=1`

---

## 4. 일반 번역 작업 흐름

1. 작업할 시트 (예: `Items`) 열기
2. 각 행의 `text` (원문) 보고 → `translation` 셀에 번역 입력
3. 필요 시 quality flag 갱신
4. 저장 (Excel 기본 단축키 `Ctrl+S`)
5. 빌드로 검증:
   ```powershell
   python tools/build_mod_package.py <locale>
   ```
6. 게임에서 모드 활성화 후 실제 표시 확인

> 빌드 시 `parsed_text/` 가 없으면 일부 검증이 자동으로 스킵됩니다 (자세한 내용 [1_unpack_and_decompile_game_kr.md](1_unpack_and_decompile_game_kr.md) 참조). duplicate / flags / method 등 xlsx 자체 검증은 그대로 동작.

### ⚠️ 주의 — 앞뒤 공백 / 줄바꿈 매칭

게임 원문 자체가 앞뒤에 공백 또는 줄바꿈 (`\n`)을 포함하는 경우가 있습니다 (예: `"\n\nReload [R]"`, `"Health:\n"`). 빌드 검증의 whitespace 체크는 **`text` 와 `translation` 의 앞뒤 공백/줄바꿈이 일치하는지** 확인 — 다르면 WARNING이 나고, 게임 화면에서도 줄간격이 어긋나거나 잘릴 수 있음.

작업 팁:

- 원문의 앞뒤 공백 / 줄바꿈 패턴을 그대로 번역에도 보존
- Excel 셀 내 줄바꿈은 `Alt+Enter`
- `text` 셀에 보이지 않는 trailing space가 있는지 의심되면 셀 클릭 후 수식 입력줄에서 끝까지 커서 이동해 확인
- 빌드 후 `Trans To Vostok/<locale>/.log/validate_translation_*.log` 에서 `whitespace` 카테고리 WARNING 확인

---

## 5. 새 행 추가 (선택)

게임에 있는 텍스트인데 xlsx에 없는 것을 번역하고 싶거나, 추가 번역 케이스 (예: 모드 호환성)를 넣고 싶을 때 행을 추가할 수 있습니다. 가능하면, 번역 누락에 대해서는 GitHub에 Issue를 등록해주세요.

### 권장: `method = substr`

추가 행은 기본적으로 `method` 를 **`substr`** 로 설정. 의미: "원문 안에 이 text가 부분 문자열로 등장하면 translation으로 치환".

| 컬럼                                                                             | 새 행 권장값                       |
| -------------------------------------------------------------------------------- | ---------------------------------- |
| WHERE / SUB / KIND                                                               | 적절히 분류 (자유, 단 일관성 유지) |
| method                                                                           | **`substr`**               |
| text                                                                             | 원문 (게임에 등장하는 영문 그대로) |
| translation                                                                      | 번역문                             |
| filename / filetype / location / parent / name / type / property / unique_id     | (substr 행은 비워둬도 됨)          |
| Transliteration / Transcreation / Machine translated / Confused / untranslatable | 보통 0                             |
| DESCRIPTION                                                                      | 왜 이 행을 추가했는지 메모 권장    |

### 다른 method 는?

`literal`, `static`, `pattern`, `ignore` 등 다른 method 는 RTV 게임 소스의 특정 위치/패턴에 정확히 매칭하는 고급 케이스입니다. **별도 method 가이드** (예정 문서)에서 자세히 다룰 예정.

> **`method = static` 인 행은 같은 원문을 등장 위치(`filename` / `parent` / `name` / `unique_id` 등)에 따라 다르게 번역할 수 있습니다.**
> 예: `NVG` 가 인벤토리 아이템 라벨에는 "야투경", 튜토리얼 본문에는 "야간투시경 (NVG)" 처럼 컨텍스트별로 다른 번역 적용. 이런 케이스는 `static`의 source 식별 컬럼 (filename / parent / name / type / property / unique_id) 이 모두 정확히 매칭돼야 동작 — 보통 자동 생성된 행을 그대로 두고 `translation`만 수정.

> **`method = ignore` 인 행은 게임 내 번역에 반영되지 않습니다.** 원문은 등록되어 있지만 의도적으로 번역을 적용하지 않는 (예: 게임 제목 "Road to Vostok") 케이스. 새 행 추가 시 일반적으로는 사용하지 않음.

새로 행을 추가할 때 위 method 들을 잘 모르겠으면 **`substr`만 사용**해도 대부분의 케이스 커버됨. substr가 너무 광범위하게 매칭될 우려가 있으면 issue로 문의.

---

## 6. 검증 & 커밋

### 6-1. 빌드 검증

```powershell
python tools/build_mod_package.py <locale>
```

성공 시:

- `Trans To Vostok.zip` 생성 (게임에서 ModLoader가 인식)
- `Translation_TSV/<locale>/` 의 TSV shadow 갱신 (git diff용)

검증 에러가 나면 콘솔 출력 / `Trans To Vostok/<locale>/.log/validate_translation_*.log` 확인.

### 6-2. 게임 실행 후 실제 표시 확인

빌드만 통과해도 게임 화면에서 의도대로 보이는지는 별개입니다 — 텍스트 길이가 UI를 넘어가거나, 줄바꿈이 어색하거나, 컨텍스트상 부적합한 번역인 경우 빌드 단계에서 잡히지 않음.

1. **Road to Vostok** 실행
2. ModLoader가 `Trans To Vostok.zip` 을 정상 로드하는지 확인
3. 게임 내 언어 설정에서 작업한 locale 선택
4. **번역한 부분을 실제로 방문하여 확인**:
   - 메뉴 / 인벤토리 / Trader UI / Tutorial 등
   - 텍스트가 잘려 보이거나 박스를 넘어가는지
   - 다른 언어 / 영어가 섞여 보이는지 (= unmatched 행 존재 가능성)
   - 컨텍스트상 어색한 의역이 없는지
5. 수정할 부분 발견 시 → Excel로 돌아가 재편집 → [6-1](#6-1-빌드-검증) 반복

> 모드 변경사항이 게임에 반영되지 않으면 ModLoader 재로드 (게임 재시작 또는 ModLoader 핫 리로드 기능) 가 필요할 수 있음.

### 6-3. Commit & Push

```powershell
git add "Trans To Vostok/<locale>/Translation.xlsx" "Translation_TSV/<locale>/"
git commit -m "<locale>: improve Items translations"
git push origin <branch-name>
```

xlsx는 binary라 PR 리뷰가 어렵지만, 같이 갱신되는 `Translation_TSV/<locale>/` 가 텍스트 diff로 변경 내역 보여줌 → 리뷰가 가능.

---

## 7. 다음 단계

- 셋업 / 일반 작업 흐름 → [0_Setting_Environments_kr.md](0_Setting_Environments_kr.md)
- 게임 소스 추출 (전체 validation 활성화) → [1_unpack_and_decompile_game_kr.md](1_unpack_and_decompile_game_kr.md)
- 새 언어 추가 → [2_Add_new_language_kr.md](2_Add_new_language_kr.md)
- 크레딧 / 코드 기여 → `CONTRIBUTING.md`
- method 가이드 → (별도 문서, 추후 작성 예정)
