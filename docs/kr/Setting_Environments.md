# 개발 환경 셋업 (한국어)

Trans To Vostok 모드에 기여하기 전 한 번 셋업하는 환경 가이드입니다.
Windows 기준이며, macOS/Linux에서도 비슷하게 진행 가능합니다.

> **이 가이드의 대상**
>
> - **개발자** (코드 + 번역 + 빌드 전체): 모든 섹션 필요
> - **번역/테스터** (저장소를 클론하여 번역 작업 + 인게임 테스트): 모든 섹션 필요. 단, DeepL 토큰은 선택
> - **번역가 (Crowdin 웹만 사용)**: 이 문서 **불필요**. 별도의 [Crowdin 웹사이트를 통한 번역 가이드](Translating_using_crowdin.md) 참조

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

- xlsx 파일(Translation.xlsx / Texture.xlsx) 편집용입니다.
- LibreOffice Calc 등도 사용할 수 있으나, 셀 내 줄바꿈(`Alt+Enter`) 동작과 서식 보존을 위해 **Microsoft Excel**을 권장합니다.

### Python 3 (Python 3.13 권장됨)

- 다운로드: https://apps.microsoft.com/detail/9PNRBTZXMB4Z?hl=neutral&gl=KR&ocid=pdpshare
- 설치 후 PowerShell에서 확인:
  ```powershell
  python --version
  pip --version
  ```

### Git 설치

- 다운로드: https://git-scm.com/download/win
- 기본 옵션으로 설치합니다.
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

- 다운로드: https://code.visualstudio.com/
- xlsx는 Excel에서 편집하지만, GDScript / Python / 마크다운 / TSV diff 검토 등에 사용합니다.
- 권장 확장: **Python**, **Rainbow CSV**(TSV 가독성), **GitLens**.

### gdre_tools (선택)

- RTV 게임의 `.pck`에서 소스(`.gd` / `.tscn` / `.tres`)를 추출하기 위한 도구입니다.
- **번역 작업만 하는 기여자는 필요하지 않습니다.**
  빌드 시 `parsed_text/` 폴더가 없으면 자동으로 일부 검증을 스킵합니다.
- 전체 validation까지 돌려보고 싶다면 [bruvzg/gdsdecomp releases](https://github.com/bruvzg/gdsdecomp/releases)에서 Windows 빌드를 다운로드하여 `tools/3rd_party/gdre_tools/gdre_tools.exe`에 배치합니다.

---

## 2. 게임과 ModLoader 설치

이 모드는 [Metro&#39;s ModLoader](https://www.nexusmods.com/roadtovostok)를 통해 로드됩니다.

1. **Road to Vostok**(Steam)를 설치합니다.
2. **Metro's ModLoader**를 설치합니다. 위 링크 또는 modworkshop을 참고하세요.
3. 모드 폴더 위치 확인: `Road to Vostok/mods/`
   - 경로 예시:
     - C 드라이브: `C:/Program Files (x86)/Steam/steamapps/common/Road to Vostok/mods/`
     - D 드라이브: `D:/SteamLibrary/steamapps/common/Road to Vostok/mods/`

---

## 3. Fork & Clone

### 3-1. GitHub Fork 만들기

1. 브라우저에서 본 저장소 페이지에 접속합니다.
2. 우측 상단 **Fork** 버튼을 클릭하여 본인 계정으로 fork를 생성합니다.

### 3-2. Repo Clone (Road to Vostok/mods/ 안에)

PowerShell에서:

```powershell
cd "D:/SteamLibrary/steamapps/common/Road to Vostok/mods"
git clone https://github.com/<your-username>/<repo-name>.git "Trans To Vostok"
```

> 모드 폴더 이름이 `Trans To Vostok`(공백 포함)이어야 ModLoader가 정상적으로 인식합니다.

### 3-3. Upstream 등록 (원본 저장소 추적)

```powershell
cd "Trans To Vostok"
git remote add upstream https://github.com/<original-owner>/<repo-name>.git
git fetch upstream
```

이후 원본의 최신 변경사항을 가져올 때:

```powershell
git fetch upstream
git merge upstream/master
```

---

## 4. Python 의존성 설치

```powershell
cd "D:/SteamLibrary/steamapps/common/Road to Vostok/mods/Trans To Vostok"
pip install -r tools/requirements.txt
```

설치되는 패키지:

| 패키지                 | 용도                                        |
| ---------------------- | ------------------------------------------- |
| `openpyxl`           | xlsx 읽기/쓰기 (모든 빌드/번역 도구의 기반) |
| `deepl`              | 신규 언어 자동 시드 번역 (DeepL API)        |
| `crowdin-api-client` | Crowdin push / pull (별도 CLI 설치 불필요)  |

---

## 5. API 토큰 설정 (DeepL / Crowdin)

DeepL 자동 번역 또는 Crowdin push/pull을 사용한다면 토큰이 필요합니다. xlsx만 직접 수정하는 경우 이 단계는 건너뛰어도 됩니다.

### 5-1. `secrets.json` 만들기

저장소 루트의 `secrets_example.json`을 같은 폴더에 `secrets.json`으로 복사:

```powershell
# 저장소 루트(Trans To Vostok)에서
cp secrets_example.json secrets.json
```

> `secrets.json`은 `.gitignore`에 등록되어 있어 커밋되지 않습니다. 실제 키를 `secrets_example.json`에 직접 적거나, `.gitignore`에서 `secrets.json`을 지우지 마십시오.

### 5-2. DeepL API 키 (신규 언어 자동 시드용)

- 발급: https://www.deepl.com/account/summary → Auth Key
- Free 플랜은 월 500K 글자입니다. 무료 키는 `:fx`로 끝납니다.
- `secrets.json`의 `deepl_api_key`에 입력합니다.

번역가/테스터로 기존 언어 작업만 한다면 비워두어도 됩니다.

### 5-3. Crowdin Personal Token (push / pull용)

- 발급: Crowdin → Account Settings → API & SSO → **New Token**
- 필요 권한(scopes): **Projects (Read & Write)**, **Source Files**, **Translations**, **Glossary (Read & Write)**
- `secrets.json`의 `crowdin_personal_token`에 입력합니다.

> Java 기반 Crowdin CLI는 **불필요**합니다. 모든 통신은 `crowdin-api-client` Python 라이브러리를 통해 이루어집니다.

---

## 6. 첫 빌드 시도

```powershell
python tools/build_mod_package.py
```

인자 없이 실행하면 `Trans To Vostok/locale.json`에 등록된 활성 locale 전부를 빌드합니다. 특정 locale만 디버그하려면 인자로 지정 (디버그/검증용):

```powershell
python tools/build_mod_package.py Korean              # Korean만
python tools/build_mod_package.py Korean French       # 두 locale만
```

성공 시 `mods/Trans To Vostok.zip`이 생성되며, 게임에서 ModLoader가 이 zip을 인식합니다.

> `parsed_text/`가 없는 환경 (=gdre_tools 미설치)에서도 빌드는 정상 동작합니다. parsed_text 의존 검증만 자동 스킵되고 다른 검증 (duplicate / flags / method / whitespace 등)은 그대로 수행됩니다.

---

## 7. 일반 작업 흐름

> ### [Important!!] 번역 수정사항은 PR(Pull Request)로 받지 않습니다
>
> 모든 번역 기여는 **Crowdin 웹 UI** 또는 **Crowdin API**를 통해서만 받습니다. (QA, Git Conflict 방지 목적)
> Translations/ 만 변경한 PR은 머지되지 않으니 [Crowdin 웹사이트를 통한 번역 가이드](Translating_using_crowdin.md) 또는 [로컬 저장소 활용 번역 가이드](Translating_on_Local.md)를 참조하세요.
>
> 이 §7은 **코드/도구/빌드 시스템 변경**(예: `tools/`, `Trans To Vostok/*.gd`, 빌드 스크립트, 가이드 문서)에 한정된 PR 흐름입니다.

> ### [Important!!] `master` 브랜치에 직접 작업하지 마십시오
>
> Clone 직후 기본 브랜치는 `master`입니다. 이 상태에서 바로 수정하고 commit하면 **fork의 master에 작업이 쌓여 PR 흐름이 꼬입니다**.
>
> 첫 작업 전에 반드시 **새 브랜치를 생성**하세요(아래 1번 단계). 자세한 브랜치 / PR 흐름은 [How_to_Pull_Request.md](How_to_Pull_Request.md)를 참조하세요.

1. **새 브랜치 생성** (작업별로):

   ```powershell
   # upstream 최신을 master에 반영
   git fetch upstream
   git checkout master
   git merge upstream/master

   # 작업용 브랜치
   git checkout -b <type>/<short-description>
   # 예: git checkout -b tools/fix-pull-locale-mapping
   ```

   브랜치 명명 컨벤션은 `How_to_Pull_Request.md` §2를 참조하세요.
2. **코드 / 도구 / 문서 수정**
3. **변경 확인**:

   ```powershell
   git status
   git diff
   ```
4. **빌드로 회귀 검증** (도구 수정이 빌드 출력에 영향을 줄 수 있다면):

   ```powershell
   python tools/build_mod_package.py
   ```
5. **Commit & Push**:

   ```powershell
   git add <변경한 파일들>
   git commit -m "tools: fix Crowdin pull locale folder remap"
   git push origin <branch-name>
   ```
6. **GitHub에서 Pull Request를 생성합니다** (your fork → 원본 repo). 자세한 PR 작성법은 `How_to_Pull_Request.md`를 참조하세요.

---

## 8. 다음 단계

- **번역만 하고 싶은 경우** → [Translating_using_crowdin.md](Translating_using_crowdin.md) (Crowdin 웹 UI)
- **번역 작업 + 인게임 테스트** → [Translating_on_Local.md](Translating_on_Local.md) (`pull_from_crowdin` + 빌드 + 테스트)
- **새 언어 추가** → [Add_new_language.md](../../docs_dev/kr/Add_new_language.md)
- **method 가이드 / 매칭 디버깅** → [Translation_Methods.md](../../docs_dev/kr/Translation_Methods.md)
- **Crowdin → 저장소 sync (메인테이너)** → [Pull_from_Crowdin.md](../../docs_dev/kr/Pull_from_Crowdin.md)
