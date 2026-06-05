# Roles

이것은 해당 프로젝트에 참여하는 인원들의 Role을 간단하게 작성한 것입니다.

Role는 한 사람이 여러가지를 가질 수도 있습니다.

## Administrator

- Repository 개발
- Crowdin 프로젝트 관리 (멤버 초대, 역할 설정)
- 새 언어 추가 (`Add_new_language.md`)
- Crowdin → 로컬 동기화 (`pull_from_crowdin.py`, `get_member_list.py`)
- 릴리즈 빌드 (`build_mod_package.py`)

## Developer

- Python 툴 / GDScript 개발
- 게임 업데이트 시 파싱 및 Template TSV 갱신
- Repository 직접 쓰기 권한
- 모드 Testing

## Translator

번역 기여는 **Crowdin**을 통해서만 이루어집니다. Repository PR은 받지 않습니다.

Crowdin 역할에 따라 크레딧이 자동 분류됩니다:

| 크레딧 표시             | Crowdin 역할                           |
| ----------------------- | -------------------------------------- |
| Lead Translator         | Owner / Manager / Language Coordinator |
| Translator              | Proofreader                            |
| Translation Contributor | Translator (Member), 번역 기여 > 0     |

local 환경에서 crowdin API를 통해 번역/push_to_crowdin을 위해서는 crowdin의 developer 권한이 필요합니다.

crowdin에 대한 developer 권한을 가진사람에 대한 처리는 현재 설계중에 있습니다.

## Texture Reworker

- 텍스처 이미지 제작 / 수정
- `Texture.xlsx`의 `Reworked by` / `Contributors` 열에 이름 직접 기입
- `get_texture_credits.py`가 빌드 시 크레딧으로 읽어들임
- Repository 접근 필요 → Administrator를 통해 참여
