# 1. 게임 PCK 추출 & 디컴파일 (한국어)

전체 validation (TSV match / tres text / gd text)을 활성화하기 위한 선택적 셋업 가이드입니다.
번역만 작업하는 기여자는 이 단계를 건너뛰어도 빌드/PR 흐름에 지장 없습니다.

> **⚠️ 법적 주의 — 반드시 읽어주세요**
>
> - 이 절차는 **본인이 합법적으로 소유한 Road to Vostok 카피**에 대해서만 수행해야 합니다.
> - 게임에서 추출된 (`.gd` / `.tscn` / `.tres` 등)는 RTV 게임 개발사의 저작물입니다.
>   **외부 공유 / 재배포 / 커밋** 등의 행위는 금지됩니다.
> - 본 저장소의 `.gitignore`는 `.tmp/`, `tools/3rd_party/` 를 제외하므로 정상 작업 시 추출물이 저장소에 들어가지 않습니다. 실수로 커밋하지 않도록 `git status` 확인을 권장합니다.

---

## 1. 사전 준비

[0_Setting_Environments_kr.md](0_Setting_Environments_kr.md) 의 셋업이 끝났다고 가정합니다.

추가로 필요한 것:

- **gdre_tools** (Godot RE Tools) — Godot `.pck` 디컴파일 도구
  - 다운로드: [https://github.com/bruvzg/gdsdecomp/releases](https://github.com/bruvzg/gdsdecomp/releases)
  - Windows용 `.zip` 다운로드 후 압축 해제
  - `gdre_tools.exe` 를 `tools/3rd_party/gdre_tools/gdre_tools.exe` 위치에 배치
  - (선택) 같이 들어있는 `GodotMonoDecompNativeAOT.dll` 등 부속 파일도 같은 폴더에 복사

폴더 구조 예시:

```
Trans To Vostok/
└── tools/
    └── 3rd_party/
        └── gdre_tools/
            ├── gdre_tools.exe
            ├── gdre_tools.pck
            └── ... (기타 부속 파일)
```

> `tools/3rd_party/.gitignore`가 안의 모든 파일을 제외하므로 실수로 gdre_tools 바이너리가 커밋될 일은 없음.

---

## 2. RTV PCK 파일 위치 확인

Road to Vostok의 메인 패키지 파일:

```
{Game Directory}/Road to Vostok.pck
```

경로 예시:

- C 드라이브: `C:\Program Files (x86)\Steam\steamapps\common\Road to Vostok\Road to Vostok.pck`
- D 드라이브: `D:\SteamLibrary\steamapps\common\Road to Vostok\Road to Vostok.pck`

게임 버전이 업데이트되면 이 파일도 갱신됨 → 매 업데이트마다 재추출 필요.

---

## 3. gdre_tools로 PCK 추출

PowerShell에서:

```powershell
cd "C:\Program Files (x86)\Steam\steamapps\common\Road to Vostok\mods/Trans To Vostok"
# 또는 cd "D:/SteamLibrary/steamapps/common/Road to Vostok/mods/Trans To Vostok"
$pck = "../../Road to Vostok.pck"
& "tools/3rd_party/gdre_tools/gdre_tools.exe" --headless --recover="$pck" --output-dir=".tmp/pck_recovered"
```

옵션 상세는 `gdre_tools.exe --help` 참조.

---

## 4. 텍스트 파싱 → parsed_text/ 생성

추출된 `.gd` / `.tscn` / `.tres` 에서 번역 가능한 문자열을 뽑아 TSV로 변환:

```powershell
python tools/parse_translatables.py
```

이 명령은 내부적으로 3개의 파서를 순차 실행:

1. `parse_tscn_text.py` — 씬 파일의 Label / Button / RichTextLabel text 추출
2. `parse_tres_text.py` — 리소스 파일의 텍스트 필드 추출
3. `parse_gd_text.py` — GDScript의 UI 문자열 추출

기본 입력: `.tmp/pck_recovered/`
기본 출력: `.tmp/parsed_text/`

출력 예시:

```
.tmp/parsed_text/
├── Scripts/
│   └── Player/
│       └── Player.gd.tsv
├── UI/
│   └── HUD.tscn.tsv
└── ... 기타
```

---

## 5. 동작 확인 — Full Validation

`parsed_text/`가 준비됐다면 build_mod_package.py가 자동으로 전체 validation 수행:

```powershell
python tools/build_mod_package.py Korean
```

콘솔에 `[1/5] Validating... (Korean, hard)` 메시지가 보이면 full mode.
`[1/5] Validating (partial: parsed_text not found)... (Korean, hard)` 가 보이면 parsed_text 부재 → 위 단계가 누락됨.

추가로 검증만 단독 실행할 수 있음:

```powershell
python tools/validate_translation.py Korean
```

검사 결과 로그: `Trans To Vostok/Korean/.log/validate_translation_<timestamp>.log`

---

## 6. 게임 업데이트 시 재추출 흐름

RTV 게임이 업데이트되면 `.pck`가 갱신됨 → 다음 절차 반복:

```powershell
# 1. 기존 추출/파싱 결과 정리 (선택)
Remove-Item -Recurse -Force .tmp/pck_recovered, .tmp/parsed_text

# 2. PCK 재추출 (GUI 또는 CLI)
& "tools/3rd_party/gdre_tools/gdre_tools.exe" --headless --recover="<pck>" --output-dir=".tmp/pck_recovered"

# 3. 파싱
python tools/parse_translatables.py

# 4. 변경된 게임 텍스트와 기존 번역 비교
python tools/check_old_translation.py Korean
```

`check_old_translation.py`는 게임 업데이트로 사라진 번역 (구식 `unique_id`)을 표시해줌.

---

## 7. 다음 단계

- 일반 작업 흐름 → [0_Setting_Environments_kr.md](0_Setting_Environments_kr.md) 6장
- 번역 작업 / 크레딧 → `CONTRIBUTING.md`
- 도구 전체 목록 → `README.md`
