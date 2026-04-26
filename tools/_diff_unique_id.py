"""
[Temporary] Compare *.tscn.tsv files in two parsed_text directories to find unique_id changes.

Usage:
    python _diff_unique_id.py <old_dir> <new_dir>

Comparison key: (filename, parent, name, type, text)
Reports cases where same key has different unique_id.
"""
import csv
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass


def load_index(tsv_dir: Path) -> dict:
    """{(filename, parent, name, type, text): unique_id}"""
    idx = {}
    for tsv in sorted(tsv_dir.rglob("*.tscn.tsv")):
        with open(tsv, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                key = (
                    row.get("filename", ""),
                    row.get("parent", ""),
                    row.get("name", ""),
                    row.get("type", ""),
                    row.get("text", ""),
                )
                uid = row.get("unique_id", "")
                if uid:
                    idx[key] = uid
    return idx


def main() -> int:
    if len(sys.argv) < 3:
        print("사용법: python _diff_unique_id.py <old_dir> <new_dir>")
        return 1

    old_dir = Path(sys.argv[1]).resolve()
    new_dir = Path(sys.argv[2]).resolve()

    if not old_dir.exists():
        print(f"[ERROR] 옛 디렉토리 없음: {old_dir}")
        return 1
    if not new_dir.exists():
        print(f"[ERROR] 새 디렉토리 없음: {new_dir}")
        return 1

    print(f"옛: {old_dir}")
    print(f"새: {new_dir}")
    print()

    old_idx = load_index(old_dir)
    new_idx = load_index(new_dir)
    print(f"옛 엔트리: {len(old_idx)}")
    print(f"새 엔트리: {len(new_idx)}")
    print()

    same = 0
    changed: list = []       # unique_id changed
    only_old: list = []      # removed
    only_new: list = []      # added

    all_keys = set(old_idx.keys()) | set(new_idx.keys())
    for key in all_keys:
        old_uid = old_idx.get(key)
        new_uid = new_idx.get(key)
        if old_uid and new_uid:
            if old_uid == new_uid:
                same += 1
            else:
                changed.append((key, old_uid, new_uid))
        elif old_uid:
            only_old.append((key, old_uid))
        else:
            only_new.append((key, new_uid))

    print("=" * 80)
    print(f"동일 unique_id 유지:  {same}")
    print(f"unique_id 변경:       {len(changed)}")
    print(f"옛에만 존재 (제거):   {len(only_old)}")
    print(f"새에만 존재 (추가):   {len(only_new)}")
    print("=" * 80)

    if changed:
        print()
        print("[unique_id 변경] — xlsx 의 unique_id 업데이트 필요")
        print("-" * 80)
        for (filename, parent, name, type_, text), old_uid, new_uid in changed:
            preview = text.replace("\n", "\\n")
            if len(preview) > 40:
                preview = preview[:40] + "..."
            print(f"  {filename}")
            print(f"    parent={parent!r} name={name!r} type={type_!r}")
            print(f"    text={preview!r}")
            print(f"    uid: {old_uid}  →  {new_uid}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
