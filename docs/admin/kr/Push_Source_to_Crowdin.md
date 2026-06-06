# Crowdin 소스 파일 Push (개발자/메인테이너 가이드)

Template TSV를 Crowdin에 소스 파일로 업로드해, 새 번역 대상 항목이 Crowdin 편집기에 표시되도록 하는 워크플로입니다.

> **이 가이드의 대상**: Crowdin 프로젝트의 Owner / Manager 권한과 저장소 write 권한을 모두 가진 Maintainer입니다.
> 소스 파일을 잘못 업로드하면 **모든 언어의 번역 항목에 영향**을 미칩니다. 일반 번역가는 이 작업을 수행하지 않습니다.

---

## 1. 언제 실행하나

다음 경우에만 실행합니다.

| 상황 | 필요 여부 |
| ---- | --------- |
| Template에 새 sheet / category 추가 | **필요** |
| 기존 source string의 `text` 변경 | **필요** |
| `translation` 컬럼만 변경 (번역 push) | **불필요** — `push_to_crowdin.py <locale>` 사용 |
| `identifier` 변경 없이 row 추가 | **필요** |
| 메타데이터만 변경 (WHERE / SUB / KIND 등) | 불필요 (Crowdin이 읽지 않음) |

번역 업로드 (`push_to_crowdin.py <locale>`) 와 소스 업로드는 별개입니다 — 혼동하지 마십시오.

---

## 2. 사전 준비

1. **[Setting_Environments.md](../../translator/kr/Setting_Environments.md)** 완료 (Python / Git / pip 의존성)
2. **`secrets.json`의 `crowdin_personal_token`** 설정 — 다음 scope가 활성화돼 있어야 합니다.
   - **Source Files**
   - **Storage**
3. **Crowdin 프로젝트 권한** — 소스 파일 수정 권한은 Owner / Manager만 가능합니다.
4. **Template TSV 최신화** — 업로드 전에 Template canonical TSV가 최신 상태인지 확인합니다.

   ```powershell
   python tools/rebuild_xlsx.py Template   # (선택) TSV가 이미 최신이면 생략 가능
   ```

---

## 3. Workflow

```
[1. Build]   tools/crowdin/build_source.py
                 ↓
             Translations/Template/tsv/<category>/*.tsv
                 ↓
             Crowdin_Mirror/source/<category>/<sheet>.tsv   (gitignored)

[2. Upload]  Crowdin SDK upload
                 ↓
             Missing file  → add  (새 항목이 Crowdin 편집기에 표시)
             Existing file → update (기존 identifier 번역은 유지)
             Missing dir   → auto-create
```

**기존 번역 보존**: `identifier`가 바뀌지 않은 행의 번역은 덮어쓰지 않습니다.
**삭제 없음**: Template에서 제거된 파일은 Crowdin에서 삭제되지 않고 숨김 처리됩니다 (수동 정리 필요).

---

## 4. 실행

### 4-1. 기본 실행 (권장)

```powershell
python tools/push_to_crowdin.py Template
```

관리자 전용 작업임을 알리는 경고와 확인 프롬프트가 표시됩니다.

```
[!] Pushing SOURCE FILES to Crowdin — maintainer-only operation.
    This updates source strings for ALL translators on Crowdin.
    Incorrect use may disrupt active translations.
    Proceed? [y/N]
```

`y` 를 입력하면 `tools/crowdin/push_source_to_crowdin.py` 가 실행됩니다.

### 4-2. 직접 실행

```powershell
python tools/crowdin/push_source_to_crowdin.py
```

확인 프롬프트 없이 바로 실행됩니다. 스크립트 자동화 등에 사용합니다.

### 4-3. 옵션 플래그

| 플래그 | 의미 |
| ------ | ---- |
| `--skip-mirror` | 1단계(build_source.py)를 건너뛰고 기존 `Crowdin_Mirror/source/` 그대로 업로드 |

```powershell
# build_source.py 를 이미 수동으로 실행했거나, Mirror가 최신 상태임이 확실할 때
python tools/push_to_crowdin.py Template --skip-mirror
```

---

## 5. 결과 확인

업로드 완료 후 출력 예시:

```
=== Summary ===
  Added   : 3
  Updated : 12
  Errors  : 0
```

Crowdin 웹 UI에서 직접 확인합니다.

- **Project → Files** — 새 파일이 추가됐는지 확인
- **Project → Overview** — 새 항목이 "Untranslated" 카운트에 잡혔는지 확인
- 기존 번역자들이 편집기를 열면 새 항목이 표시되어야 합니다

---

## 6. 이후 작업

소스 push 이후 번역자들이 새 항목을 Crowdin에서 번역하면, 정기 pull 워크플로로 저장소에 반영합니다.

- **Crowdin 번역 반영** → [Pull_from_Crowdin.md](Pull_from_Crowdin.md)
- **새 언어 전체 시드 (DeepL)** → [Add_new_language.md](Add_new_language.md)

---

## 7. 자주 겪는 케이스

### 7-1. `Source Files scope 누락`

```
403 Endpoint isn't allowed for token scopes
```

Crowdin → Account Settings → API & SSO → 해당 토큰에 **Source Files** + **Storage** scope를 추가 후 재발급합니다.

### 7-2. `Crowdin_Mirror/source/ missing`

`--skip-mirror` 를 사용했는데 Mirror가 없는 경우입니다. `--skip-mirror` 없이 다시 실행합니다.

### 7-3. 업로드 후 기존 번역이 사라짐

`identifier`가 변경된 경우입니다 (예: `unique_id` 재발급, sheet rename). Crowdin은 identifier 기준으로 번역을 매핑하므로, identifier가 바뀌면 기존 번역과의 연결이 끊깁니다.

- identifier 변경 전 Crowdin에서 기존 번역을 export / 백업합니다.
- 부득이하게 identifier를 변경해야 한다면 Crowdin 웹 UI에서 수동으로 번역을 옮기거나, TM(Translation Memory)에서 복구합니다.

### 7-4. `Errors : N` 출력

업로드 실패한 파일 목록이 함께 출력됩니다. 네트워크 오류라면 재시도로 해결됩니다. 파일 형식 오류(헤더 누락 등)라면 `build_source.py` 출력을 먼저 확인합니다.
