# 5. Master(main) 브랜치 업데이트 동기화 (한국어)

작업 중간에 본 저장소의 `main` 브랜치가 갱신됐을 때, 내 작업 브랜치를 어떻게 동기화할지 다룹니다.

> 본 저장소의 기본 브랜치 이름은 `main` 입니다 ("master"가 아님). 문서 제목은 일반적인 표현을 따랐고, 본문에서는 `main`을 사용합니다.

---

## 1. 왜 동기화가 필요한가

작업 시작 후 시간이 흐르면 upstream `main`이 다른 기여자의 PR로 갱신되는데, 내 작업 브랜치는 갈라진 시점에 머물러 있습니다.

이 상태로 계속 작업 → PR 생성 시 충돌 다발 가능. 작업 진행 중에 주기적으로 동기화하면 충돌이 작은 단위로 분산됨 (작업 끝나고 한꺼번에 해결하는 것보다 쉬움).

권장 시점:
- 작업 시작 직전 (Step 1)
- 작업이 며칠 이상 걸리면 매일 / 매번 작업 시작 시
- PR 보내기 직전 (마지막 정리)

---

## 2. 정책: 한 브랜치 = 한 사람 → **rebase 사용**

이 프로젝트는 "한 브랜치는 한 기여자만 push" 정책 ([4_How_to_Pull_Request_kr.md](4_How_to_Pull_Request_kr.md) §2 참조). 그래서 **rebase 가 안전하고 권장**됩니다:

- ✅ Linear history (PR diff 깔끔, 리뷰 추적 쉬움)
- ✅ Force push 충돌 위험 없음 (혼자 쓰는 브랜치)
- ✅ Merge commit으로 인한 잡음 없음

> **Merge 가 더 적절한 케이스**: 둘 이상의 기여자가 같은 브랜치에 push 중이라면 (이 프로젝트에선 드묾) merge로 가야 함. 이 가이드는 rebase 기준으로 작성.

---

## 3. 동기화 절차 (rebase)

### 3-1. upstream 최신 가져오기

```powershell
git fetch upstream
```

> upstream이 등록 안 됐으면 [0_Setting_Environments_kr.md](0_Setting_Environments_kr.md) §3-3 참조.

### 3-2. 내 main 갱신 (선택, 좋은 습관)

```powershell
git checkout main
git merge upstream/main      # 빠른 fast-forward (충돌 없음)
git push origin main         # fork의 main도 갱신
```

내 fork의 main을 항상 upstream과 같게 유지 → 새 브랜치 만들 때 출발점이 항상 최신.

### 3-3. 작업 브랜치를 upstream/main 위로 rebase

```powershell
git checkout <my-branch>
git rebase upstream/main
```

충돌 없으면 끝. push:

```powershell
git push --force-with-lease origin <my-branch>
```

> `--force-with-lease` 는 일반 `--force` 보다 안전 — 원격에 내가 모르는 변경이 있으면 거부. 혼자 쓰는 브랜치라도 습관적으로 사용 권장.

---

## 4. 충돌 해결

rebase 도중 충돌이 나면 git이 멈추고 충돌 파일을 표시합니다.

```powershell
git status            # 충돌 파일 목록 확인
```

### 4-1. 텍스트 파일 (.gd / .py / .md / TSV / json)

표준 git 충돌 마커 (`<<<<<<<`, `=======`, `>>>>>>>`) 가 파일 안에 들어감. 에디터에서 열어 원하는 결과로 편집 → 마커 제거 → 저장 → stage:

```powershell
git add <resolved-file>
git rebase --continue
```

VS Code는 충돌 마커에 대한 GUI 가이드 제공 (Accept Current / Incoming / Both).

### 4-2. xlsx (binary)

xlsx는 binary라 git이 줄 단위 merge를 못 함 → "both modified" 상태로만 표시되고 자동 머지 안 됨.

선택지:

**옵션 A — Translation_TSV 기반으로 재구축 (권장)**
1. 현재 작업 (`HEAD`) 의 xlsx로 갈지, upstream의 xlsx로 갈지 결정
2. 예시: 내 변경 + upstream 변경 모두 반영하려면:
   ```powershell
   # 일단 upstream 버전으로 받음 (xlsx)
   git checkout --theirs "Trans To Vostok/<locale>/Translation.xlsx"

   # TSV는 양쪽 변경을 합쳐 반영
   # → TSV는 텍스트 충돌 마커가 떴을 거니 4-1 절차로 해결
   git add "Translation_TSV/<locale>/"

   # 내 변경을 다시 적용하려면 TSV → xlsx 재빌드 (현재 정책 적용)
   python tools/rebuild_xlsx.py <locale>

   # xlsx도 stage
   git add "Trans To Vostok/<locale>/Translation.xlsx"
   git rebase --continue
   ```

**옵션 B — 한쪽 버전 채택**
```powershell
# 내 버전 (HEAD) 유지
git checkout --ours "Trans To Vostok/<locale>/Translation.xlsx"

# 또는 upstream 버전 채택
git checkout --theirs "Trans To Vostok/<locale>/Translation.xlsx"

git add "Trans To Vostok/<locale>/Translation.xlsx"
git rebase --continue
```
주의: 한쪽만 채택하면 다른 쪽의 변경이 사라짐. 이걸 원하지 않으면 옵션 A.

### 4-3. rebase 중단하고 처음 상태로

상황이 꼬였거나 다시 시도하고 싶으면:

```powershell
git rebase --abort
```

rebase 시작 전 상태로 완전 복구.

---

## 5. PR 보내기 직전 마지막 동기화

PR 직전에 한 번 더 rebase하면 머지 시점에 충돌이 거의 없음:

```powershell
git fetch upstream
git rebase upstream/main
# 충돌 발생 시 §4 절차

python tools/build_mod_package.py <locale>      # 빌드 검증
git push --force-with-lease origin <my-branch>
```

이미 PR이 열려있는 상태에서 force push 하면 PR이 자동으로 갱신됨 (리뷰 코멘트는 보존).

---

## 6. 트러블슈팅

| 증상 | 원인 / 해결 |
| --- | --- |
| `git push` 가 거부됨 (rejected, non-fast-forward) | rebase로 history가 바뀌었음 → `git push --force-with-lease origin <branch>` |
| `--force-with-lease` 도 거부됨 | 원격에 내가 모르는 commit이 있음 (다른 컴퓨터에서 push했거나). `git fetch && git log origin/<branch>` 확인 후 안전 판단 |
| rebase 시 같은 충돌이 commit마다 반복 | `git rebase -i` 로 commit squash 후 rebase 하거나, 충돌 한 번 해결 후 `git rerere` 활용 검토 |
| xlsx 충돌 후 빌드 실패 | TSV / xlsx 동기화가 깨졌을 가능성 — `python tools/rebuild_xlsx.py <locale>` 로 TSV → xlsx 재생성 |
| rebase 끝났는데 작업 commit이 사라진 것 같음 | `git reflog` 로 이전 HEAD 확인 → `git reset --hard HEAD@{N}` 으로 복구 (Step 4-3 abort보다 광범위 복구) |

---

## 7. 다음 단계

- 셋업 / 일반 흐름 → [0_Setting_Environments_kr.md](0_Setting_Environments_kr.md)
- PR 생성 / 머지 후 정리 → [4_How_to_Pull_Request_kr.md](4_How_to_Pull_Request_kr.md)
- xlsx ↔ TSV 재빌드 도구 → `tools/rebuild_xlsx.py`
