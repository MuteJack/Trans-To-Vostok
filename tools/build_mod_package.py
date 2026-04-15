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
    - Trans To Vostok/translator.gd                         (런타임 엔진)
    - Trans To Vostok/<locale>/translation_static.tsv
    - Trans To Vostok/<locale>/translation_literal_scoped.tsv
    - Trans To Vostok/<locale>/translation_pattern_scoped.tsv
    - Trans To Vostok/<locale>/translation_literal.tsv
    - Trans To Vostok/<locale>/translation_pattern.tsv

출력: mods/Trans To Vostok.zip
"""
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
MOD_FILES = ["translator.gd"]  # 모드 루트에 배치되는 파일들
LOCALE_FILES = [
    "translation_static.tsv",
    "translation_literal_scoped.tsv",
    "translation_pattern_scoped.tsv",
    "translation_literal.tsv",
    "translation_pattern.tsv",
]


def build_locale(tools_dir: Path, locale: str) -> bool:
    """build_runtime_tsv.py를 호출하여 TSV 생성. 성공 여부 반환."""
    print(f"=== 로케일 빌드: {locale} ===")
    result = subprocess.run(
        [sys.executable, "build_runtime_tsv.py", locale],
        cwd=tools_dir,
    )
    if result.returncode != 0:
        print(f"[ERROR] {locale} 빌드 실패")
        return False
    print()
    return True


def package_mod(mod_root: Path, locales: list[str], out_path: Path) -> int:
    """
    모드를 .vmz (ZIP)으로 패키징.
    반환: 패키징된 파일 개수
    """
    count = 0

    # 원자적 쓰기
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. mod.txt → ZIP 루트
            mod_txt = mod_root / "mod.txt"
            if not mod_txt.exists():
                raise FileNotFoundError(f"mod.txt가 없습니다: {mod_txt}")
            zf.write(mod_txt, "mod.txt")
            count += 1

            # 2. 모드 파일들 → Trans To Vostok/
            for fname in MOD_FILES:
                src = mod_root / fname
                if not src.exists():
                    raise FileNotFoundError(f"모드 파일이 없습니다: {src}")
                zf.write(src, f"{MOD_NAME}/{fname}")
                count += 1

            # 3. 로케일 파일들 → Trans To Vostok/<locale>/
            for locale in locales:
                locale_dir = mod_root / locale
                for fname in LOCALE_FILES:
                    src = locale_dir / fname
                    if not src.exists():
                        raise FileNotFoundError(f"로케일 파일이 없습니다: {src}")
                    zf.write(src, f"{MOD_NAME}/{locale}/{fname}")
                    count += 1

        # 성공 시 원본 덮어쓰기
        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    return count


def main() -> int:
    locales = sys.argv[1:] if len(sys.argv) > 1 else ["Korean"]

    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent                # mods/Trans To Vostok
    mods_parent = mod_root.parent                # mods/
    out_path = mods_parent / f"{MOD_NAME}.zip"

    # 1. 각 로케일 빌드 (validate 포함)
    for locale in locales:
        locale_dir = mod_root / locale
        if not locale_dir.exists():
            print(f"[ERROR] 로케일 폴더가 없습니다: {locale_dir}")
            return 1
        if not build_locale(script_dir, locale):
            return 1

    # 2. 패키징
    print(f"=== 패키징 ===")
    print(f"대상 로케일: {', '.join(locales)}")
    print(f"출력 파일: {out_path}")
    try:
        file_count = package_mod(mod_root, locales, out_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    size_kb = out_path.stat().st_size / 1024.0
    print()
    print("=" * 60)
    print(f"빌드 완료: {out_path.name}")
    print(f"  파일 수: {file_count}")
    print(f"  크기:    {size_kb:.1f} KB")
    print(f"  로케일:  {', '.join(locales)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
