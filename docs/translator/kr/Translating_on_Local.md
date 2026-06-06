# 로컬 환경에서의 번역 (인게임 테스트 포함)

> NOTE: In-Game Testing을 동시에 수행하려는 목적이 아니라면
> Crowdin 웹페이지에서 번역하는 것을 권장합니다. ([Translating_using_crowdin.md](Translating_using_crowdin.md) 참고)

> **번역 데이터의 source of truth는 Crowdin입니다.**
> 번역 수정에 대한 PR(Pull Request)는 일반적으로 받지 않습니다.

[Translating_using_crowdin.md](Translating_using_crowdin.md)의 **확장 워크플로**입니다. Crowdin 웹만 쓰는 대신:

- 저장소를 클론하여 **인게임에서 직접 결과 확인**하면서 번역할 수 있습니다.
- 대량 수정 / 여러 행 한 번에 변경 시 xlsx로 작업 후 `push_to_crowdin`으로 일괄 반영합니다.
- 빌드 / 검증 로그를 직접 보고 누락·길이 초과 같은 문제를 미리 잡을 수 있습니다.

---

## 1. 사전 준비

1. **[Setting_Environments.md](../../developer/kr/Setting_Environments.md)** 완료
   - Python 3.10+ / Git / Excel / Fork & Clone
   - `pip install -r tools/requirements.txt`
   - `secrets.json` 생성 + Crowdin Personal Token 입력 (DeepL 토큰은 선택)
   - **gdre_tools 설치 (선택, 권장)** — `.pck`에서 게임 소스를 추출해 빌드 검증의 *method 매칭* 단계까지 활성화합니다. 미설치여도 빌드는 동작하며 해당 검증만 자동 스킵됩니다.
2. **Crowdin 프로젝트 가입** (자세히는 [Translating_using_crowdin.md §1-2](Translating_using_crowdin.md))
3. **첫 빌드 통과 확인**: `python tools/build_mod_package.py`

---

## 2. Work-Flow

```
[0. Unpack] gdre_tools로 .pck 추출 → python tools/parse_translatables.py
                ↓                              (선택사항, 게임 업데이트 시 / 첫 Setup 시 1회 수행)
            parsed_text/                       (모드 빌드 시, 매칭 검증에 사용)

[1. Sync ]  git fetch upstream && git pull          (메인테이너의 최신 sync 받기)
                ↓
[2. xlsx ]  python tools/rebuild_xlsx.py <locale>   (canonical TSV → xlsx 재생성, 필수)
                ↓ (선택) Excel에서 편집
[3. Build]  python tools/build_mod_package.py
                ↓
            mods/Trans To Vostok.zip                (게임에서 ModLoader가 로드)
                ↓
[4. Test ]  인게임에서 실제 표시 확인
                ↓ 편집한 경우
[5. Push ]  python tools/push_to_crowdin.py <locale>
```

**Crowdin → 저장소 sync는 개발자/Maintainer가 관리합니다**.

---

## 3. 최신 번역 받아오기

### 3-1. git pull로 번역 데이터 최신화

```powershell
git fetch upstream
git checkout master           # 또는 작업 브랜치
git merge upstream/master     # 메인테이너의 최신 sync 반영
```

### 3-2. 엑셀 파일(.xlsx) Re-Build (필수))

```powershell
python tools/rebuild_xlsx.py Korean
```
로컬 환경에서의 번역 편집, 모드 빌드 파이프라인은 엑셀(.xlsx) 파일을 기준으로 하지만,
Github에서의 번역 데이터베이스는 TSV 포맷으로 저장/관리됩니다. (Translations/`<locale>/tsv/<category>/`)
xlsx를 rebuild (tsv -> xlsx)하지 않으면, 번역이 적용되지 않으므로 반드시 수행되어야 합니다.
xlsx포맷은 불특정 다수가 편집할 경우, 잠재적 보안 위험이 있으므로 별도로 제공되지 않습니다.

---

## 4. 로컬 빌드 + 인게임 테스트

### 4-1. 빌드

```powershell
python tools/build_mod_package.py             # locale.json의 활성 locale 전부
python tools/build_mod_package.py Korean      # Korean만 (디버그/회귀)
```

성공 시 `mods/Trans To Vostok.zip`이 갱신됩니다. 빌드 검증에서 잡히는 항목 예시:

- 같은 키에 다른 번역 (duplicate)
- whitespace 불일치 (앞뒤 공백 / 줄바꿈 mismatch)
- placeholder 누락 (예: `{0}`이 빠진 번역)
- method 매칭 누락 (parsed_text 있을 때만)

### 4-2. 게임 실행 후 표시 확인

1. **Road to Vostok** 실행
2. ModLoader가 `Trans To Vostok.zip` 로드되는지 확인
3. 게임 내 언어 설정에서 본인 locale 선택
4. **번역한 부분을 실제로 방문**:
   - 메뉴 / 인벤토리 / Trader UI / Tutorial 등
   - 텍스트 잘림·박스 초과 여부
   - 다른 언어/영어가 섞여 보이는지 (= 미매칭 행 있음)
   - 컨텍스트상 어색한 의역
5. 수정사항을 발견하면 §5 흐름으로 처리합니다.

> 모드 변경이 게임에 반영되지 않으면 ModLoader 재로드(게임 재시작 또는 핫 리로드)가 필요할 수 있습니다.

---

## 5. 번역 수정
xlsx 파일을 편집 후, 아래 명령어를 실행해주세요. Crowdin에 자동으로 반영됩니다 (Suggestion).
```powershell
# Translations/<locale>/Translation.xlsx 편집 후
python tools/push_to_crowdin.py Korean
```

게임에 표시되는 텍스트가 xlsx에 없으면 새 행을 추가할 수 있습니다. 자세한 방법은 [Translation_Methods.md](../../developer/kr/Translation_Methods.md)를 참조하세요.

Translation validation, exact matching 등에 의해 편집 방법이 조금 복잡할 수 있으므로,
번역 대상 텍스트 누락에 대해서는 가급적 GitHub에 Issue를 등록해 주시는 것을 권장드립니다.

---

## 6. Credit 등록

크레딧 데이터의 출처는 두 갈래로 분리되어 있습니다.

| 항목                                | 출처                                                               | 자동 반영 시점                                  |
| ----------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------- |
| **번역가 (Translator)**       | Crowdin 프로필 이름 (Leader / Translator / Contributor)            | `pull_from_crowdin` 시 자동 (메인테이너 sync) |
| **텍스처 (Texture_reworker)** | `Texture.xlsx`의 각 시트 `Reworked by` / `Contributors` 컬럼 | 빌드 시 `get_texture_credits.py`가 자동 추출  |

번역가는 별도로 본인 이름을 등록할 필요가 없습니다 — Crowdin에 가입할 때 설정한 프로필 이름이 그대로 표시되니, 크레딧에 쓸 이름으로 Crowdin 프로필을 설정해 두십시오.

텍스처 작업자는 `Texture.xlsx`의 해당 시트/행에 본인 이름을 기재하면 됩니다. (셀 내 줄바꿈은 `Alt+Enter`).

빌드 시 두 출처가 합쳐져 다음 파일에 반영됩니다.

- `Trans To Vostok/<locale>/credits.json` (게임 zip 포함, F9 Info 탭에서 표시)
- `Trans To Vostok/<locale>/Translation_Credit.md`
- 프로젝트 루트 `AUTHORS.md`

> `AUTHORS.md` / `credits.json` / `Translation_Credit.md`는 직접 편집할 수 없습니다. (자동 생성 과정에서 Overwite됩니다.)

---

## 7. 자주 겪는 케이스

### 7-1. Pull 했더니 방금 작업한 행이 사라진 경우

다른 contributor가 같은 행을 Crowdin에서 수정한 뒤 메인테이너가 sync한 상황입니다. `git diff`로 비교한 뒤 본인 의도가 더 적절하면 Crowdin 웹에서 다시 수정합니다 (덮어쓰기 충돌 회피).

### 7-2. push했는데 Crowdin에 반영되지 않는 경우

가장 흔한 원인은 다음과 같습니다.

- **번역 == 원문**: Crowdin이 "원문과 동일한 번역"을 자동으로 거절합니다 (UI 라벨 / 고유명사 등). 의도적으로 동일하게 두려면 Crowdin 웹에서 직접 입력합니다.
- **method=ignore / untranslatable=1**: push 대상에서 제외됩니다 (의도된 동작).

### 7-3. 빌드 시 whitespace WARNING

원문이 `"\nReload [R]"`인데 번역이 `"재장전 [R]"`처럼 앞 줄바꿈이 빠진 경우입니다. 원문의 앞뒤 공백·줄바꿈을 그대로 보존해야 합니다. Excel 셀 내 줄바꿈은 `Alt+Enter`로 입력합니다.

### 7-4. method=pattern 행은 어떻게 처리합니까?

`In {str} Days` 같은 pattern 행은 자동 시드(DeepL)가 적용되지 않습니다. 빌드 시 translation이 비어 있으면 substr로 폴백되어 부분 번역(예: `In 5 Days` → `In 5 일`)이 발생할 수 있습니다. 의도적으로 영문을 그대로 두려면 **translation = text**로 동일하게 입력합니다.

---

## 8. 다음 단계

- **Pull Request 흐름** (코드/도구 변경) → [Setting_Environments.md §7](../../developer/kr/Setting_Environments.md#7-일반-작업-흐름)
- **새 언어 추가 / DeepL 시드** → [Add_new_language.md](../../admin/kr/Add_new_language.md)
- **method 자세히** → [Translation_Methods.md](../../developer/kr/Translation_Methods.md)
