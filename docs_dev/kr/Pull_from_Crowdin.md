# Crowdin → 저장소 Sync (개발자/메인테이너 가이드)

Crowdin에 누적된 번역 활동을 정기적으로 저장소에 반영해, 다른 contributor가 `git pull`로 최신 번역을 받아 빌드·테스트할 수 있도록 하는 워크플로입니다.

> **이 가이드의 대상**: Crowdin 프로젝트의 Owner / Manager 권한과 저장소 write 권한을 모두 가진 Maintainer입니다.
> 일반 번역가는 이 작업을 직접 수행하지 않습니다.

---

## 1. 사전 준비

1. **[Setting_Environments.md](../../docs/kr/Setting_Environments.md)** 완료 (Python / Git / pip 의존성)
2. **`secrets.json`의 `crowdin_personal_token`** 설정 — 다음 scope들이 활성화돼 있어야 합니다.
   - **Projects** (Read & Write)
   - **Source Files**
   - **Translations**
   - **Glossary** (Read & Write)
3. **Crowdin 프로젝트 권한** — 본인 계정이 프로젝트의 Owner / Manager 또는 Language Coordinator로 등록돼 있어야 sync가 가능합니다.
4. **저장소 write 권한** — sync 결과를 commit / push 하려면 본 저장소(또는 fork)에 push 가능해야 합니다.

---

## 2. Workflow

```
[1. Pull]   python tools/pull_from_crowdin.py {locale | all}
                ↓
            Crowdin                                  (서버 측 build + zip 생성)
                ↓
            Crowdin_Mirror/translations/<locale>/    (zip 추출, gitignored)
                ↓
            Translations/<locale>/<category>/*.tsv   (canonical TSV, committed)
                ↓
            Trans To Vostok/<locale>/credits.json    (Translator + translation_updated)
                ↓
[2. Review] git diff Translations/  Trans To Vostok/*/credits.json
                ↓ 의도된 변경만 stage
[3. Commit] git add Translations/ Trans To Vostok/*/credits.json
            git commit -m "Pull translations from Crowdin"
                ↓
[4. Push ]  git push   (다른 contributor가 git pull로 받을 수 있게)
```

**권장 빈도**: 주 1회, 또는 주요 번역 완료 직후 / 모드 빌드/배포 직전.

---

## 3. `pull_from_crowdin` 실행

### 3-1. 기본 사용

```powershell
python tools/pull_from_crowdin.py Korean       # 단일 locale
python tools/pull_from_crowdin.py all          # 활성 locale 전부 (시간 더 걸림)
```

`all` 또는 명시적 locale은 **필수**입니다 — 빈 인자 호출은 의도치 않은 대량 sync를 방지하기 위해 거부됩니다.

### 3-2. 내부 단계

스크립트는 다음 3단계를 순차 실행합니다.

1. **Crowdin SDK download** ([api_client.py: download_translations](../../tools/crowdin/api_client.py))

   - Crowdin 서버에 build 요청 → 완료 polling → zip 다운로드 → 압축 해제
   - 추출 경로: `Crowdin_Mirror/translations/<locale>/<category>/*.tsv`
   - zip 내부의 BCP-47 locale 코드(예: `ko-KR`)는 `languages.json` 매핑에 따라 친절한 폴더명(예: `Korean`)으로 자동 변환됩니다.
2. **apply_to_repo.py** — Crowdin_Mirror → canonical TSV

   - `Translations/<locale>/<category>/*.tsv`의 `translation` 컬럼을 갱신
   - **Crowdin이 빈 값으로 보낸 행은 로컬 값을 보존합니다** (실수로 wipe되지 않도록 하는 보호 장치)
   - identifier 매칭은 각 카테고리의 `make_*_id()` 함수로 수행
3. **get_member_list.py** — Crowdin → credits.json

   - Crowdin 멤버 목록 + Top Members Report 조회
   - role 분류: Owner/Manager/Language Coordinator → `Leader`, Proofreader → `Translator`, 활동 있는 Member → `Contributor`
   - `translation_updated`는 해당 locale의 가장 최근 번역 활동 시점(createdAt / updatedAt 중 max)
   - `Texture_reworker` 필드는 손대지 않음 (`get_texture_credits.py`가 별도 관리)

### 3-3. 옵션 플래그

```powershell
python tools/pull_from_crowdin.py Korean --skip-download
```

`--skip-download`: 1단계(Crowdin → Crowdin_Mirror)를 건너뛰고 기존 Mirror 상태로 2~3단계만 실행. 디버깅이나 재처리 용도.

---

## 4. 결과 검토

### 4-1. canonical TSV 변경분

```powershell
git diff Translations/
```

행 단위로 어떤 번역이 추가 / 변경됐는지 확인합니다. 의도치 않은 대규모 변경(예: 한 locale 전체가 비워짐)이 보이면 commit 하지 말고 원인 조사:

- Crowdin 측에서 사용자가 실수로 일괄 삭제했을 가능성
- locale 매핑 오류 (예: zip 추출 시 `ko-KR` 폴더가 변환 안 된 경우)

### 4-2. credits.json 변경분

```powershell
git diff "Trans To Vostok/"*/credits.json
```

다음을 확인합니다.

- `translation_updated` 시점이 합리적으로 진행됐는지
- 새 contributor가 Translator/Contributor 리스트에 잡혔는지
- 기존 Leader가 누락되지 않았는지 (만약 그렇다면 Crowdin 권한 변경 가능성)

### 4-3. xlsx 미반영 확인

`Translation.xlsx`는 gitignored이므로 sync로 갱신되지 않습니다. 본인의 로컬 xlsx를 새로운 canonical TSV에 맞추고 싶다면:

```powershell
python tools/rebuild_xlsx.py Korean
```

(메인테이너가 직접 번역하지 않는 경우엔 생략 가능 — 다른 contributor들이 `git pull` 후 자기 환경에서 rebuild_xlsx 합니다.)

---

## 5. 커밋 + Push

검토에서 이상 없으면 변경분을 커밋합니다.

```powershell
git add Translations/ "Trans To Vostok/"*/credits.json
git commit -m "Pull translations from Crowdin"
git push
```

> `Trans To Vostok/<locale>/runtime_tsv/` 등 빌드 산출물은 같이 commit 할 필요 없습니다 — 다른 contributor가 빌드할 때 자동 생성됩니다.

다른 contributor에게는 다음을 안내합니다.

1. `git fetch && git pull`
2. `python tools/rebuild_xlsx.py <locale>` (필수 — 자세히는 [Translating_on_Local.md §3-2](../../docs/kr/Translating_on_Local.md#3-2-엑셀-파일xlsx-re-build-필수))
3. `python tools/build_mod_package.py`로 zip 갱신 후 인게임 테스트

---

## 6. 자주 겪는 케이스

### 6-1. `Crowdin token not found` 에러

`secrets.json`에 `crowdin_personal_token`이 비어 있거나 파일 자체가 없는 경우입니다. `secrets_example.json`을 복사해 토큰을 채우거나, `CROWDIN_PERSONAL_TOKEN` 환경변수를 설정합니다.

### 6-2. `403 Endpoint isn't allowed for token scopes`

토큰 발급 시 누락된 scope가 있습니다. Crowdin → Account Settings → API & SSO → 해당 토큰의 scope에 §1-2의 4개를 모두 포함시켜 재발급합니다.

### 6-3. `Crowdin build {failed|canceled|timed out}`

서버 측 빌드가 실패한 경우입니다. Crowdin 웹 UI에서 직접 빌드를 한번 돌려 보고 (Project → Build & Download → Build), 정상 빌드가 가능해진 뒤 다시 시도합니다. 일시적 서버 이슈면 잠시 후 재시도로 해결됩니다.

### 6-4. canonical TSV에서 모든 행이 빈 값으로 변경됨

**Crowdin 측에서 실제로 비어 있어** 그대로 받아온 게 아니라, locale 매핑 / zip 추출 단계에서 잘못된 폴더에 풀린 경우가 더 흔합니다. `Crowdin_Mirror/translations/` 디렉터리의 폴더명을 확인하세요 — `Korean / French / Portuguese_BR`만 있어야 하고 `ko-KR / fr-FR / pt-BR` 같은 BCP-47 폴더가 잔재로 있으면 매핑 실패. `git checkout` 으로 변경 되돌리고 원인 조사 후 재시도.

### 6-5. 특정 contributor가 credits.json에 안 잡힘

다음을 확인합니다.

- 해당 사용자의 Crowdin 활동이 0인지 (Top Members Report에서 `translated > 0`이어야 Contributor로 잡힘)
- 사용자가 본인 언어에 대한 권한을 가지고 있는지 (없으면 list_project_members 결과에서 누락)
- 사용자의 fullName이 비어 있는 경우 username으로 표시됨 — 본인이 Crowdin 프로필에 표시 이름을 설정하도록 안내

### 6-6. Sync 후 다른 contributor의 push와 충돌

본 sync 시점과 다른 메인테이너의 sync가 시간상 가까이 발생한 경우입니다. `git pull --rebase` 후 충돌 해결, 다시 push.

---

## 7. 다음 단계

- **Push (xlsx → Crowdin)**: 메인테이너 본인이 번역도 직접 한다면 `tools/push_to_crowdin.py` 흐름 참조 (별도 문서 예정)
- **새 언어 추가 / DeepL 자동 시드**: 별도 문서 예정
- **Crowdin Glossary 관리**: 별도 문서 예정
- **빌드 & 배포**: `tools/build_mod_package.py` (활성 locale 전체 zip 빌드)
