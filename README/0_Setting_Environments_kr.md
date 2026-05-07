# 0. 개발 환경 셋업 (한국어)

Trans To Vostok 모드에 기여하기 전 한 번 셋업하는 환경 가이드입니다.
Windows 기준이며, macOS/Linux에서도 비슷하게 진행 가능합니다.

> 이 문서는 **모드 빌드 / 코드 수정 / 번역 작업**을 모두 포괄합니다. 단순히 xlsx만 수정해서 PR/Issue로 제출할 거면 [Excel](#1-필요-프로그램) + [Git](#git-설치) + [Fork &amp; Clone](#3-fork--clone)만 있으면 충분합니다.

---

## 1. 필요 프로그램

| 용도                  | 프로그램                                          | 필수 여부                 |
| --------------------- | ------------------------------------------------- | ------------------------- |
| 번역 데이터 편집      | **Microsoft Excel** (또는 LibreOffice Calc) | 필수                      |
| 빌드 / 도구 실행      | **Python 3.10+**                            | 필수                      |
| 버전 관리             | **Git**                                     | 필수                      |
| 코드 편집 (권장)      | **VS Code**                                 | 권장                      |
| 게임 소스 추출 (선택) | **gdre_tools**                              | 선택 (전체 validation 시) |

### Microsoft Excel

- xlsx 파일 (Translation.xlsx / Glossary.xlsx / Texture.xlsx) 편집용.
- LibreOffice Calc 등도 사용 가능하나 셀 내 줄바꿈(`Alt+Enter`) 동작과 서식 보존을 위해 **Microsoft Excel** 권장.

### Python 3 (Python 3.13 권장됨)

- 다운로드: https://apps.microsoft.com/detail/9PNRBTZXMB4Z?hl=neutral&gl=KR&ocid=pdpshare
- 설치 후 PowerShell에서 확인:
  ```powershell
  python --version
  pip --version
  ```

### Git 설치

- 다운로드: [https://git-scm.com/download/win](https://git-scm.com/download/win)
- 기본 옵션으로 설치하면 됨.
- 설치 후 PowerShell에서 확인:
  ```powershell
  git --version
  ```
- 첫 사용 시 사용자 정보 등록:
  ```powershell
  git config --global user.name "Your Name"
  git config --global user.email "you@example.com"
  ```

### VS Code (권장)

- 다운로드: [https://code.visualstudio.com/](https://code.visualstudio.com/)
- xlsx는 Excel에서 편집하지만, GDScript / Python / 마크다운 / TSV diff 검토 등에 사용.
- 권장 확장: **Python**, **Rainbow CSV** (TSV 가독성), **GitLens**.

### gdre_tools (선택)

- RTV 게임의 `.pck`에서 소스 (`.gd` / `.tscn` / `.tres`)를 추출하기 위한 도구.
- **번역 작업만 하는 기여자는 필요 없습니다.**
  빌드 시 `parsed_text/` 폴더가 없으면 자동으로 일부 검증을 스킵함.
- 전체 validation까지 돌려보고 싶다면 [bruvzg/gdsdecomp releases](https://github.com/bruvzg/gdsdecomp/releases)에서 Windows 빌드 다운로드 → `tools/3rd_party/gdre_tools/gdre_tools.exe`에 배치.
- 추출 절차는 README 본문 참조.

---

## 2. 게임과 ModLoader 설치

이 모드는 [Metro&#39;s ModLoader](https://www.nexusmods.com/roadtovostok)를 통해 로드됩니다.

1. **Road to Vostok** (Steam) 설치.
2. **Metro's ModLoader** 설치. 위 링크 또는 modworkshop 참고.
3. 모드 폴더 위치 확인: `Road to Vostok/mods/`
   - 경로 예시: 
   C 드라이브: `C:\Program Files (x86)\Steam\steamapps\common/Road to Vostok/mods/`
   D 드라이브: `D:/SteamLibrary/steamapps/common/Road to Vostok/mods/`
---

## 3. Fork & Clone

### 3-1. GitHub Fork 만들기

1. 브라우저에서 본 저장소 페이지 접속.
2. 우측 상단 **Fork** 버튼 클릭 → 본인 계정으로 fork 생성.

### 3-2. Repo Clone (Road to Vostok/mods/ 안에)

PowerShell에서:

```powershell
cd "D:/SteamLibrary/steamapps/common/Road to Vostok/mods"
git clone https://github.com/<your-username>/<repo-name>.git "Trans To Vostok"
```

> 모드 폴더 이름이 `Trans To Vostok` (공백 포함) 이어야 ModLoader가 정상 인식합니다.

### 3-3. Upstream 등록 (원본 저장소 추적)

```powershell
cd "Trans To Vostok"
git remote add upstream https://github.com/<original-owner>/<repo-name>.git
git fetch upstream
```

이후 원본의 최신 변경사항을 가져올 때:

```powershell
git fetch upstream
git merge upstream/main
```

---

## 4. Python 의존성 설치

```powershell
# cd "{Game Directory}/mods/Trans to Vostok"
# 예: cd "D:/SteamLibrary/steamapps/common/Road to Vostok/mods/Trans To Vostok"
cd "C:\Program Files (x86)\Steam\steamapps\common/Road to Vostok\mods"
pip install -r tools/requirements.txt
```

주요 의존성: `openpyxl` (xlsx 읽기/쓰기) 등.

---

## 5. 첫 빌드 시도

자신의 locale (예: Korean) 빌드:

```powershell
python tools/build_mod_package.py Korean
```

성공 시 `mods/Trans To Vostok.zip` 생성. 게임에서 ModLoader가 이 zip을 인식.

> `parsed_text/`가 없는 환경 (=gdre_tools 미설치)에서도 빌드는 정상 동작합니다. parsed_text 의존 검증만 자동 스킵되고 다른 검증 (duplicate / flags / method / whitespace 등)은 그대로 수행됩니다.

---

## 6. 일반 작업 흐름

> ### ⚠️ 시작 전 필수 — `main` 브랜치에 직접 작업하지 마세요
>
> Clone 직후 기본 브랜치는 `main` 입니다. 이 상태에서 바로 xlsx를 편집하고 commit하면 **fork의 main에 작업이 쌓여 PR 흐름이 꼬입니다**.
>
> 첫 작업 전에 반드시 **새 브랜치 생성** (아래 1번 단계). 자세한 브랜치 / PR 흐름은 [4_How_to_Pull_Request_kr.md](4_How_to_Pull_Request_kr.md) 참조.

1. **새 브랜치 생성** (작업별로):
   ```powershell
   # upstream 최신을 main에 반영
   git fetch upstream
   git checkout main
   git merge upstream/main

   # 작업용 브랜치
   git checkout -b <type>/<short-description>
   # 예: git checkout -b translate/korean-items-fix
   ```
   브랜치 명명 컨벤션 → [4_How_to_Pull_Request_kr.md](4_How_to_Pull_Request_kr.md) §2 참조.

2. **xlsx / 코드 수정**
3. **변경 확인**:
   ```powershell
   git status
   git diff
   ```

   - xlsx는 binary라 diff가 안 보이지만, `Translation_TSV/<locale>/` 의 TSV shadow에서 변경사항을 볼 수 있습니다.
4. **빌드로 검증**:
   ```powershell
   python tools/build_mod_package.py Korean
   ```
5. **Commit & Push**:
   ```powershell
   git add "Trans To Vostok/Korean/Translation.xlsx" "Translation_TSV/Korean/"
   git commit -m "Korean: fix translation for X"
   git push origin <branch-name>
   ```
6. **GitHub에서 Pull Request 생성** (your fork → 원본 repo). 자세한 PR 작성법 → [4_How_to_Pull_Request_kr.md](4_How_to_Pull_Request_kr.md).

---

## 7. 다음 단계

- 번역 작업 → `README/CONTRIBUTING.md` ("How to be credited")
- 더 자세한 빌드 옵션 / 도구 설명 → `README.md`
- 새 언어 추가 (DeepL 자동 번역) → `README/CONTRIBUTING.md` 의 "Adding a new language" 섹션

---
