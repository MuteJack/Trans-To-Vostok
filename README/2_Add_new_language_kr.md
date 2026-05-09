# 2. 새 언어 추가하기 (한국어)

새 locale을 추가해서 자동 번역 (DeepL)으로 초기 번역 셋을 만든 뒤, 사람이 다듬어 완성하는 흐름입니다.

> CONTRIBUTING.md의 "Adding a new language with DeepL machine translation" 섹션의 한국어판입니다.

---

## 1. 사전 준비

[0_Setting_Environments_kr.md](0_Setting_Environments_kr.md) 의 셋업이 끝났다고 가정합니다. 추가로 필요한 것:

1. **DeepL API key** (Free 또는 Pro)
   - 가입: [https://www.deepl.com/pro-api](https://www.deepl.com/pro-api)
   - 키를 `secrets.json` 의 `deepl_api_key` 필드에 입력 (repo 루트, gitignored). `secrets.example.json` 복사해서 시작.
   - 또는 환경 변수 `DEEPL_AUTH_KEY` 로 설정
2. **DeepL 언어 코드** 확인
   - 예: `FR` (French), `JA` (Japanese), `PT-BR` (Brazilian Portuguese)
   - 전체 목록: [https://developers.deepl.com/docs/getting-started/supported-languages](https://developers.deepl.com/docs/getting-started/supported-languages)
3. (선택) **DeepL Free 쿼터 확인** — 월 500K 글자
   - 한국어 풀 소스 기준 unique 약 62K 글자 → Free로 한 달에 약 8개 언어 + 재시도 여유

---

## 2. Step 1 — Template 최신화

이 프로젝트는 **TSV가 canonical, xlsx는 그로부터 빌드되는 파생물**입니다. 새 locale 작업 전에 Template (= 새 locale의 시작점)이 fresh 상태인지 확인:

```powershell
# (선택) Korean에서 변경된 게 있다면 먼저 Template TSV에 sync
python d:/tmp/sync_locale_to_korean.py Template --apply
# (sync 도구는 정착되면 tools/utils/로 이동 예정)

# Template TSV → Template xlsx 재빌드 (현재 서식 / 너비 / 조건부 서식 자동 적용)
python tools/rebuild_xlsx.py Template
```

이 단계 이후 Template TSV와 Template.xlsx 양쪽 모두 최신 상태.

---

## 3. Step 2 — 새 locale 생성 (Template 복사)

Step 1에서 Template.xlsx가 fresh로 만들어졌으니, 새 locale은 Template 폴더를 그대로 복사하면 됨 (별도 rebuild 불필요).

```powershell
$loc = "French"   # 추가할 locale 폴더 이름으로 변경

# 1. xlsx 폴더 복사 (Translation.xlsx / Glossary.xlsx / Texture.xlsx 등)
Copy-Item -Recurse "Trans To Vostok/Template" "Trans To Vostok/$loc"

# 2. TSV 복사 (git diff용 shadow, 처음부터 동기화 상태로 시작)
Copy-Item -Recurse "Translations/Template" "Translations/$loc"
```

결과:

- `Translations/French/Translation.xlsx` / `Glossary.xlsx` / `Texture.xlsx` (Template과 동일, 서식 적용 완료)
- `Translations/French/Translation/*.tsv` (Korean 구조 + translation 컬럼 빈 값)

> Template TSV/xlsx는 Korean을 source-of-truth로 sync된 상태 — 모든 메타데이터 (행 구조 / WHERE/SUB/KIND / filename 등)가 Korean과 일치하고 quality flag는 0, translation은 빈 값. DeepL이 채울 준비 완료.

---

## 4. Step 3 — DeepL 자동 번역 파이프라인

한 번에 export → DeepL → import:

```powershell
python tools/machine_translation_deepl.py French
```

### 옵션

| Flag                | 용도                                                                |
| ------------------- | ------------------------------------------------------------------- |
| `--deepl-lang FR` | 자동 매핑된 코드 override (예:`BrazilianPortuguese` → `PT-BR`) |
| `--limit 10`      | 처음 10개만 번역 (스모크 테스트)                                    |
| `--dry-run`       | export까지만 + 무엇이 번역될지 표시. API 호출 / import 스킵         |

### 내부 단계 (`tools/utils/` 의 3개 스크립트 chained)

1. **`export_unique_text.py French`**
   - `Translation.xlsx` / `Texture.xlsx` / `Glossary.xlsx` 스캔
   - `method=ignore`, `method=pattern`, `untranslatable=1`, 이미 번역된 행은 제외
   - 본문 기준 중복 제거 → `.tmp/unique_text/French/unique.tsv` 작성
2. **`translate_with_deepl.py FR --source French`**
   - 각 unique text를 DeepL에 전송 (placeholder 보호: `{name}` → `<x>{name}</x>`, XML escape)
   - 결과 → `.tmp/unique_text/French/translated_FR.tsv`
   - **재시도 안전**: 텍스트 키 기반이므로 재실행 시 성공한 항목 skip, 실패한 것만 재시도
3. **`import_translations.py French`**
   - 위 결과를 3개 xlsx에 다시 기록

수동으로 단계별 실행도 가능 (예: translate와 import 사이에 LLM 검토 삽입).

### 행별 import 로직

| 행 조건                              | 동작                                                   |
| ------------------------------------ | ------------------------------------------------------ |
| `translation` 이미 채워짐          | skip (사람이 작업한 결과 / 고정값 보존)                |
| `untranslatable=1`                 | 원문을 그대로 복사. `Comments` 변경 안 함              |
| `method=pattern`                   | skip (regex 원본은 기계 번역 불가)                     |
| `method=ignore` + 번역 결과에 있음 | 그 번역 사용. `Comments` 끝에 `#Machine Translated` 추가 |
| `method=ignore` + 번역 결과에 없음 | fallback: 원문 그대로 복사 (예: "Road to Vostok" 제목) |
| 일반 행 + 번역 결과에 있음           | 번역 적용. `Comments` 끝에 `#Machine Translated` 추가    |

---

## 5. Step 4 — `locale.json` 등록

`Trans To Vostok/locale.json` 에 새 항목 추가:

```json
{
  "locale": "French",
  "dir": "French",
  "display": "Français",
  "message": "Sélectionnez une langue",
  "compatible": "Mode compatible (à utiliser si certains textes ne sont pas traduits)",
  "enabled": true
}
```

| 필드           | 의미                                                |
| -------------- | --------------------------------------------------- |
| `locale`     | 내부 식별자 (영문)                                  |
| `dir`        | 폴더명 (위 Step 1에서 만든 이름)                    |
| `display`    | 게임 내 언어 선택 화면 표시명 (해당 언어 표기 권장) |
| `message`    | 그 언어의 "언어 선택" 안내 메시지                   |
| `compatible` | "호환 모드" 안내 텍스트 (일부 미번역 시 사용)       |
| `enabled`    | 게임에 노출 여부                                    |

---

## 6. Step 5 — Build & 검증

```powershell
python tools/build_mod_package.py
```

전체 locale에 대해 다음 항목 재생성:

- runtime TSV (게임 내 `translator.gd`가 로드)
- `Texture_Attribution.md` (locale별)
- `Translation_Credit.md` (locale별)
- `AUTHORS.md` 의 자동 섹션 (전체 locale 통합)
- `Translations/<locale>/<category>/*.tsv` (git diff용 shadow)
- 최종 `Trans To Vostok.zip`

확인 사항:

- `Trans To Vostok/French/Translation.xlsx` — translation 컬럼이 채워졌는지
- `Trans To Vostok/French/runtime_tsv/` — runtime 파일 생성 여부
- `Trans To Vostok.zip` 안에 새 locale 포함 여부

---

## 7. Quirks & 자주 겪는 이슈

### Glossary 상속 주의

Template이 과거에 다른 번역된 locale (예: Korean)에서 복사된 흔적이 있다면, Glossary의 `translation` 컬럼이 그 언어 텍스트로 채워져 있을 수 있음. 파이프라인의 "이미 번역됨" 필터가 그 행들을 skip → 새 locale에서 엉뚱한 언어가 들어감.

해결:

- 새 locale의 `Glossary.xlsx`에서 `translation` 컬럼 비우기, 또는
- (권장) Template의 모든 `translation` 컬럼을 항상 비워두기

### DeepL XML 파싱 에러

원문에 `&`, `<`, `>` 가 있으면 batch 실패 (`Tag handling parsing failed`) 가능. 현재 도구는 자동으로 `&amp;` / `&lt;` / `&gt;` 로 escape해서 보내고 응답에서 복원함.

### 부분 실패 시 재실행

DeepL 호출이 일부 실패 (네트워크 / 쿼터 등) 시 그냥 다시 돌리면 됨:

```powershell
python tools/utils/translate_with_deepl.py FR --source French
```

원문 텍스트를 키로 성공 항목 보존 → 실패 / 신규 항목만 재시도.

### Free 쿼터

DeepL Free: 월 500K 글자. 한국어 풀 unique 약 62K → 한 달에 약 8개 언어 + 재시도 여유.

### 품질 검토

DeepL은 출발점일 뿐, 최종이 아님. 후속 검토 권장:

- **고유 명사 / 게임 용어** (Vostok, Outpost 등): 의도한 표기 규칙 일관성 확인
- **UI 문자열** (짧고 맥락 부족): DeepL이 오역 가능
- **Glossary**: 사람이 직접 큐레이트하는 영역 → DeepL 결과는 초안으로만 사용, 검토/수정 필수

---

## 8. DeepL 없이 수동 번역만 하기

DeepL 사용 안 하고 처음부터 수동 번역만 해도 가능:

1. Step 1 (Template 최신화)
2. Step 2 (새 locale 생성)
3. xlsx의 `translation` 컬럼을 직접 채움
4. Step 4 (`locale.json` 등록)
5. Step 5 (빌드)

DeepL 단계가 없을 뿐 흐름은 동일. 시간이 오래 걸리지만 품질이 일관적.

---

## 9. 다음 단계

- 일반 작업 흐름 → [0_Setting_Environments_kr.md](0_Setting_Environments_kr.md) 6장
- 게임 소스 추출 (선택) → [1_unpack_and_decompile_game_kr.md](1_unpack_and_decompile_game_kr.md)
- 크레딧 등록 / 코드 기여 → `CONTRIBUTING.md`
- 도구 전체 목록 → `README.md`
