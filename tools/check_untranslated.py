"""
Compare extracted TSV with Translation.xlsx and report translation coverage.

Match classification:
- direct:      xlsx static or scoped literal row matched by 5-tuple (translation complete)
- literal:     xlsx global literal row matched by text (fallback translation)
- expression:  xlsx global pattern row regex matched text (fallback translation)
- ignored:     present in xlsx with method=ignore (operational exclusion)
- untranslatable: present in xlsx with untranslatable=1 (untranslatable text)
- empty:       present in xlsx but translation is empty (awaiting translation)
- missing:     not present in xlsx at all (needs to be added)

Usage:
    python check_untranslated.py <locale>

Example:
    python check_untranslated.py Korean

Output:
    screen + <locale>/.log/check_untranslated_YYYYMMDD_HHMMSS.log
"""
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import openpyxl  # noqa: F401
except ImportError:
    print("ERROR: openpyxl이 필요합니다. pip install openpyxl", file=sys.stderr)
    sys.exit(1)

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_translation import (
    _preview,
    _effective_method,
    load_all_translation_sheets,
    load_metadata,
    format_metadata_lines,
    Tee,
)


BOOL_TRUE = {"1", "true"}


# ==========================================
# pattern compilation (same logic as translator.gd)
# ==========================================

def compile_pattern(text: str) -> re.Pattern:
    """Compile pattern supporting {name} and * into a Python regex."""
    placeholder_re = re.compile(r"\{(\w+)\}")
    result = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == "{":
            m = placeholder_re.match(text, i)
            if m:
                name = m.group(1)
                result.append(f"(?P<{name}>.+?)")
                i = m.end()
                continue
        if c == "*":
            result.append("(?:.+?)")
            i += 1
            continue
        if c in r"\.^$+?()[]|{}":
            result.append("\\" + c)
        else:
            result.append(c)
        i += 1
    return re.compile("^" + "".join(result) + "$")


# ==========================================
# load extracted TSV
# ==========================================

def load_tsv_entries(tsv_dir: Path) -> list[dict]:
    """
    Load double-extension TSV files from parsed_text/.

    Targets:
        *.tscn.tsv  — scn entries with unique_id
        *.tres.tsv  — tres entries without unique_id
        *.gd.tsv    — gd script literals/patterns
    """
    entries = []
    tsv_files = (sorted(tsv_dir.rglob("*.tscn.tsv"))
                 + sorted(tsv_dir.rglob("*.tres.tsv"))
                 + sorted(tsv_dir.rglob("*.gd.tsv")))
    for tsv_file in tsv_files:
        try:
            with open(tsv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    text = row.get("text") or ""
                    if not text:
                        continue
                    filetype = (row.get("filetype") or "").strip()
                    uid = (row.get("unique_id") or "").strip()
                    # tscn entries require uid; tres allows missing uid
                    if filetype == "tscn" and not uid:
                        continue
                    entries.append({
                        "unique_id": uid,
                        "filename": (row.get("filename") or "").strip(),
                        "filetype": filetype,
                        "location": (row.get("location") or "").strip(),
                        "parent": (row.get("parent") or "").strip(),
                        "name": (row.get("name") or "").strip(),
                        "type": (row.get("type") or "").strip(),
                        "property": (row.get("property") or "").strip(),
                        "text": text,
                        "_tsv_file": tsv_file.name,
                    })
        except Exception as e:
            print(f"[WARN] TSV 읽기 실패: {tsv_file} ({e})")
    return entries


# ==========================================
# xlsx analysis (new schema: method / translation)
# ==========================================

def analyze_xlsx(rows: list[dict]) -> tuple[dict, set, set, set, dict, dict, list, list]:
    """
    Index xlsx rows against the runtime matching model.

    Returns:
      - direct_keys:         { 5-tuple: translation } — static + scoped literal (tscn)
      - ignored_keys:        set of 5-tuples (method=ignore)
      - untranslatable_keys: set of 5-tuples (untranslatable=1)
      - empty_keys:          set of 5-tuples (empty translation)
      - literal_map:         {text: translation} — global literal
      - tres_direct:         { (filename, filetype, text): translation } — tres direct match
      - pattern_list:        [(compiled_regex, template), ...] — global pattern
      - ignore_rows:         [row, ...] — original method=ignore rows (for coverage check)
    """
    direct_keys: dict = {}
    ignored_keys: set = set()
    untranslatable_keys: set = set()
    tres_ignored: set = set()
    tres_untranslatable: set = set()
    empty_keys: set = set()
    literal_map: dict = {}
    tres_direct: dict = {}
    pattern_list: list = []
    ignore_rows: list = []

    for row in rows:
        translation = row.get("translation", "")
        text = row.get("text", "")
        location = row.get("location", "").strip()
        parent = row.get("parent", "").strip()
        name = row.get("name", "").strip()
        type_ = row.get("type", "").strip()
        effective = _effective_method(row)
        untranslatable = row.get("untranslatable", "").strip().lower() in BOOL_TRUE

        key_5 = (location, parent, name, type_, text)

        if effective == "ignore":
            if location:
                ignored_keys.add(key_5)
            fn = row.get("filename", "").strip()
            ft = row.get("filetype", "").strip()
            if fn and ft:
                if untranslatable:
                    tres_untranslatable.add((fn, ft, text))
                else:
                    tres_ignored.add((fn, ft, text))
            if not untranslatable:
                ignore_rows.append(row)
            continue

        if untranslatable:
            if effective in ("static",) or (effective == "literal" and location):
                untranslatable_keys.add(key_5)
            fn = row.get("filename", "").strip()
            ft = row.get("filetype", "").strip()
            if fn and ft:
                tres_untranslatable.add((fn, ft, text))
            continue

        if effective == "static":
            if translation:
                direct_keys[key_5] = translation
            else:
                empty_keys.add(key_5)

        elif effective == "literal":
            if location:
                # scoped literal — direct key space
                if translation:
                    direct_keys[key_5] = translation
                else:
                    empty_keys.add(key_5)
            else:
                # global literal
                if translation:
                    literal_map[text] = translation
                # tres direct match: register by (filename, filetype, text) key
                fn = row.get("filename", "").strip()
                ft = row.get("filetype", "").strip()
                if fn and ft:
                    tres_key = (fn, ft, text)
                    if translation:
                        tres_direct[tres_key] = translation

        elif effective == "pattern":
            if location:
                # scoped pattern is currently treated the same as global pattern in the report model
                if translation:
                    try:
                        regex = compile_pattern(text)
                        pattern_list.append((regex, translation))
                    except re.error:
                        pass
            else:
                if translation:
                    try:
                        regex = compile_pattern(text)
                        pattern_list.append((regex, translation))
                    except re.error:
                        pass
                # if filename/filetype is set, also register the raw pattern text in tres_direct
                # → classify treats exact pattern text as "direct"
                fn = row.get("filename", "").strip()
                ft = row.get("filetype", "").strip()
                if fn and ft and translation:
                    tres_direct[(fn, ft, text)] = translation

        elif effective == "substr":
            # substr → register in both literal_map and tres_direct (same as build)
            if translation:
                literal_map[text] = translation
                fn = row.get("filename", "").strip()
                ft = row.get("filetype", "").strip()
                if fn and ft:
                    tres_direct[(fn, ft, text)] = translation

    return direct_keys, ignored_keys, untranslatable_keys, tres_ignored, tres_untranslatable, empty_keys, literal_map, tres_direct, pattern_list, ignore_rows


# ==========================================
# classify TSV entries
# ==========================================

def _check_fallback(text: str, literal_map: dict, pattern_list: list) -> tuple[str, str] | None:
    """Check global literal/pattern fallback match. Returns (status, method) on hit, None on miss."""
    if text in literal_map:
        return ("literal", "literal")
    for regex, _tmpl in pattern_list:
        if regex.match(text):
            return ("expression", f"pattern: {regex.pattern}")
    return None


def classify_entry(
    entry: dict,
    direct_keys: dict,
    ignored_keys: set,
    untranslatable_keys: set,
    tres_ignored: set,
    tres_untranslatable: set,
    empty_keys: set,
    literal_map: dict,
    tres_direct: dict,
    pattern_list: list,
) -> tuple[str, str]:
    """
    Classify the translation status of a TSV entry.
    Returns: (status, method)
        status: "direct" | "ignored" | "delegated" | "untranslatable" | "literal" | "expression" | "empty" | "missing"

    delegated: row was treated as ignore/untranslatable in xlsx, but a global literal/pattern catches it.
               Since it is actually translated at runtime, must be distinguished from ignored/untranslatable.
    """
    text = entry["text"]
    filetype = entry.get("filetype", "")

    # tscn entries are first looked up by 5-tuple
    if filetype == "tscn":
        key_5 = (
            entry["location"],
            entry["parent"],
            entry["name"],
            entry["type"],
            text,
        )
        if key_5 in ignored_keys:
            fb = _check_fallback(text, literal_map, pattern_list)
            if fb:
                return ("delegated", fb[1])
            return ("ignored", "")
        if key_5 in untranslatable_keys:
            fb = _check_fallback(text, literal_map, pattern_list)
            if fb:
                return ("delegated", fb[1])
            return ("untranslatable", "")
        if key_5 in direct_keys:
            return ("direct", "")
        if key_5 in empty_keys:
            return ("empty", "")
        # check whether tscn + substr/pattern was registered in tres_direct
        tscn_src_key = (entry.get("filename", ""), "tscn", text)
        if tscn_src_key in tres_direct:
            return ("direct", "")

    # tres / gd entries match on (filename, filetype, text)
    if filetype in ("tres", "gd"):
        src_key = (entry.get("filename", ""), filetype, text)
        if src_key in tres_ignored:
            fb = _check_fallback(text, literal_map, pattern_list)
            if fb:
                return ("delegated", fb[1])
            return ("ignored", "")
        if src_key in tres_untranslatable:
            fb = _check_fallback(text, literal_map, pattern_list)
            if fb:
                return ("delegated", fb[1])
            return ("untranslatable", "")
        if src_key in tres_direct:
            return ("direct", "")

    # text-only fallback (tscn/tres/gd miss)
    fb = _check_fallback(text, literal_map, pattern_list)
    if fb:
        return fb

    return ("missing", "")


# ==========================================
# main
# ==========================================

def format_percent(n: int, total: int) -> str:
    if total == 0:
        return "-"
    return f"{n / total * 100:.1f}%"


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: python check_untranslated.py <locale>")
        print("예: python check_untranslated.py Korean")
        return 1

    locale = sys.argv[1]
    script_dir = Path(__file__).resolve().parent
    mod_root = script_dir.parent
    pkg_root = mod_root / "Trans To Vostok"
    locale_dir = pkg_root / locale
    xlsx_path = locale_dir / "Translation.xlsx"
    tsv_dir = mod_root / ".tmp" / "parsed_text"

    if not xlsx_path.exists():
        print(f"[ERROR] xlsx 파일이 없습니다: {xlsx_path}")
        return 1
    if not tsv_dir.exists():
        print(f"[ERROR] TSV 디렉토리가 없습니다: {tsv_dir}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = locale_dir / ".log" / f"check_untranslated_{timestamp}.log"
    tee = Tee(log_path)

    try:
        tee.print(f"xlsx:   {xlsx_path}")
        tee.print(f"TSV:    {tsv_dir}")
        tee.print(f"로그:   {log_path}")
        tee.print(f"실행:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        meta = load_metadata(xlsx_path)
        for line in format_metadata_lines(meta):
            tee.print(line)
        tee.print()

        # 1. load xlsx and analyze (merge all translation sheets)
        tee.print("xlsx 로드 중...")
        sheets = load_all_translation_sheets(xlsx_path)
        all_rows: list[dict] = []
        for sheet_name, _header, rows in sheets:
            all_rows.extend(rows)
        tee.print(f"  시트 {len(sheets)}개, 총 {len(all_rows)}행")

        (
            direct_keys,
            ignored_keys,
            untranslatable_keys,
            tres_ignored,
            tres_untranslatable,
            empty_keys,
            literal_map,
            tres_direct,
            pattern_list,
            ignore_rows,
        ) = analyze_xlsx(all_rows)

        scoped_count = sum(1 for k in direct_keys if k[0])
        tee.print(
            f"  → direct {len(direct_keys)}개 (scoped {scoped_count}), "
            f"tres_direct {len(tres_direct)}개, "
            f"ignored {len(ignored_keys)}+{len(tres_ignored)}개, "
            f"untranslatable {len(untranslatable_keys)}+{len(tres_untranslatable)}개, "
            f"empty {len(empty_keys)}개, "
            f"literal {len(literal_map)}개, "
            f"pattern {len(pattern_list)}개"
        )
        tee.print()

        # 2. load extracted TSV
        tee.print("추출 TSV 로드 중...")
        tsv_entries = load_tsv_entries(tsv_dir)
        tee.print(f"  {len(tsv_entries)}개 엔트리")
        tee.print()

        # 3. classify
        per_file: dict = defaultdict(lambda: {
            "total": 0,
            "direct": 0,
            "literal": 0,
            "expression": 0,
            "delegated": 0,
            "ignored": 0,
            "untranslatable": 0,
            "empty": 0,
            "missing": 0,
            "empty_entries": [],
            "missing_entries": [],
            "fallback_entries": [],
            "delegated_entries": [],
        })

        for entry in tsv_entries:
            fname = entry["_tsv_file"]
            status, method = classify_entry(
                entry, direct_keys, ignored_keys, untranslatable_keys,
                tres_ignored, tres_untranslatable, empty_keys,
                literal_map, tres_direct, pattern_list,
            )
            bucket = per_file[fname]
            bucket["total"] += 1
            if status == "direct":
                bucket["direct"] += 1
            elif status == "literal":
                bucket["literal"] += 1
                bucket["fallback_entries"].append((entry, method))
            elif status == "expression":
                bucket["expression"] += 1
                bucket["fallback_entries"].append((entry, method))
            elif status == "delegated":
                bucket["delegated"] += 1
                bucket["delegated_entries"].append((entry, method))
            elif status == "ignored":
                bucket["ignored"] += 1
            elif status == "untranslatable":
                bucket["untranslatable"] += 1
            elif status == "empty":
                bucket["empty"] += 1
                bucket["empty_entries"].append(entry)
            else:
                bucket["missing"] += 1
                bucket["missing_entries"].append(entry)

        # 4. per-file summary (split tscn / tres)
        tscn_files = sorted(f for f in per_file if f.endswith(".tscn.tsv"))
        tres_files = sorted(f for f in per_file if f.endswith(".tres.tsv"))

        total_all = 0
        effective_all = 0
        direct_all = 0
        fallback_all = 0
        delegated_all = 0
        ignored_all = 0
        untranslatable_all = 0
        empty_all = 0
        missing_all = 0

        def _print_file_group(label: str, file_names: list):
            nonlocal total_all, effective_all, direct_all, fallback_all, delegated_all
            nonlocal ignored_all, untranslatable_all, empty_all, missing_all

            if not file_names:
                return
            tee.print("=" * 80)
            tee.print(f"{label} (ignored/untranslatable 제외 유효 엔트리 기준)")
            tee.print("=" * 80)

            max_fname = max((len(n) for n in file_names), default=20)
            for fname in file_names:
                b = per_file[fname]
                total = b["total"]
                direct = b["direct"]
                fallback = b["literal"] + b["expression"]
                delegated = b["delegated"]
                ignored = b["ignored"]
                untranslatable = b["untranslatable"]
                empty = b["empty"]
                missing = b["missing"]

                excluded = ignored + untranslatable
                effective = total - excluded
                translation_count = direct + fallback + delegated

                total_all += total
                effective_all += effective
                direct_all += direct
                fallback_all += fallback
                delegated_all += delegated
                ignored_all += ignored
                untranslatable_all += untranslatable
                empty_all += empty
                missing_all += missing

                covered = translation_count + ignored + untranslatable
                matched = direct + delegated + ignored + untranslatable + empty
                tee.print(
                    f"[{fname:<{max_fname}}] "
                    f"매치 {matched}/{total} ({format_percent(matched, total)}), "
                    f"번역 {covered}/{total} ({format_percent(covered, total)}), "
                    f"직접 {direct}/{total} ({format_percent(direct, total)}), "
                    f"fallback {fallback}, delegated {delegated}, "
                    f"ignored {ignored}, untranslatable {untranslatable}, "
                    f"empty {empty}, missing {missing}"
                )
            tee.print()

        gd_files = sorted(f for f in per_file if f.endswith(".gd.tsv"))

        _print_file_group("tscn 파일별 요약", tscn_files)
        _print_file_group("tres 파일별 요약", tres_files)
        _print_file_group("gd 파일별 요약", gd_files)

        covered_all = direct_all + fallback_all + delegated_all + ignored_all + untranslatable_all
        matched_all = direct_all + delegated_all + ignored_all + untranslatable_all + empty_all
        tee.print(
            f"[전체] "
            f"매치 {matched_all}/{total_all} ({format_percent(matched_all, total_all)}), "
            f"번역 {covered_all}/{total_all} ({format_percent(covered_all, total_all)}), "
            f"직접 {direct_all}/{total_all} ({format_percent(direct_all, total_all)}), "
            f"fallback {fallback_all}, delegated {delegated_all}, "
            f"ignored {ignored_all}, untranslatable {untranslatable_all}, "
            f"empty {empty_all}, missing {missing_all}"
        )
        tee.print()

        # 5. per-file detail (split tscn / tres)
        def _print_detail_group(label: str, file_list: list):
            has_any = False
            for fname in file_list:
                b = per_file[fname]
                if b["missing"] > 0 or b["empty"] > 0 or len(b["fallback_entries"]) > 0:
                    has_any = True
                    break
            if not has_any:
                return
            tee.print("=" * 80)
            tee.print(f"{label} 상세")
            tee.print("=" * 80)
            for fname in file_list:
                _print_file_detail(fname)

        def _print_file_detail(fname: str):
            b = per_file[fname]
            if (
                b["missing"] == 0
                and b["empty"] == 0
                and len(b["fallback_entries"]) == 0
            ):
                return
            tee.print()
            tee.print(f"[{fname}]")

            if b["missing_entries"]:
                tee.print(f"  missing - xlsx에 없음 ({b['missing']}개):")
                for e in b["missing_entries"]:
                    tee.print(
                        f"    uid={e['unique_id']}  "
                        f"name={e['name']}  "
                        f"type={e['type']}  "
                        f"property={e.get('property', '')}  "
                        f"text={_preview(e['text'], 50)}"
                    )

            if b["empty_entries"]:
                tee.print(f"  empty - xlsx에 있지만 미번역 ({b['empty']}개):")
                for e in b["empty_entries"]:
                    tee.print(
                        f"    uid={e['unique_id']}  "
                        f"name={e['name']}  "
                        f"type={e['type']}  "
                        f"property={e.get('property', '')}  "
                        f"text={_preview(e['text'], 50)}"
                    )

            if b["fallback_entries"]:
                tee.print(
                    f"  fallback - literal/pattern 으로 매칭 "
                    f"({len(b['fallback_entries'])}개):"
                )
                for e, method in b["fallback_entries"]:
                    tee.print(
                        f"    uid={e['unique_id']}  "
                        f"name={e['name']}  "
                        f"property={e.get('property', '')}  "
                        f"text={_preview(e['text'], 50)}  "
                        f"← {method}"
                    )

        _print_detail_group("tscn", tscn_files)
        _print_detail_group("tres", tres_files)
        _print_detail_group("gd", gd_files)

        # write delegated log to a separate file (no detail on screen)
        delegated_log_path = locale_dir / ".log" / f"check_delegated_{timestamp}.log"
        has_delegated = any(
            len(per_file[f]["delegated_entries"]) > 0 for f in per_file
        )
        if has_delegated:
            delegated_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(delegated_log_path, "w", encoding="utf-8") as df:
                df.write("delegated 상세 — ignore/untranslatable 이지만 전역 매칭됨\n")
                df.write(f"실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for fname in sorted(per_file.keys()):
                    b = per_file[fname]
                    if not b["delegated_entries"]:
                        continue
                    df.write(f"[{fname}]\n")
                    for e, method in b["delegated_entries"]:
                        df.write(
                            f"  uid={e['unique_id']}  "
                            f"name={e['name']}  "
                            f"property={e.get('property', '')}  "
                            f"text={_preview(e['text'], 50)}  "
                            f"← {method}\n"
                        )
                df.write(f"\n총 {delegated_all}개\n")
            tee.print(f"delegated 로그: {delegated_log_path}")
        else:
            tee.print("delegated: 없음")

        # 6. suspicious ignore check
        # rows with method=ignore + untranslatable≠1 that are not covered by any other row
        covered_texts: set = set()
        for key_5, _trans in direct_keys.items():
            covered_texts.add(key_5[4])  # text part
        covered_texts.update(literal_map.keys())

        suspicious: list = []
        for row in ignore_rows:
            text = row.get("text", "")
            if not text:
                continue
            if text in covered_texts:
                continue
            # check pattern match
            pattern_hit = False
            for regex, _tmpl in pattern_list:
                if regex.match(text):
                    pattern_hit = True
                    break
            if pattern_hit:
                continue
            suspicious.append(row)

        if suspicious:
            tee.print()
            tee.print("=" * 80)
            tee.print(
                f"ignore 검토 — method=ignore 이지만 다른 행에서 커버되지 않음 "
                f"({len(suspicious)}개):"
            )
            tee.print("=" * 80)
            for row in suspicious:
                tee.print(
                    f"  filename={row.get('filename', '')!r}  "
                    f"text={_preview(row.get('text', ''), 50)}"
                )

        tee.print()
        tee.print("=" * 80)
        tee.print(
            f"완료: 전체 {total_all}개 중 "
            f"ignored {ignored_all} + untranslatable {untranslatable_all} 제외 "
            f"유효 {effective_all}개, "
            f"번역 {direct_all + fallback_all} "
            f"({format_percent(direct_all + fallback_all, effective_all)}), "
            f"empty {empty_all}, missing {missing_all}"
        )
        if suspicious:
            tee.print(f"경고: 커버되지 않는 ignore 행: {len(suspicious)}개 (위 목록 확인)")

        return 0
    finally:
        tee.close()


if __name__ == "__main__":
    sys.exit(main())
