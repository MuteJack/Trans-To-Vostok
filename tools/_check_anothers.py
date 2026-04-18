"""
[임시 도구] 자동 추출 도구가 잡지 못하는 번역 후보를 스캔해 TSV로 출력.

검증/빌드에는 사용하지 않고, 번역 대상 후보를 찾는 참고용.

스캔 항목:
    1. GDScript 배열 리터럴의 문자열 (var/const x = ["...", ...])
    2. Loader.gd 의 LoadScene() 씬 이름 목록

사용법:
    python _check_anothers.py                   # 기본 경로
    python _check_anothers.py <scripts_dir>     # Scripts 디렉토리 지정

출력:
    .tmp/extracted_text/_anothers.tsv
"""
import csv
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


OUT_COLUMNS = ["source", "filename", "line", "var", "text"]

ARRAY_START_RE = re.compile(r'(?:var|const)\s+(?P<name>\w+)\s*=\s*\[')
STRING_RE = re.compile(r'"([^"]*)"')
SCENE_CMP_RE = re.compile(r'scene\s*==\s*"([^"]+)"')

SKIP_PATTERNS = [
    "res://", "uid://", ".tscn", ".scn", ".tres", ".gd",
    ".png", ".obj", ".wav", ".ogg", ".mp3", ".ttf",
    ".import", ".remap", ".cfg", ".json",
]


def _is_candidate(s: str) -> bool:
    if len(s) < 2:
        return False
    if any(p in s for p in SKIP_PATTERNS):
        return False
    if s.startswith("/") or s.startswith("\\"):
        return False
    alpha = sum(1 for c in s if c.isalpha())
    if alpha < 2:
        return False
    return True


# ==========================================
# 1. GDScript 배열 문자열 스캔
# ==========================================

def scan_gd_arrays(scripts_dir: Path) -> list[dict]:
    """var/const 배열 리터럴에서 문자열 값을 추출."""
    results = []
    for gd in sorted(scripts_dir.rglob("*.gd")):
        try:
            rel = gd.relative_to(scripts_dir).as_posix()
            lines = gd.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        current_var = ""
        in_array = False
        bracket_depth = 0

        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()

            if not in_array:
                m = ARRAY_START_RE.search(stripped)
                if m:
                    current_var = m.group("name")
                    in_array = True
                    bracket_depth = stripped.count("[") - stripped.count("]")
                    rest = stripped[m.end():]
                    for sm in STRING_RE.finditer(rest):
                        val = sm.group(1)
                        if _is_candidate(val):
                            results.append({
                                "source": "array",
                                "filename": rel,
                                "line": lineno,
                                "var": current_var,
                                "text": val,
                            })
                    if bracket_depth <= 0:
                        in_array = False
                        current_var = ""
            else:
                bracket_depth += stripped.count("[") - stripped.count("]")
                for sm in STRING_RE.finditer(stripped):
                    val = sm.group(1)
                    if _is_candidate(val):
                        results.append({
                            "source": "array",
                            "filename": rel,
                            "line": lineno,
                            "var": current_var,
                            "text": val,
                        })
                if bracket_depth <= 0:
                    in_array = False
                    current_var = ""

    return results


# ==========================================
# 2. Loader.gd 씬 이름 스캔
# ==========================================

def scan_scene_names(scripts_dir: Path) -> list[dict]:
    """Loader.gd 의 if scene == "Name" 패턴에서 씬 이름을 추출."""
    loader_path = scripts_dir / "Loader.gd"
    if not loader_path.exists():
        print(f"[WARN] Loader.gd 없음: {loader_path}", file=sys.stderr)
        return []

    try:
        text = loader_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"[WARN] 읽기 실패: {loader_path} ({e})", file=sys.stderr)
        return []

    lines = text.splitlines()

    # label.hide() 가 있는 씬 찾기 (로딩 메시지 미표시)
    hidden_scenes: set = set()
    hide_re = re.compile(r'label\.hide\(\)')
    for lineno, line in enumerate(lines, 1):
        if hide_re.search(line.strip()):
            for back in range(max(0, lineno - 3), lineno):
                for m in SCENE_CMP_RE.finditer(lines[back]):
                    hidden_scenes.add(m.group(1))

    # 모든 씬 이름 수집 (중복 제거)
    seen: set = set()
    results = []
    for lineno, line in enumerate(lines, 1):
        for m in SCENE_CMP_RE.finditer(line.strip()):
            name = m.group(1)
            if name in seen:
                continue
            seen.add(name)
            loading_visible = name not in hidden_scenes
            results.append({
                "source": "scene" if loading_visible else "scene_hidden",
                "filename": "Loader.gd",
                "line": lineno,
                "var": "LoadScene",
                "text": name,
            })

    return results


# ==========================================
# TSV 출력
# ==========================================

def write_tsv(out_path: Path, rows: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(OUT_COLUMNS)
            for row in rows:
                writer.writerow([row.get(c, "") for c in OUT_COLUMNS])
        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


# ==========================================
# 메인
# ==========================================

def main() -> int:
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    default_scripts = mod_root / ".tmp" / "pck_recovered" / "Scripts"
    out_path = mod_root / ".tmp" / "extracted_text" / "_anothers.tsv"

    scripts_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_scripts.resolve()

    if not scripts_dir.exists():
        print(f"[ERROR] 경로가 없습니다: {scripts_dir}", file=sys.stderr)
        return 1

    all_rows: list[dict] = []

    # 1. 배열 스캔
    print("GDScript 배열 스캔 중...")
    array_rows = scan_gd_arrays(scripts_dir)
    all_rows.extend(array_rows)
    print(f"  배열 문자열: {len(array_rows)}개")

    # 2. 씬 이름 스캔
    print("씬 이름 스캔 중...")
    scene_rows = scan_scene_names(scripts_dir)
    all_rows.extend(scene_rows)
    visible = sum(1 for r in scene_rows if r["source"] == "scene")
    hidden = sum(1 for r in scene_rows if r["source"] == "scene_hidden")
    print(f"  씬 이름: {len(scene_rows)}개 (로딩 표시 {visible}, 미표시 {hidden})")

    if not all_rows:
        print("\n후보를 찾지 못했습니다.")
        return 0

    # TSV 출력
    write_tsv(out_path, all_rows)
    print(f"\n출력: {out_path}")
    print(f"총 {len(all_rows)}개 엔트리")

    # 화면에도 표시
    print()
    for r in all_rows:
        tag = r["source"]
        print(f"  [{tag:<13}] {r['filename']}:{r['line']}  {r['var']}: {r['text']!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
