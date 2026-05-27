# Crowdin 웹사이트를 통한 번역 (기본 가이드)

Trans To Vostok의 **모든 번역 기여는 Crowdin 웹사이트를 기본 진입점**으로 합니다.

- 브라우저만 있으면 됩니다. Excel / Python / Git / 코드 편집기는 일체 불필요합니다.
- 번역 데이터의 **단일 source of truth**는 Crowdin입니다. 다른 경로(직접 PR 등)로 보낸 번역 변경은 받지 않습니다.
- 관리자가 주기적으로 Crowdin → 저장소로 sync하며, 다음 모드 빌드부터 게임에 반영됩니다.

> **인게임에서 직접 테스트하면서 번역하고 싶다면** → [Translating_on_Local.md](Translating_on_Local.md) (저장소 클론 + `pull_from_crowdin` + 빌드). 단, 결과물 업로드는 여전히 Crowdin이 최종 목적지입니다.

---

## 1. 시작하기

### 1-1. Crowdin 계정 만들기

- https://crowdin.com 접속 → **Sign up**
- 이메일 인증 완료

### 1-2. 프로젝트 가입

- 프로젝트 사이트: [Trans to Vostok translation project on Crowdin](https://crowdin.com/project/trans-to-vostok)
- 번역 참여는 추가 인증 없이 바로 가능합니다.
- Glossary, 언어별 QA 등 특정 언어에 대한 추가 권한이 필요하신 분(Manager)은 Crowdin 또는 GitHub를 통해 별도로 요청해주십시오.

### 1-3. 작업 언어 선택

- 프로젝트 메인 페이지의 언어 목록에서 본인 언어 클릭 → **Translate** 진입
- 처음 들어가면 짧은 Crowdin Editor 튜토리얼이 표시됩니다 — 한 번 둘러보는 것을 권장합니다.

---

## 2. 번역 파일 구조

번역 대상은 두 카테고리로 나뉩니다:

| 폴더                  | 내용                                       | 비고                                                                                          |
| --------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------- |
| **Translation** | 게임 본문 (메뉴 / UI / 아이템명 / 대사 등) |                                                                                               |
| **Texture**     | 텍스처(이미지) 내 번역해야 할 텍스트       | 이미지 수정/편집 작업은 별도<br />(번역/수정 후 Issue 등록, 또는 이미지 추가 후 Pull Request) |

각 폴더 안에는 시트(파일) 단위로 분리되어 있습니다. 예: `Translation/Main.tsv`, `Translation/Items.tsv`, `Translation/ToolTips.tsv` …

용어집(Glossary)은 별도 폴더가 아닌 **Crowdin 네이티브 Glossary 리소스**로 관리됩니다 — Editor에서 번역 중일 때 우측 패널에 자동 매칭되어 표시되며, 직접 폴더로 보거나 편집하지 않습니다 (자세한 설명은 §5-1).

번역 행마다 다음과 같은 정보가 함께 표시됩니다 (Crowdin Editor 우측 패널):

- **WHERE / SUB / KIND**: 게임 화면 / 영역 분류 (예: `UI` / `Inventory` / `Trader`)
- **method**: 매칭 방식(`substr` / `literal` / `static` / `pattern` / `ignore`) — 참고용이며 일반적으로 번역가가 다룰 필요 없습니다.
- **DESCRIPTION**: 개발자 노트 (있으면 컨텍스트 힌트로 활용)

> **읽기 전용 컬럼**은 절대 수정하지 마십시오. Crowdin Editor에서는 원문(`source`)도 수정할 수 없습니다 — 이는 정상 동작이며, 원문 수정이 필요한 경우 GitHub Issue로 알려주십시오.

---

## 3. Editor 기본 사용법

### 3-1. 화면 구성

```
+----------------+----------------------------------------+----------------+
| 좌측: 문자열   | 중앙: 원문 + 번역 입력란               | 우측: 컨텍스트 |
| 목록 / 필터    |                                        | TM / Glossary  |
+----------------+----------------------------------------+----------------+
```

### 3-2. 자주 쓰는 단축키

| 단축키           | 동작                                |
| ---------------- | ----------------------------------- |
| `Ctrl + Enter` | 번역 저장 + 다음 미번역 행으로 이동 |
| `Ctrl + Down`  | 다음 행                             |
| `Ctrl + Up`    | 이전 행                             |
| `Tab`          | 우측 TM/Glossary 매칭 사용          |

### 3-3. 필터링 팁

좌측 상단 필터로 작업량을 관리합니다.

- **Untranslated**: 아직 번역되지 않은 행 (가장 먼저 처리)
- **Need to be reviewed**: 번역은 입력됐으나 미승인 (Proofreader 검수 대기)
- **With suggestions**: TM / 기계 번역 제안이 있는 행

라벨로도 필터링이 가능합니다 — 메인테이너가 라벨을 붙여 둔 경우(`#priority-high`, `#tutorial` 등).

### 3-4. 자동 저장

번역 입력란을 떠나면(`Ctrl + Enter` 또는 다른 행 클릭) 자동 저장됩니다. 별도 저장 버튼은 없습니다.

### 3-5. Comments / Issues

- 원문이 모호하거나 컨텍스트가 없는 경우 → 해당 행에 **Comment** 작성 → 메인테이너가 답변합니다.
- 명백한 원문 오류 / 누락인 경우 → **Issue**를 등록합니다 (Editor 내 깃발 아이콘).

---

## 4. QA 다이얼로그 다루기

번역 저장 시 Crowdin이 **QA 체크**를 수행합니다. 일부 항목은 저장을 차단할 수 있습니다(`Review Issues to save`).

| QA 항목                       | 의미                                       | 일반적인 대처                                    |
| ----------------------------- | ------------------------------------------ | ------------------------------------------------ |
| **Numbers consistency**       | 원문의 숫자가 번역에서 빠지거나 추가됨     | 숫자 보존이 원칙. 의역이라면 `Save anyway`       |
| **Punctuation consistency**   | 괄호 / 따옴표 등 문장부호가 매칭되지 않음  | 동일. 한국어 관용 표현이라면 `Save anyway`       |
| **Tags consistency**          | `{0}`, `%s` 같은 placeholder 누락 / 변경   | **반드시 보존합니다**. 게임이 깨질 수 있습니다.  |
| **Spaces around variables**   | placeholder 주변 공백이 어긋남             | 원문에 맞춥니다.                                 |
| **Translation length**        | 번역이 너무 길거나 짧음                    | 권장 길이를 넘으면 UI 잘림 우려 — 최대한 줄입니다.|

### 4-1. `Save anyway`를 사용해도 되는 경우

- 한국어로 옮겼을 때 자연스러운 표현이 원문 부호와 다른 경우 (예: `"Cabinet. 0"` → `"수납장 (나무)"` — 원문의 `0`은 게임 내 변종 ID라 사용자에게 의미가 없습니다)
- 원문의 영문 따옴표/대시가 한국어 문맥에서 어색해 다른 부호로 바꾼 경우

### 4-2. `Save anyway`를 절대 사용하면 안 되는 경우

- **Tags consistency 경고**: `{0}`, `%s`, `<color>...</color>` 같은 placeholder는 게임 코드와 직접 연결돼 있습니다. 빠뜨리면 런타임 에러 / 잘못된 표시가 발생합니다.
- 원문의 핵심 숫자가 의미 있는 경우 (예: 날짜, 좌표, 아이템 수량)

판단이 애매하면 해당 행에 Comment를 남기고 메인테이너의 의견을 기다립니다.

---

## 5. Glossary / TM 활용

### 5-1. Glossary (용어집)

프로젝트에 연결된 **Crowdin 네이티브 Glossary 리소스**의 용어가 Editor 우측 패널에 자동으로 매칭되어 표시됩니다 (현재 source 문자열에 등록 용어가 포함될 때).

- 게임 고유명사 / 핵심 용어의 **일관된 번역**을 보장합니다.
- 매칭이 표시됐을 때 클릭하면 입력란에 자동으로 삽입됩니다.
- Glossary 전체 보기는 Crowdin 메인 메뉴 → **Resources → Glossaries**에서 확인 / 검색할 수 있습니다.
- 새 용어를 발견하거나 기존 용어 번역을 수정하고 싶으면 해당 행에 Comment를 남기거나 메인테이너에게 제안합니다 → 메인테이너가 Glossary에 추가 / 수정합니다.

### 5-2. TM (Translation Memory)

이미 번역된 비슷한 문자열의 매칭이 우측에 점수와 함께 표시됩니다.

- **100% 매칭**: 그대로 사용해도 됩니다 (단, 컨텍스트가 다를 수 있으니 한 번 검토합니다).
- **부분 매칭**(60–99%): 참고용입니다. 그대로 쓰지 말고, 차이점만 수정해서 사용합니다.

### 5-3. 기계 번역 제안

Editor 우측 패널에 DeepL 등 기계 번역 결과가 표시될 수 있습니다. 출발점으로 활용하되, 게임 컨텍스트는 반드시 직접 검토합니다. 자동 시드 결과가 그대로 채워져 있는 경우(`#Machine Translated` 마커)는 검수 후 정리합니다.

---

## 6. 검수 흐름과 인게임 반영 시점

```
[번역가] Crowdin Editor에서 번역 입력
    ↓
[Proofreader] Crowdin Editor에서 ✓ Approve
    ↓
[메인테이너] 주기적으로 pull_from_crowdin → git commit
    ↓
[다음 모드 빌드] 게임에 반영
```

- 본인이 입력한 번역은 **즉시 Crowdin에 반영**되며, 다른 번역가/검수자에게 보입니다.
- 게임에 실제로 반영되는 시점은 메인테이너의 정기 sync와 모드 재배포 이후입니다.
- Proofreader 권한이 있다면 본인이 입력한 번역에 ✓ Approve를 적용할 수 있습니다.

---

## 7. 크레딧

번역 기여자 명단은 메인테이너의 sync 후 자동으로 `AUTHORS.md`에 반영됩니다. Crowdin 프로필 이름이 그대로 표시되니, 크레딧에 사용할 이름으로 프로필을 설정해 두십시오.

자세한 크레딧 규칙은 `CONTRIBUTING.md`의 *"How to be credited"* 섹션을 참조하세요.

---

## 8. 다음 단계

- **인게임에서 테스트하며 번역하고 싶다** → [Translating_on_Local.md](Translating_on_Local.md)
- **Crowdin Editor 자세한 기능** → [Crowdin 공식 가이드](https://support.crowdin.com/online-editor/)
- **새 언어 추가 (관리자/개발자 영역)** → [Add_new_language.md](../../docs_dev/kr/Add_new_language.md)
