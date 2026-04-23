"""
Godot .tres 파일을 파싱해 지정한 필드 값을 추출한다.

[resource] 블록 내부의 `field = "value"` 패턴을 찾아 값을 TSV로 출력한다.
여러 줄 문자열(개행 포함)과 이스케이프된 따옴표(\")를 정확히 처리한다.

원본 .tres 파일마다 하나의 .tres.tsv 파일이 생성되며, 출력 경로는
원본의 pck_recovered 기준 상대 경로를 parsed_text 아래에 미러링한다.

    pck_recovered/Events/List/D1_Generalist.tres
        ↓
    parsed_text/Events/List/D1_Generalist.tres.tsv

출력 컬럼: filetype, location, field, text

실행 모드:
  1) 배치 (권장):  python parse_tres_text.py  또는 --config <path>
     tres_list.json 을 읽어 여러 그룹을 한 번에 처리.
     기본 경로: 이 스크립트 옆의 tres_list.json.
  2) 단일 job:     python parse_tres_text.py --input <dir> --fields <list>

사용법:
    python parse_tres_text.py                       # 기본 tres_list.json 사용
    python parse_tres_text.py --config other.json   # 다른 config 사용
    python parse_tres_text.py --input Events/List --fields name,description

tres_list.json 스키마:
    {
      "groups": [
        {
          "name": "Events",                     # 선택사항 (진행 표시용)
          "dir": "Events",                      # pck_recovered 기준 상대 경로
          "fields": ["name", "description"],    # 추출할 필드
          "targets": ["List"]                   # dir 기준 상대 경로 (파일/디렉토리)
        }
      ]
    }
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

# Windows 콘솔 한글 출력 지원
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


# 출력 TSV 고정 컬럼 (tscn 추출 도구와 통일)
# .tres 엔트리는 노드 계층이 없으므로 location/parent/type/unique_id 를 빈 값으로 둔다.
# prop 컬럼에 tres의 필드 이름(예: "name", "description")을 넣는다.
OUT_COLUMNS = ["filename", "filetype", "location", "parent", "name", "type", "property", "unique_id", "text"]

# 기본 경로
DEFAULT_CONFIG_NAME = "tres_list.json"


# ==========================================
# .tres 파서
# ==========================================

_SUB_RESOURCE_RE = re.compile(r"^\[sub_resource\b", re.MULTILINE)


def _find_resource_block(text: str) -> tuple[int, int]:
    """
    [resource] 블록의 본문 시작~끝 오프셋을 반환.
    [resource] 라인 다음부터 파일 끝까지가 블록 본문.
    """
    m = re.search(r"^\[resource\]\s*$", text, re.MULTILINE)
    if not m:
        return (-1, -1)
    return (m.end(), len(text))


def _count_sub_resources(text: str) -> int:
    """[sub_resource ...] 블록 개수를 센다. 경고 로그용."""
    return len(_SUB_RESOURCE_RE.findall(text))


def _extract_string_field(body: str, field_name: str) -> str | None:
    """
    [resource] 블록 안에서 `field_name = "값"` 을 찾아 값을 반환.
    이스케이프된 따옴표(\")와 여러 줄 문자열을 처리한다.
    찾지 못하면 None 반환.
    """
    pattern = re.compile(
        rf'^{re.escape(field_name)}\s*=\s*"', re.MULTILINE
    )
    m = pattern.search(body)
    if not m:
        return None

    i = m.end()  # 여는 따옴표 다음 위치
    chars = []
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            # 이스케이프 시퀀스 처리
            nxt = body[i + 1]
            if nxt == "n":
                chars.append("\n")
            elif nxt == "t":
                chars.append("\t")
            elif nxt == "r":
                chars.append("\r")
            elif nxt == '"':
                chars.append('"')
            elif nxt == "\\":
                chars.append("\\")
            else:
                chars.append(nxt)
            i += 2
            continue
        if c == '"':
            # 닫는 따옴표 발견
            return "".join(chars)
        chars.append(c)
        i += 1
    return None  # 닫는 따옴표를 못 찾음


def parse_tres(path: Path, fields: list[str]) -> dict | None:
    """
    한 개의 .tres 파일에서 지정한 필드 값들을 dict로 반환.
    파일이 리소스가 아니거나 필드가 하나도 추출되지 않으면 None.

    주의: 현재는 [resource] 블록만 파싱한다. [sub_resource] 블록 안의 문자열은
    추출되지 않으며, 발견 시 경고 로그만 출력한다.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"[WARN] 읽기 실패: {path} ({e})", file=sys.stderr)
        return None

    sub_count = _count_sub_resources(text)
    if sub_count > 0:
        print(
            f"[WARN] {path.name}: [sub_resource] {sub_count}개 발견 — 현재 파서는 [resource] 블록만 처리하므로 이 내용은 스킵됩니다.",
            file=sys.stderr,
        )

    body_start, body_end = _find_resource_block(text)
    if body_start < 0:
        return None
    body = text[body_start:body_end]

    result: dict = {}
    found_any = False
    for field in fields:
        val = _extract_string_field(body, field)
        if val is not None and val != "":
            result[field] = val
            found_any = True
    return result if found_any else None


# ==========================================
# 추출 로직
# ==========================================

def _collect_tres_files(target_path: Path) -> list[Path]:
    """target이 파일이면 [파일], 디렉토리면 재귀 *.tres 리스트."""
    if target_path.is_file():
        if target_path.suffix == ".tres":
            return [target_path]
        return []
    if target_path.is_dir():
        return sorted(target_path.rglob("*.tres"))
    return []


def collect_target_files(
    pck_root: Path,
    dir_rel: str,
    targets: list[str],
) -> list[Path]:
    """
    한 그룹의 targets를 풀어 처리 대상 .tres 파일 경로 리스트 반환.
    """
    base = (pck_root / dir_rel).resolve() if dir_rel else pck_root
    out: list[Path] = []
    for target in targets:
        target_path = (base / target).resolve() if target else base
        if not target_path.exists():
            print(
                f"[WARN] target 경로 없음: {target_path} "
                f"(dir={dir_rel!r}, target={target!r})",
                file=sys.stderr,
            )
            continue
        tres_files = _collect_tres_files(target_path)
        if not tres_files:
            print(
                f"[WARN] .tres 파일 없음: {target_path}",
                file=sys.stderr,
            )
            continue
        out.extend(tres_files)
    return out


def tres_to_rows(
    tres_path: Path,
    fields: list[str],
    pck_root: Path,
) -> list[dict]:
    """
    한 개의 .tres 파일에서 행을 추출. 파일에 지정 필드가 하나도 없으면 빈 리스트.

    각 행은 tscn 추출 도구와 동일한 8컬럼 구조로 반환된다.
    .tres 는 Godot 노드 계층이 없으므로:
      - filename  = 확장자 없는 상대 경로
      - filetype  = "tres"
      - location  = "" (비움, 전역 text 매칭 기본)
      - parent    = ""
      - name      = ""
      - type      = ""
      - unique_id = ""
      - property  = tres 필드명 (예: "description")
      - text      = 필드 값
    """
    parsed = parse_tres(tres_path, fields)
    if parsed is None:
        return []

    try:
        rel = tres_path.resolve().relative_to(pck_root)
        filename = rel.with_suffix("").as_posix()
    except ValueError:
        filename = str(tres_path.resolve())

    rows: list[dict] = []
    for field in fields:
        if field not in parsed:
            continue
        rows.append({
            "filename": filename,
            "filetype": "tres",
            "location": "",
            "parent": "",
            "name": "",
            "type": "",
            "unique_id": "",
            "property": field,
            "text": parsed[field],
        })
    return rows


def write_tsv(out_path: Path, rows: list[dict]) -> None:
    """행 리스트를 TSV로 원자적 쓰기."""
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
# 배치 모드 (tres_list.json)
# ==========================================

def run_batch(
    config_path: Path,
    pck_root: Path,
    output_dir: Path,
) -> int:
    """tres_list.json 의 각 그룹을 실행. 반환: 에러 코드."""
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 파싱 실패: {config_path} ({e})", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"[ERROR] config 읽기 실패: {config_path} ({e})", file=sys.stderr)
        return 1

    groups = config.get("groups")
    if not isinstance(groups, list) or not groups:
        print(f"[ERROR] config에 'groups' 배열이 없습니다: {config_path}", file=sys.stderr)
        return 1

    # 기본 무결성 체크 (name은 선택사항)
    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            print(f"[ERROR] groups[{i}] 가 object가 아닙니다", file=sys.stderr)
            return 1
        for required in ("dir", "fields", "targets"):
            if required not in g:
                print(f"[ERROR] groups[{i}] 에 '{required}' 누락", file=sys.stderr)
                return 1
        if not isinstance(g["fields"], list) or not g["fields"]:
            print(f"[ERROR] groups[{i}].fields 가 비어있거나 배열이 아님", file=sys.stderr)
            return 1
        if not isinstance(g["targets"], list) or not g["targets"]:
            print(f"[ERROR] groups[{i}].targets 가 비어있거나 배열이 아님", file=sys.stderr)
            return 1

    print(f"config: {config_path}")
    print(f"pck_root: {pck_root}")
    print(f"출력: {output_dir}")
    print(f"그룹 수: {len(groups)}")
    print()

    total_files_written = 0
    total_rows = 0
    for idx, g in enumerate(groups, start=1):
        name = g.get("name", f"group {idx}")
        dir_rel = g["dir"]
        fields = g["fields"]
        targets = g["targets"]

        print(f"[{idx}/{len(groups)}] {name}")
        print(f"    dir:     {dir_rel}")
        print(f"    targets: {targets}")
        print(f"    fields:  {fields}")

        tres_files = collect_target_files(pck_root, dir_rel, targets)
        group_rows = 0
        group_files = 0
        joined_rows: list[dict] = []
        for tres in tres_files:
            rows = tres_to_rows(tres, fields, pck_root)
            if not rows:
                continue
            try:
                rel = tres.resolve().relative_to(pck_root)
            except ValueError:
                print(f"[WARN] pck_root 밖의 파일 스킵: {tres}", file=sys.stderr)
                continue
            out_path = output_dir / (rel.as_posix() + ".tsv")
            write_tsv(out_path, rows)
            joined_rows.extend(rows)
            group_rows += len(rows)
            group_files += 1

        # join 필드가 지정되면 그룹 전체를 합본 TSV 로 추가 출력
        join_name = g.get("join")
        if join_name and joined_rows:
            join_path = output_dir / dir_rel / f"{join_name}.tres.joined.tsv"
            write_tsv(join_path, joined_rows)
            print(f"    → {group_files}개 파일, {group_rows}개 엔트리")
            print(f"    → 합본: {join_path.relative_to(output_dir)}")
        else:
            print(f"    → {group_files}개 파일, {group_rows}개 엔트리")
        print()
        total_files_written += group_files
        total_rows += group_rows

    print("=" * 60)
    print(f"완료: {len(groups)}개 그룹, {total_files_written}개 TSV 파일, {total_rows}개 엔트리")
    return 0


# ==========================================
# 단일 job 모드 (--input / --fields)
# ==========================================

def run_single_job(
    input_dir: Path,
    fields: list[str],
    pck_root: Path,
    output_dir: Path,
) -> int:
    """
    단일 디렉토리에서 필드 추출.
    각 .tres 파일마다 미러링된 경로로 .tres.tsv 생성.
    """
    if not input_dir.exists():
        print(f"[ERROR] 입력 경로가 없습니다: {input_dir}", file=sys.stderr)
        return 1
    if not input_dir.is_dir():
        print(f"[ERROR] 디렉토리가 아닙니다: {input_dir}", file=sys.stderr)
        return 1
    if not fields:
        print("[ERROR] --fields 가 비어있습니다.", file=sys.stderr)
        return 1

    tres_files = sorted(input_dir.rglob("*.tres"))
    if not tres_files:
        print(f"[ERROR] .tres 파일이 없습니다: {input_dir}", file=sys.stderr)
        return 1

    files_written = 0
    total_rows = 0
    for tres in tres_files:
        rows = tres_to_rows(tres, fields, pck_root)
        if not rows:
            continue
        try:
            rel = tres.resolve().relative_to(pck_root)
        except ValueError:
            print(f"[WARN] pck_root 밖의 파일 스킵: {tres}", file=sys.stderr)
            continue
        out_path = output_dir / (rel.as_posix() + ".tsv")
        write_tsv(out_path, rows)
        files_written += 1
        total_rows += len(rows)

    print(f"\n완료: {files_written}개 TSV 파일, {total_rows}개 엔트리")
    print(f"출력: {output_dir}")
    return 0


# ==========================================
# 엔트리 포인트
# ==========================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description=".tres 파일에서 필드 값 추출",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--config", help=f"tres_list.json 경로 (기본: tools/{DEFAULT_CONFIG_NAME})")
    parser.add_argument("--input", help="단일 job 모드: 대상 디렉토리 (하위 재귀)")
    parser.add_argument("--fields", help="단일 job 모드: 추출할 필드 (콤마 구분)")
    args = parser.parse_args()

    # 경로 기준
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent              # mods/Trans To Vostok
    pck_root = (mod_root / ".tmp" / "pck_recovered").resolve()
    parsed_dir = (mod_root / ".tmp" / "parsed_text").resolve()

    # --input 과 --config 동시 지정 금지
    if args.input and args.config:
        print("[ERROR] --input 과 --config 는 함께 사용할 수 없습니다.", file=sys.stderr)
        return 1

    # 단일 job 모드
    if args.input:
        if not args.fields:
            print("[ERROR] --input 사용 시 --fields 도 지정해야 합니다.", file=sys.stderr)
            return 1
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        input_dir = Path(args.input).resolve()
        return run_single_job(input_dir, fields, pck_root, parsed_dir)

    # 배치 모드
    if args.config:
        config_path = Path(args.config).resolve()
    else:
        config_path = (script_dir / DEFAULT_CONFIG_NAME).resolve()

    if not config_path.exists():
        print(f"[ERROR] config 파일이 없습니다: {config_path}", file=sys.stderr)
        print("  --config 로 경로를 지정하거나 --input / --fields 로 단일 job을 실행하세요.",
              file=sys.stderr)
        return 1

    if not pck_root.exists():
        print(f"[ERROR] pck_root가 없습니다: {pck_root}", file=sys.stderr)
        print("  먼저 decompile_gdc.bat 를 실행하여 pck_recovered 를 생성하세요.", file=sys.stderr)
        return 1

    return run_batch(config_path, pck_root, parsed_dir)


if __name__ == "__main__":
    sys.exit(main())
