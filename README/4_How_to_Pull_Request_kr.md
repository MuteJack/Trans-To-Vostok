# 4. Pull Request 가이드 (한국어)

작업한 결과를 본 저장소에 제출 (Pull Request) 하는 흐름입니다. 0~3번 가이드의 git 부분을 한 곳에 모은 단일 진입점.

---

## 1. 사전 준비

- [0_Setting_Environments_kr.md](0_Setting_Environments_kr.md) 의 셋업 완료 (Fork + Clone + upstream 등록)
- 작업 (번역 / 코드) 이 로컬에 있는 상태

---

## 2. 작업 시작 — 새 브랜치

`main`에 직접 작업하지 말고 작업별 브랜치 생성:

```powershell
# upstream 최신 가져오기
git fetch upstream
git checkout main
git merge upstream/main

# 새 브랜치 생성 (작업 단위별)
git checkout -b <type>/<short-description>
```

브랜치 이름 컨벤션 (권장):

| 작업 종류 | 예시 |
| --- | --- |
| 번역 | `translate/korean-items-fix` |
| 새 언어 추가 | `translate/add-japanese` |
| 텍스처 / 이미지 | `texture/world-map-revision` |
| 코드 | `code/improve-validate-output` |
| 문서 | `docs/contributing-update` |

> 한 브랜치 = 한 PR. 여러 종류의 작업을 한 브랜치에 섞지 말 것 (리뷰가 어려워짐).
>
> **이름 중복 방지**: 다른 기여자가 이미 사용 중인 / 사용했던 브랜치명을 피해주세요. 자기 작업을 식별할 수 있는 단어 (locale, 다루는 시트 / 이슈 번호 / 짧은 핸들 등) 를 포함하면 안전합니다.
>
> - 좋은 예: `translate/korean-items-armor`, `translate/french-tooltips-clarity`, `code/validate-allow-missing-parsed-text`
> - 피할 예: `fix`, `update`, `wip`, `my-branch` (의미 없음 / 충돌 가능성 높음)
>
> 본 저장소의 활성 브랜치는 GitHub의 **Branches** 탭에서 확인 가능. fork 안에서도 본인이 과거에 사용한 브랜치명 재사용은 피하는 게 좋음 (PR 추적 / 리뷰 코멘트 컨텍스트가 섞임).

---

## 3. Commit 메시지 컨벤션

권장 형식:
```
<scope>: <짧은 요약 (영문 또는 한글)>

<선택: 자세한 설명 (왜 변경했는가, 영향 범위 등)>
```

예시:
```
Korean: fix Items SUB consistency (append filename suffix)

- Updated 1570 rows in Items.tsv (Armor → Armor/Armor_Plate_II 등)
- Skipped 41 rows with empty filename
- Reflects parent/child relationship for visual grouping
```

scope 예시:
- `Korean` / `French` / `Template` (locale 기준 작업)
- `tools` (Python 도구 변경)
- `runtime` (translator.gd / translator_ui.gd 변경)
- `docs` (README/가이드 문서)
- `mod-compat` (모드 호환성)

> **xlsx 변경만 있을 때**도 의미있는 메시지를 남기세요. "Update xlsx" 보다는 "Korean: improve Items wording for X-class items" 처럼.

---

## 4. PR에 포함할 것

작업 종류에 따라 commit / staging 대상이 달라짐:

### 번역 작업 (xlsx 편집)
```powershell
git add "Trans To Vostok/<locale>/Translation.xlsx"
git add "Translation_TSV/<locale>/"
```
xlsx + TSV shadow **둘 다** 포함. TSV가 git diff를 가능하게 해서 리뷰가 쉬워짐.

### 새 언어 추가
```powershell
git add "Trans To Vostok/<locale>/"
git add "Translation_TSV/<locale>/"
git add "Trans To Vostok/locale.json"
```

### 텍스처 / 이미지
```powershell
git add "Trans To Vostok/<locale>/textures/"
git add "Trans To Vostok/<locale>/Texture.xlsx"     # attribution 갱신
git add "Trans To Vostok/<locale>/Texture_Attribution.md"  # 빌드로 자동 갱신됨
```

### 코드 변경
```powershell
git add tools/
git add "Trans To Vostok/*.gd"
```

### 빼야 할 것
- `.tmp/` 의 결과물 (gitignored 이지만 혹시 모름)
- `.log/` 의 로그 파일
- `~$*.xlsx` (Excel 락 파일)
- `tools/3rd_party/` 의 gdre_tools 바이너리 등 (gitignored)
- `tools/.deepl_key` (gitignored)

`git status` 로 staged 파일이 의도한 것만인지 확인.

---

## 5. 빌드 검증 → 게임 테스트 → Push

PR 전 마지막 체크:

```powershell
# 1. 빌드 통과 확인
python tools/build_mod_package.py <locale>

# 2. (번역 작업이면) 게임에서 실제 화면 확인
#    [3_How_to_Translate_kr.md](3_How_to_Translate_kr.md) 6-2 참조

# 3. push
git push origin <branch-name>
```

빌드 실패 / 게임 표시 이상 시 PR 전 수정.

---

## 6. PR 생성

GitHub에서 fork → 원본 저장소로 PR 생성. 권장 템플릿:

### 제목
```
[<scope>] 짧은 요약 (70자 이내)
```
예: `[Korean] Items SUB consistency fix (append filename suffix)`

### 설명
```markdown
## 변경 내용
- 변경 1 줄 요약
- 변경 2 줄 요약

## 영향 범위
- locale: Korean / French / Template / All
- 시트: Items, Assets(Furniture)
- 행 수: 변경 1570, 추가 0, 삭제 0

## 검증
- [x] `python tools/build_mod_package.py Korean` 통과
- [x] 게임 내 표시 확인 (메뉴 / Items / Trader)
- [ ] Validation 로그 첨부 (선택)

## 참고 / 컨텍스트
(이 변경의 배경 / 관련 issue / 디자인 결정 이유 등)

## 스크린샷 (선택)
(UI 변경이면 before/after 캡처 권장)
```

### 어떤 정보가 리뷰에 도움이 되나
- **변경 동기** (issue 링크 / 게임 화면 문제 / 일관성 개선 등)
- **검증 결과** (빌드 / 게임 테스트 / Validation 로그)
- **영향 범위** (모든 locale / 하나만 / 코드 / asset)
- **breaking change 여부** (xlsx 컬럼 추가/삭제 등 다른 locale에도 영향 가는 변경)

---

## 7. 리뷰 대응

리뷰어가 코멘트를 남기면:

1. 코멘트 확인 → 로컬에서 수정
2. 같은 브랜치에 추가 commit (force push 지양)
   ```powershell
   git add <changed-files>
   git commit -m "Address review: <what you changed>"
   git push origin <branch-name>
   ```
3. PR이 자동으로 갱신됨
4. 리뷰어에게 "응답 완료" 알림 (코멘트로 ✅ 또는 짧은 메시지)

> 작은 typo 수정이면 force push로 squash해도 무방. 하지만 의미있는 변경은 commit history를 보존하는 게 리뷰 추적에 좋음.

---

## 8. 머지 후 정리

PR이 머지됐다면 로컬 / fork 정리:

```powershell
# upstream 최신 가져오기 (방금 머지된 내 PR 포함)
git checkout main
git fetch upstream
git merge upstream/main

# 머지된 브랜치 삭제 (로컬)
git branch -d <branch-name>

# fork의 원격 브랜치 삭제 (선택)
git push origin --delete <branch-name>

# fork 의 main도 동기화 (push)
git push origin main
```

다음 작업은 `git checkout -b <new-branch>` 부터 다시 시작.

---

## 9. 자주 겪는 이슈

| 증상 | 원인 / 해결 |
| --- | --- |
| PR diff에 xlsx만 있고 TSV 없음 | `Translation_TSV/<locale>/` 도 add. xlsx 단독은 리뷰 불가 |
| PR diff에 의도하지 않은 파일 다수 포함 | `git status` / `.gitignore` 확인. `~$*.xlsx`, `.log/`, `.tmp/` 등 stage 해제 |
| PR을 올렸는데 빌드 검증 실패 표시 | CI 로그 확인 → 로컬에서 `python tools/build_mod_package.py` 재현 → 수정 |
| upstream main이 빠르게 변해서 충돌 | `git fetch upstream && git rebase upstream/main` 또는 `git merge upstream/main` 후 push |
| Excel에 파일 열려있어 push 후 다른 사람이 build 시 conflict | xlsx는 binary라 Git rebase / merge 로 다루기 어려움 — 가능하면 같은 xlsx 동시 작업 회피 |

---

## 10. 다음 단계

- 셋업 → [0_Setting_Environments_kr.md](0_Setting_Environments_kr.md)
- 게임 소스 추출 → [1_unpack_and_decompile_game_kr.md](1_unpack_and_decompile_game_kr.md)
- 새 언어 추가 → [2_Add_new_language_kr.md](2_Add_new_language_kr.md)
- 번역 작업 → [3_How_to_Translate_kr.md](3_How_to_Translate_kr.md)
- 개발자용 매칭 / method 가이드 → [3_How_to_Translate_kr(For Developers).md](3_How_to_Translate_kr%28For%20Developers%29.md)
- 크레딧 / 코드 기여 / 새 언어 DeepL → `CONTRIBUTING.md`
