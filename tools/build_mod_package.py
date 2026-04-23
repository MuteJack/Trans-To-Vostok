"""
Trans To Vostok 모드를 .zip 파일로 패키징.

사용법:
    python build_mod_package.py [locale...]

예시:
    python build_mod_package.py Korean
    python build_mod_package.py Korean Japanese  (다국어 지원 시)
    python build_mod_package.py                   (기본: Korean)

동작:
1. 지정된 로케일에 대해 build_runtime_tsv를 호출하여 TSV 생성 (검증 포함)
2. 모드 파일 구조를 ZIP으로 압축하여 ../Trans To Vostok.zip 생성
    - mod.txt                                               (모드 메타데이터)
    - Trans To Vostok/translator_ui.gd                      (UI + 엔진 관리)
    - Trans To Vostok/translator.gd                         (텍스트 번역 엔진)
    - Trans To Vostok/texture_loader.gd                     (텍스처 교체 엔진)
    - Trans To Vostok/locale.json                           (로케일 설정)
    - Trans To Vostok/<locale>/translation_*.tsv            (런타임 TSV)
    - Trans To Vostok/<locale>/metadata.tsv
    - Trans To Vostok/<locale>/textures/**                   (번역 이미지, 있으면 포함)

출력: mods/Trans To Vostok.zip
"""
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Windows 콘솔 한글 출력 지원
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


MOD_NAME = "Trans To Vostok"
MOD_FILES = ["translator_ui.gd", "translator.gd", "texture_loader.gd", "locale.json"]
LOCALE_FILES = [
    "metadata.tsv",
    "translation_static.tsv",
    "translation_literal_scoped.tsv",
    "translation_pattern_scoped.tsv",
    "translation_literal.tsv",
    "translation_pattern.tsv",
    "translation_substr.tsv",
]
TEXTURE_DIR = "textures"
TEXTURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def build_locale(tools_dir: Path, locale: str, soft: bool = False, ignore: bool = False) -> bool:
    """build_runtime_tsv.py를 호출하여 TSV 생성. 성공 여부 반환."""
    print(f"=== 로케일 빌드: {locale} ===")
    cmd = [sys.executable, "build_runtime_tsv.py", locale]
    if ignore:
        cmd.append("--ignore")
    elif soft:
        cmd.append("--soft")
    result = subprocess.run(cmd, cwd=tools_dir)
    if result.returncode != 0:
        print(f"[ERROR] {locale} 빌드 실패")
        return False
    print()
    return True


def package_mod(mod_root: Path, locales: list[str], out_path: Path) -> tuple[int, int]:
    """
    모드를 .vmz (ZIP)으로 패키징.
    반환: (전체 파일 개수, 텍스처 파일 개수)
    """
    pkg_root = mod_root / MOD_NAME
    count = 0
    texture_count = 0

    # 원자적 쓰기
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. mod.txt → ZIP 루트 (outer/repo root)
            mod_txt = mod_root / "mod.txt"
            if not mod_txt.exists():
                raise FileNotFoundError(f"mod.txt가 없습니다: {mod_txt}")
            zf.write(mod_txt, "mod.txt")
            count += 1

            # 2. 모드 파일들 (pkg_root) → Trans To Vostok/
            for fname in MOD_FILES:
                src = pkg_root / fname
                if not src.exists():
                    raise FileNotFoundError(f"모드 파일이 없습니다: {src}")
                zf.write(src, f"{MOD_NAME}/{fname}")
                count += 1

            # 3. 로케일 파일들 → Trans To Vostok/<locale>/
            for locale in locales:
                locale_dir = pkg_root / locale
                for fname in LOCALE_FILES:
                    src = locale_dir / fname
                    if not src.exists():
                        raise FileNotFoundError(f"로케일 파일이 없습니다: {src}")
                    zf.write(src, f"{MOD_NAME}/{locale}/{fname}")
                    count += 1

                # 4. 텍스처 폴더 → Trans To Vostok/<locale>/textures/**
                # 폴더가 없으면 스킵 (로케일별 선택 사항)
                textures_dir = locale_dir / TEXTURE_DIR
                if textures_dir.exists() and textures_dir.is_dir():
                    for tex_file in sorted(textures_dir.rglob("*")):
                        if not tex_file.is_file():
                            continue
                        if tex_file.suffix.lower() not in TEXTURE_EXTENSIONS:
                            continue
                        rel = tex_file.relative_to(locale_dir).as_posix()
                        zf.write(tex_file, f"{MOD_NAME}/{locale}/{rel}")
                        count += 1
                        texture_count += 1

        # 성공 시 원본 덮어쓰기
        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    return count, texture_count


def load_locale_config(mod_root: Path) -> list[dict]:
    """locale.json 에서 enabled=true 인 로케일 목록을 반환."""
    locale_json = mod_root / MOD_NAME / "locale.json"
    if not locale_json.exists():
        return []
    try:
        data = json.loads(locale_json.read_text(encoding="utf-8"))
        return [loc for loc in data.get("locales", []) if loc.get("enabled", False)]
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] locale.json 읽기 실패: {e}", file=sys.stderr)
        return []


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent                # mods/Trans To Vostok

    # --soft / --hard / --ignore 파싱
    cli_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cli_flags = {a for a in sys.argv[1:] if a.startswith("--")}
    soft = "--soft" in cli_flags
    ignore = "--ignore" in cli_flags

    # 커맨드라인 인자가 있으면 override, 없으면 locale.json 에서 읽기
    if cli_args:
        locales = cli_args
        print(f"커맨드라인 로케일: {locales}")
    else:
        locale_config = load_locale_config(mod_root)
        if locale_config:
            locales = [lc["dir"] for lc in locale_config]
            display = [f"{lc.get('display', lc['dir'])} ({lc['dir']})" for lc in locale_config]
            print(f"locale.json 에서 로드: {', '.join(display)}")
        else:
            locales = ["Korean"]
            print("locale.json 없음, 기본값: Korean")
    mods_parent = mod_root.parent                # mods/
    out_path = mods_parent / f"{MOD_NAME}.zip"

    # 1. 각 로케일 빌드 (validate 포함, 폴더 없는 locale 스킵)
    pkg_root = mod_root / MOD_NAME
    build_locales = []
    for locale in locales:
        locale_dir = pkg_root / locale
        xlsx_path = locale_dir / "Translation.xlsx"
        if not locale_dir.exists() or not xlsx_path.exists():
            print(f"[SKIP] {locale} — 번역 폴더/xlsx 없음 (기본 언어)")
            continue
        if not build_locale(script_dir, locale, soft=soft, ignore=ignore):
            return 1
        build_locales.append(locale)
    locales = build_locales

    # 2. 패키징
    print(f"=== 패키징 ===")
    print(f"대상 로케일: {', '.join(locales)}")
    print(f"출력 파일: {out_path}")
    try:
        file_count, texture_count = package_mod(mod_root, locales, out_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    size_kb = out_path.stat().st_size / 1024.0
    print()
    print("=" * 60)
    print(f"빌드 완료: {out_path.name}")
    print(f"  파일 수:  {file_count}  (텍스처 {texture_count}개 포함)")
    print(f"  크기:     {size_kb:.1f} KB")
    print(f"  로케일:   {', '.join(locales)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
