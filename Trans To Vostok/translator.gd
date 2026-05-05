# Trans To Vostok - 런타임 번역 엔진 (8층 fallback 체인)
#
# 데이터 파일 (build_runtime_tsv.py 가 생성, <locale>/runtime_tsv/ 아래):
#   translation_static.tsv           — static        (5필드 + text + translation)
#   translation_literal_scoped.tsv   — scoped literal (5필드 + text + translation)
#   translation_pattern_scoped.tsv   — scoped pattern (5필드 + text + translation)
#   translation_literal.tsv          — global literal (text + translation)
#   translation_pattern.tsv          — global pattern (text + translation)
#
# 매칭 우선순위 (첫 히트에서 종료):
#   1. static exact          — (location, parent, name, type, text) 완전 일치
#   2. scoped literal exact  — 동일 구조, 동적 텍스트
#   3. scoped pattern exact  — 컨텍스트 완전 일치 + 정규식 매칭
#   4. literal global        — text 완전 일치 (컨텍스트 무시)
#   5. pattern global        — 정규식 매칭 (컨텍스트 무시)
#   6. static score          — 부분 컨텍스트 매칭 (+8/+4/+2/+1)
#   7. scoped literal score  — 동적 텍스트 부분 컨텍스트 매칭
#   8. scoped pattern score  — 정규식 + 부분 컨텍스트
#
# score 계산: location(+8), parent(+4), name(+2), type(+1)
# score 동률은 첫 발견 우선 + push_warning 경고.
#
# 런타임 구조 (DIO-KAMI 패턴 참고):
#   - 바인딩 테이블: 관심 노드만 등록, 트리 재순회 없음
#   - last 값 비교: 변경 없으면 조회 전부 스킵
#   - 결과/음성 캐시: 같은 (컨텍스트, text) 조합은 평생 1회만 매칭
#   - Priority (_process, 매 프레임) / Normal (타이머 배치) 분리

extends Node

# ==========================================
# 설정
# ==========================================

var _locale: String = "Korean"
var _compatible_mode: bool = false
var _initialized: bool = false
const DATA_BASE: String = "res://Trans To Vostok"

const SCORE_LOCATION: int = 8
const SCORE_PARENT: int = 4
const SCORE_NAME: int = 2
const SCORE_TYPE: int = 1

const TRANSLATABLE_PROPS: Array = ["text", "placeholder_text", "tooltip_text", "containerName"]

const PRIORITY_NAME_KEYWORDS: Array = ["interact", "tooltip", "hint", "container", "corpse"]

# 추가 whitelist 프리셋 — translator_ui 가 enabled_whitelist 로 on/off 전달.
# key = 노드 경로 키워드 (to_lower 후 비교). 값은 UI 표시용 메타데이터.
# 기본값은 모두 OFF — 사용자가 필요할 때만 on.
const WHITELIST_PRESETS: Dictionary = {
	"hud/info": {
		"nickname": "HUD Info Area (Broad)",
		"description": "Entire HUD info area (map + FPS etc.)",
		"mod_list": [],
		"default": false,
	},
	"hud/info/map": {
		"nickname": "HUD Map Label",
		"description": "Top-left HUD map name label",
		"mod_list": ["ImmersiveXP (v3.0.3)"],
		"default": false,
	},
	"interface/context": {
		"nickname": "Context Menu (Right-click)",
		"description": "Right-click menu on inventory (Use/Drop/Take etc.)",
		"mod_list": [],
		"default": false,
	},
	"interface/container": {
		"nickname": "Container UI",
		"description": "Container window",
		"mod_list": [],
		"default": false,
	},
	"interface/inventory": {
		"nickname": "Inventory UI",
		"description": "Inventory window",
		"mod_list": [],
		"default": false,
	},
	"interface/equipment": {
		"nickname": "Equipment UI",
		"description": "Equipment window",
		"mod_list": [],
		"default": false,
	},
	"interface/trader": {
		"nickname": "Trader UI",
		"description": "Trader window",
		"mod_list": [],
		"default": false,
	},
}

# UI/_apply_locale 가 세팅. key → bool.
var enabled_whitelist: Dictionary = {}

# 배치 처리 파라미터 (UI 에서 런타임 조정 가능)
var normal_batch_interval: float = 0.01
var normal_batch_size: int = 512

# 성능 통계 수집 (개발용). 배포 시 false 로 설정할 것.
const DEBUG_STATS: bool = false
const DEBUG_STATS_INTERVAL: float = 10.0


# ==========================================
# 데이터 클래스
# ==========================================

# 컨텍스트 + text 행 (static / scoped literal).
# 컨텍스트 필드는 score 계산용으로도 사용.
class ExactEntry:
	var location: String
	var parent: String
	var node_name: String
	var node_type: String
	var text: String
	var translation: String


# 컨텍스트 + 정규식 행 (scoped pattern).
class ScopedPatternEntry:
	var location: String
	var parent: String
	var node_name: String
	var node_type: String
	var regex: RegEx
	var template: String
	var placeholders: Array

	func apply(m: RegExMatch, translate_func: Callable = Callable()) -> String:
		var result: String = template
		for ph_name in placeholders:
			var value: String = m.get_string(ph_name)
			if translate_func.is_valid():
				value = translate_func.call(value)
			result = result.replace("{" + ph_name + "}", value)
		return result


# 전역 정규식 행 (pattern global).
class GlobalPatternEntry:
	var regex: RegEx
	var template: String
	var placeholders: Array

	func apply(m: RegExMatch, translate_func: Callable = Callable()) -> String:
		var result: String = template
		for ph_name in placeholders:
			var value: String = m.get_string(ph_name)
			if translate_func.is_valid():
				value = translate_func.call(value)
			result = result.replace("{" + ph_name + "}", value)
		return result


# ==========================================
# 상태
# ==========================================

# Tier 1+6: static
var static_rows: Array = []                  # [ExactEntry] — 전체 리스트
var static_exact_index: Dictionary = {}      # "loc\tpar\tnam\ttyp\ttext" → translation
var static_by_text: Dictionary = {}          # text → [ExactEntry, ...] — score 용 인덱스

# Tier 2+7: scoped literal
var literal_scoped_rows: Array = []
var literal_scoped_exact_index: Dictionary = {}
var literal_scoped_by_text: Dictionary = {}  # text → [ExactEntry, ...]

# Tier 3+8: scoped pattern
var pattern_scoped_rows: Array = []          # [ScopedPatternEntry] — score 순회용
var pattern_scoped_by_ctx: Dictionary = {}   # "loc\tpar\tnam\ttyp" → [ScopedPatternEntry]

# Tier 4: literal global
var literal_global: Dictionary = {}          # text → translation

# Tier 5: pattern global
var pattern_global: Array = []               # [GlobalPatternEntry]

# Tier 9: substr (부분 문자열 치환, 길이 내림차순 정렬)
var substr_entries: Array = []               # [{text: String, translation: String}, ...]

# 바인딩 테이블
# 각 항목: {node: WeakRef, prop: String, last: String}
var priority_bindings: Array = []
var normal_bindings: Array = []
var _normal_cursor: int = 0

# 캐시 (key = scene\tparent\tname\ttype\ttext)
var translation_cache: Dictionary = {}
var miss_cache: Dictionary = {}

# 성능 통계 (DEBUG_STATS=true 일 때만 사용)
var _stats: Dictionary = {
	"apply_calls": 0,          # _apply_binding 호출 수
	"early_returns": 0,        # last == cur 조기 리턴
	"cache_hits": 0,           # translation_cache 또는 miss_cache 히트
	"cache_misses": 0,         # _find_translation_ctx 실행
	"translations_applied": 0, # node.set(prop, translated) 실제 호출
	"regex_tries": 0,          # pattern 정규식 시도 수
}
var _stats_last: Dictionary = {}


# ==========================================
# 초기화
# ==========================================

func _ready() -> void:
	# translator_ui.gd 가 _locale 을 설정한 뒤 add_child 하므로
	# _ready 시점에 _locale 이 세팅되어 있어야 함.
	# 만약 비어있으면 대기 (안전장치).
	if _locale == "" or _locale == "English":
		return
	_initialize()


func _initialize() -> void:
	if _initialized:
		return
	_initialized = true
	print("[TransToVostok] Initializing... locale=%s, compatible=%s" % [_locale, _compatible_mode])
	_load_translations()

	if _compatible_mode:
		_apply_compatible_mode()

	_bind_tree(get_tree().root)
	get_tree().node_added.connect(_on_node_added)

	var timer: Timer = Timer.new()
	timer.name = "NormalBatchTimer"
	timer.wait_time = normal_batch_interval
	timer.autostart = true
	timer.timeout.connect(_process_normal_batch)
	add_child(timer)

	# DEBUG_STATS 모드: 10초 주기로 통계 덤프
	if DEBUG_STATS:
		var stats_timer: Timer = Timer.new()
		stats_timer.name = "StatsDumpTimer"
		stats_timer.wait_time = DEBUG_STATS_INTERVAL
		stats_timer.autostart = true
		stats_timer.timeout.connect(_dump_stats)
		add_child(stats_timer)

	print("[TransToVostok] Ready. priority=%d normal=%d" % [
		priority_bindings.size(), normal_bindings.size()
	])


func _dump_stats() -> void:
	var delta: Dictionary = {}
	for k in _stats:
		delta[k] = _stats[k] - _stats_last.get(k, 0)
		_stats_last[k] = _stats[k]

	var apply: int = delta["apply_calls"]
	var early_pct: float = 0.0 if apply == 0 else delta["early_returns"] * 100.0 / apply
	var total_lookups: int = delta["cache_hits"] + delta["cache_misses"]
	var hit_pct: float = 0.0 if total_lookups == 0 else delta["cache_hits"] * 100.0 / total_lookups

	print("[TransToVostok][stats] %.0fs Δ:" % DEBUG_STATS_INTERVAL)
	print("  apply=%d  early=%d(%.1f%%)  cache hit/miss=%d/%d(%.1f%%)  regex_tries=%d  applied=%d" % [
		apply, delta["early_returns"], early_pct,
		delta["cache_hits"], delta["cache_misses"], hit_pct,
		delta["regex_tries"], delta["translations_applied"]
	])
	print("  bindings: priority=%d normal=%d  cache_size: trans=%d miss=%d" % [
		priority_bindings.size(), normal_bindings.size(),
		translation_cache.size(), miss_cache.size()
	])


# UI 에서 런타임에 배치 파라미터를 변경. 재초기화 없이 즉시 반영.
func set_batch_params(size: int, interval: float) -> void:
	normal_batch_size = max(1, size)
	normal_batch_interval = max(0.005, interval)
	var timer: Node = get_node_or_null("NormalBatchTimer")
	if timer is Timer:
		timer.wait_time = normal_batch_interval


func _apply_compatible_mode() -> void:
	# 호환 모드: 모든 literal + static 번역을 substr 에도 추가
	# → 부분 문자열 매칭이 전체 번역 데이터로 확장됨
	var added: int = 0
	var existing_texts: Dictionary = {}
	for entry in substr_entries:
		existing_texts[entry["text"]] = true

	# literal_global → substr
	for text in literal_global:
		if not existing_texts.has(text):
			substr_entries.append({"text": text, "translation": literal_global[text]})
			added += 1

	# static exact → substr (번역값만)
	for entry in static_rows:
		if not existing_texts.has(entry.text):
			substr_entries.append({"text": entry.text, "translation": entry.translation})
			existing_texts[entry.text] = true
			added += 1

	# 길이 내림차순 재정렬
	substr_entries.sort_custom(func(a, b): return a["text"].length() > b["text"].length())
	print("[TransToVostok] Compatible mode: %d entries added to substr (total %d)" % [added, substr_entries.size()])


func shutdown() -> void:
	# 타이머 정지 + 프로세스 비활성 (queue_free 전 추가 실행 방지)
	set_process(false)
	for child in get_children():
		if child is Timer:
			child.stop()
			child.queue_free()
	if get_tree().node_added.is_connected(_on_node_added):
		get_tree().node_added.disconnect(_on_node_added)

	var total_bindings: int = priority_bindings.size() + normal_bindings.size()

	# 모든 바인딩의 텍스트를 원본으로 복원 + Value 자식 offset 복원
	for b in priority_bindings + normal_bindings:
		var node = b["node"].get_ref()
		if node == null or not is_instance_valid(node):
			continue
		# 0. OptionButton / PopupMenu 항목 복원
		if b["prop"] == "_popup_items":
			var popup: PopupMenu = null
			if node is PopupMenu:
				popup = node
			elif node is OptionButton:
				popup = node.get_popup()
			if popup != null and popup.has_meta("_ttv_popup_originals"):
				var originals: Array = popup.get_meta("_ttv_popup_originals")
				for i in range(min(originals.size(), popup.item_count)):
					popup.set_item_text(i, originals[i])
				popup.remove_meta("_ttv_popup_originals")
			continue
		# 1. 텍스트 원본 복원
		if b.has("original") and b["original"] != "" and b["prop"] in node:
			node.set(b["prop"], b["original"])
		# 2. _adjust_value_child_offset 이 수정한 Value 자식의 offset 복원
		if b["prop"] == "text" and node is Label:
			var value = node.get_node_or_null("Value")
			if value != null and value.has_meta("_ttv_orig_offset_left"):
				value.offset_left = value.get_meta("_ttv_orig_offset_left")
				value.offset_right = value.get_meta("_ttv_orig_offset_right")
				value.remove_meta("_ttv_orig_offset_left")
				value.remove_meta("_ttv_orig_offset_right")
		# 3. _bind_node dedupe 추적 meta 제거 — 언어 전환 등 재초기화 시 재-bind 허용
		if node.has_meta(META_BOUND_PROPS):
			node.remove_meta(META_BOUND_PROPS)

	# 모든 상태 초기화 (재초기화 시 중복 적재 방지)
	_reset_state()
	_initialized = false
	print("[TransToVostok] Shutdown — %d bindings restored" % total_bindings)


# 번역 인덱스/캐시/바인딩을 전부 비운다. shutdown 또는 재초기화 전에 호출.
func _reset_state() -> void:
	static_rows.clear()
	static_exact_index.clear()
	static_by_text.clear()
	literal_scoped_rows.clear()
	literal_scoped_exact_index.clear()
	literal_scoped_by_text.clear()
	pattern_scoped_rows.clear()
	pattern_scoped_by_ctx.clear()
	literal_global.clear()
	pattern_global.clear()
	substr_entries.clear()
	priority_bindings.clear()
	normal_bindings.clear()
	_normal_cursor = 0
	translation_cache.clear()
	miss_cache.clear()
	if DEBUG_STATS:
		for k in _stats:
			_stats[k] = 0
		_stats_last.clear()


# ==========================================
# TSV 로딩
# ==========================================

func _load_translations() -> void:
	var base: String = DATA_BASE + "/" + _locale + "/runtime_tsv"

	_load_exact_tsv(base + "/translation_static.tsv", static_rows, static_exact_index, static_by_text)
	_load_exact_tsv(
		base + "/translation_literal_scoped.tsv",
		literal_scoped_rows,
		literal_scoped_exact_index,
		literal_scoped_by_text,
	)
	_load_pattern_scoped_tsv(base + "/translation_pattern_scoped.tsv")
	_load_literal_global_tsv(base + "/translation_literal.tsv")
	_load_pattern_global_tsv(base + "/translation_pattern.tsv")
	_load_substr_tsv(base + "/translation_substr.tsv")

	print("[TransToVostok] Loaded: static=%d, literal_scoped=%d, pattern_scoped=%d, literal=%d, pattern=%d, substr=%d" % [
		static_rows.size(),
		literal_scoped_rows.size(),
		pattern_scoped_rows.size(),
		literal_global.size(),
		pattern_global.size(),
		substr_entries.size(),
	])


func _load_exact_tsv(path: String, out_rows: Array, out_index: Dictionary, out_by_text: Dictionary) -> void:
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_warning("[TransToVostok] Cannot open: " + path)
		return

	var _header: PackedStringArray = f.get_csv_line("\t")
	while not f.eof_reached():
		var line: PackedStringArray = f.get_csv_line("\t")
		if line.size() < 6:
			continue
		var entry: ExactEntry = ExactEntry.new()
		entry.location = line[0]
		entry.parent = line[1]
		entry.node_name = line[2]
		entry.node_type = line[3]
		entry.text = line[4]
		entry.translation = line[5]
		out_rows.append(entry)

		var key: String = (entry.location + "\t" + entry.parent + "\t"
			+ entry.node_name + "\t" + entry.node_type + "\t" + entry.text)
		if out_index.has(key):
			push_warning("[TransToVostok] duplicate exact key: " + key)
		out_index[key] = entry.translation

		# score 용 text 별 인덱스
		if not out_by_text.has(entry.text):
			out_by_text[entry.text] = []
		out_by_text[entry.text].append(entry)
	f.close()


func _load_pattern_scoped_tsv(path: String) -> void:
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_warning("[TransToVostok] Cannot open: " + path)
		return

	var _header: PackedStringArray = f.get_csv_line("\t")
	while not f.eof_reached():
		var line: PackedStringArray = f.get_csv_line("\t")
		if line.size() < 6:
			continue
		var entry: ScopedPatternEntry = _compile_scoped_pattern(
			line[0], line[1], line[2], line[3], line[4], line[5]
		)
		if entry == null:
			continue
		pattern_scoped_rows.append(entry)

		var ctx_key: String = (entry.location + "\t" + entry.parent + "\t"
			+ entry.node_name + "\t" + entry.node_type)
		if not pattern_scoped_by_ctx.has(ctx_key):
			pattern_scoped_by_ctx[ctx_key] = []
		pattern_scoped_by_ctx[ctx_key].append(entry)
	f.close()


func _load_literal_global_tsv(path: String) -> void:
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_warning("[TransToVostok] Cannot open: " + path)
		return

	var _header: PackedStringArray = f.get_csv_line("\t")
	while not f.eof_reached():
		var line: PackedStringArray = f.get_csv_line("\t")
		if line.size() < 2:
			continue
		literal_global[line[0]] = line[1]
	f.close()


func _load_pattern_global_tsv(path: String) -> void:
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_warning("[TransToVostok] Cannot open: " + path)
		return

	var _header: PackedStringArray = f.get_csv_line("\t")
	while not f.eof_reached():
		var line: PackedStringArray = f.get_csv_line("\t")
		if line.size() < 2:
			continue
		var entry: GlobalPatternEntry = _compile_global_pattern(line[0], line[1])
		if entry != null:
			pattern_global.append(entry)
	f.close()


func _load_substr_tsv(path: String) -> void:
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_warning("[TransToVostok] Cannot open: " + path)
		return

	var _header: PackedStringArray = f.get_csv_line("\t")
	while not f.eof_reached():
		var line: PackedStringArray = f.get_csv_line("\t")
		if line.size() < 2:
			continue
		if line[0] == "" or line[1] == "":
			continue
		substr_entries.append({"text": line[0], "translation": line[1]})
	f.close()

	# 길이 내림차순 정렬 — 긴 문자열이 먼저 치환되어야 오매칭 방지
	substr_entries.sort_custom(func(a, b): return a["text"].length() > b["text"].length())


# 패턴 문자열(text)을 RegEx 로 컴파일. 실패 시 null.
# 반환: {regex, template, placeholders} 정보를 담은 Dictionary
func _compile_regex(pattern_text: String) -> Dictionary:
	var pattern_str: String = pattern_text
	var meta: Array = ["\\", ".", "^", "$", "+", "?", "(", ")", "[", "]", "|"]
	for c in meta:
		pattern_str = pattern_str.replace(c, "\\" + c)

	var name_re: RegEx = RegEx.new()
	name_re.compile("\\{(\\w+)\\}")
	var placeholders: Array = []
	var matches: Array = name_re.search_all(pattern_str)
	for m in matches:
		placeholders.append(m.get_string(1))
	pattern_str = name_re.sub(pattern_str, "(?<$1>.+?)", true)
	pattern_str = pattern_str.replace("*", "(?:.+?)")

	var regex: RegEx = RegEx.new()
	var err: int = regex.compile("^" + pattern_str + "$")
	if err != OK:
		return {}
	return {
		"regex": regex,
		"placeholders": placeholders,
	}


func _compile_scoped_pattern(
		location: String, parent: String, node_name: String, node_type: String,
		text: String, translation: String) -> ScopedPatternEntry:
	var compiled: Dictionary = _compile_regex(text)
	if compiled.is_empty():
		push_warning("[TransToVostok] Failed to compile scoped pattern: " + text)
		return null
	var entry: ScopedPatternEntry = ScopedPatternEntry.new()
	entry.location = location
	entry.parent = parent
	entry.node_name = node_name
	entry.node_type = node_type
	entry.regex = compiled["regex"]
	entry.template = translation
	entry.placeholders = compiled["placeholders"]
	return entry


func _compile_global_pattern(text: String, translation: String) -> GlobalPatternEntry:
	var compiled: Dictionary = _compile_regex(text)
	if compiled.is_empty():
		push_warning("[TransToVostok] Failed to compile global pattern: " + text)
		return null
	var entry: GlobalPatternEntry = GlobalPatternEntry.new()
	entry.regex = compiled["regex"]
	entry.template = translation
	entry.placeholders = compiled["placeholders"]
	return entry


# ==========================================
# 바인딩 관리
# ==========================================

func _bind_tree(root: Node) -> void:
	var stack: Array = [root]
	while stack.size() > 0:
		var n: Node = stack.pop_back()
		_bind_node(n)
		for child in n.get_children():
			stack.push_back(child)


func _on_node_added(node: Node) -> void:
	_bind_node(node)


const META_BOUND_PROPS := "_ttv_bound_props"

func _bind_node(node: Node) -> void:
	var props_found: Array = []
	for prop in TRANSLATABLE_PROPS:
		if prop in node:
			props_found.append(prop)

	# OptionButton / PopupMenu 는 item_text 배열을 따로 번역
	var popup_target: bool = (node is OptionButton) or (node is PopupMenu)

	if props_found.is_empty() and not popup_target:
		return

	# 같은 (node, prop) 에 이미 binding 이 등록돼 있으면 새 binding 추가 금지.
	# node_added 시그널이 reparent 등으로 한 노드에 대해 여러 번 fire 되면
	# binding 이 중복 누적되어 substr 결과가 매 프레임 다시 입력으로 쌓임 ("Hybrid → Hybride → Hybridee...").
	# meta 로 추적 — 노드 free 시 meta 도 같이 사라지므로 cleanup 불필요. O(1) 조회.
	var bound: Array = node.get_meta(META_BOUND_PROPS, [])

	var is_priority: bool = _is_priority_node(node)

	for prop in props_found:
		if prop in bound:
			continue
		bound.append(prop)
		var b: Dictionary = {
			"node": weakref(node),
			"prop": prop,
			"last": "",
		}
		if is_priority:
			priority_bindings.append(b)
		else:
			normal_bindings.append(b)
		_apply_binding(b)

	if popup_target and not ("_popup_items" in bound):
		bound.append("_popup_items")
		var b: Dictionary = {
			"node": weakref(node),
			"prop": "_popup_items",
			"last": "",
		}
		if is_priority:
			priority_bindings.append(b)
		else:
			normal_bindings.append(b)
		_apply_binding(b)

	if bound.size() > 0:
		node.set_meta(META_BOUND_PROPS, bound)


const PRIORITY_PATH_KEYWORDS: Array = ["tooltip", "transition", "door", "hint", "notification", "message"]

func _is_priority_node(node: Node) -> bool:
	var name_lower: String = node.name.to_lower()
	for kw in PRIORITY_NAME_KEYWORDS:
		if kw in name_lower:
			return true
	var node_path: String = str(node.get_path()).to_lower()
	for kw in PRIORITY_PATH_KEYWORDS:
		if kw in node_path:
			return true
	# 사용자 활성화 whitelist 프리셋 추가 체크
	for kw in enabled_whitelist:
		if enabled_whitelist[kw] and kw in node_path:
			return true
	return false


# ==========================================
# 런타임 처리
# ==========================================

func _process(_delta: float) -> void:
	var i: int = priority_bindings.size() - 1
	while i >= 0:
		var b: Dictionary = priority_bindings[i]
		var node = b["node"].get_ref()
		if node == null or not is_instance_valid(node) or not node.is_inside_tree():
			priority_bindings.remove_at(i)
		else:
			_apply_binding(b)
		i -= 1


func _process_normal_batch() -> void:
	var size: int = normal_bindings.size()
	if size == 0:
		return
	var processed: int = 0
	while processed < normal_batch_size:
		if _normal_cursor >= size:
			_normal_cursor = 0
			break
		var b: Dictionary = normal_bindings[_normal_cursor]
		var node = b["node"].get_ref()
		if node == null or not is_instance_valid(node) or not node.is_inside_tree():
			normal_bindings.remove_at(_normal_cursor)
			size -= 1
		else:
			_apply_binding(b)
			_normal_cursor += 1
		processed += 1


func _apply_binding(b: Dictionary) -> void:
	if DEBUG_STATS:
		_stats["apply_calls"] += 1
	var node = b["node"].get_ref()
	if node == null or not is_instance_valid(node):
		return
	var prop: String = b["prop"]
	if prop == "_popup_items":
		_apply_popup_items(b, node)
		return
	if not (prop in node):
		return
	var cur = node.get(prop)
	if typeof(cur) != TYPE_STRING:
		return
	var cur_str: String = cur
	if cur_str == "":
		return
	if b["last"] == cur_str:
		if DEBUG_STATS:
			_stats["early_returns"] += 1
		return

	var translated = _lookup_cached(node, cur_str)
	if translated != null and translated != cur_str:
		if not b.has("original") or b["original"] == "":
			b["original"] = cur_str
		node.set(prop, translated)
		b["last"] = translated
		if DEBUG_STATS:
			_stats["translations_applied"] += 1
		# 수동 위치 Value 자식이 있으면 새 text 너비에 맞춰 offset 재조정
		if prop == "text":
			_adjust_value_child_offset(node)
	else:
		b["last"] = cur_str


# OptionButton / PopupMenu 의 항목 텍스트를 번역.
# 항목은 Node property 가 아니라 내부 배열이라 _lookup_cached 를 직접 호출한다.
# 원본은 PopupMenu 에 meta 로 저장하여 shutdown 시 복원.
func _apply_popup_items(b: Dictionary, node) -> void:
	var popup: PopupMenu = null
	if node is PopupMenu:
		popup = node
	elif node is OptionButton:
		popup = node.get_popup()
	if popup == null:
		return

	var count: int = popup.item_count
	# 변경 감지용 시그니처 (항목 수 + 현재 텍스트 조인)
	var sig: String = str(count)
	for i in range(count):
		sig += "\t" + popup.get_item_text(i)
	if b["last"] == sig:
		if DEBUG_STATS:
			_stats["early_returns"] += 1
		return

	# 원본 보존 (최초 1회)
	if not popup.has_meta("_ttv_popup_originals"):
		var originals: Array = []
		for i in range(count):
			originals.append(popup.get_item_text(i))
		popup.set_meta("_ttv_popup_originals", originals)

	var any_applied: bool = false
	var host: Node = node  # OptionButton 이면 node, PopupMenu 면 popup — scene 컨텍스트는 node 기준
	for i in range(count):
		var cur: String = popup.get_item_text(i)
		if cur == "":
			continue
		var translated = _lookup_cached(host, cur)
		if translated != null and translated != cur:
			popup.set_item_text(i, translated)
			any_applied = true
			if DEBUG_STATS:
				_stats["translations_applied"] += 1

	# 새 시그니처 재계산 (번역 반영 후 텍스트 기준)
	var new_sig: String = str(popup.item_count)
	for i in range(popup.item_count):
		new_sig += "\t" + popup.get_item_text(i)
	b["last"] = new_sig
	if not any_applied:
		return


# Label 의 자식 "Value" 가 layout_mode=0 (수동 위치) 인 경우,
# Label 의 새 text 너비에 맞춰 Value 의 offset_left/offset_right 를 재계산.
# Tooltip.tscn 같이 "라벨: [값]" 패턴에서 번역된 라벨 너비와 값 위치를 자연스럽게 맞춤.
#
# 호환성 모드 (_compatible_mode) 에서는 레이아웃 변경을 건너뛴다.
# substr 전용 호환성 모드는 최소 간섭 원칙 — 게임 씬의 offset 등 구조 변경 금지.
func _adjust_value_child_offset(label_node) -> void:
	if _compatible_mode:
		return
	if not (label_node is Label):
		return
	var value = label_node.get_node_or_null("Value")
	if value == null or not (value is Control):
		return
	# layout_mode 0 (POSITION) 또는 1 (ANCHORS) 만 대상.
	# 2 (CONTAINER) 인 경우는 부모 Container 가 위치 관리하므로 건드리지 않음.
	# (이전에는 0만 허용했는데, 게임의 Trader/HUD 등 다수 Value 노드가
	#  layout_mode=1 로 설정되어 있어 함수가 silently 동작 안 하던 문제 수정.)
	if value.layout_mode != 0 and value.layout_mode != 1:
		return

	# 폰트/크기 조회 (theme_override 우선, 없으면 기본)
	var font: Font = label_node.get_theme_font("font")
	if font == null:
		return
	var font_size: int = label_node.get_theme_font_size("font_size")
	if font_size <= 0:
		font_size = 16

	# 최초 조정 전에 원본 offset 을 메타데이터로 보존 (shutdown 복원용)
	if not value.has_meta("_ttv_orig_offset_left"):
		value.set_meta("_ttv_orig_offset_left", value.offset_left)
		value.set_meta("_ttv_orig_offset_right", value.offset_right)

	var text_width: float = font.get_string_size(
		label_node.text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size
	).x

	var current_width: float = value.offset_right - value.offset_left
	# Visual gap between Label text end and Value start (in pixels).
	const PADDING: float = 4.0
	value.offset_left = text_width + PADDING
	value.offset_right = value.offset_left + current_width


# ==========================================
# 캐시된 매칭 조회
# ==========================================

func _lookup_cached(node: Node, text: String):
	var scene: String = _get_scene_name(node)
	var parent: String = _get_parent_path(node)
	var node_name: String = node.name
	var node_type: String = node.get_class()
	var cache_key: String = scene + "\t" + parent + "\t" + node_name + "\t" + node_type + "\t" + text

	if miss_cache.has(cache_key):
		if DEBUG_STATS:
			_stats["cache_hits"] += 1
		return null
	if translation_cache.has(cache_key):
		if DEBUG_STATS:
			_stats["cache_hits"] += 1
		return translation_cache[cache_key]

	if DEBUG_STATS:
		_stats["cache_misses"] += 1
	var result = _find_translation_ctx(scene, parent, node_name, node_type, text)
	if result == null:
		miss_cache[cache_key] = true
	else:
		translation_cache[cache_key] = result
	return result


# ==========================================
# 9층 매칭 체인
# ==========================================

func _find_translation_ctx(scene: String, parent: String,
		node_name: String, node_type: String, text: String):
	var exact_key: String = scene + "\t" + parent + "\t" + node_name + "\t" + node_type + "\t" + text
	var ctx_key: String = scene + "\t" + parent + "\t" + node_name + "\t" + node_type

	# --- Tier 1: static exact ---
	if static_exact_index.has(exact_key):
		return static_exact_index[exact_key]

	# --- Tier 2: scoped literal exact ---
	if literal_scoped_exact_index.has(exact_key):
		return literal_scoped_exact_index[exact_key]

	# 캡처 변수 번역용 콜백 (pattern 내 {변수}를 전체 fallback에서 조회하되 pattern은 스킵)
	var _capture_translate: Callable = func(value: String) -> String:
		return _translate_captured(scene, parent, node_name, node_type, value)

	# --- Tier 3: scoped pattern exact (컨텍스트 완전 일치) ---
	if pattern_scoped_by_ctx.has(ctx_key):
		for entry in pattern_scoped_by_ctx[ctx_key]:
			if DEBUG_STATS:
				_stats["regex_tries"] += 1
			var m: RegExMatch = entry.regex.search(text)
			if m != null:
				return entry.apply(m, _capture_translate)

	# --- Tier 4: literal global ---
	if literal_global.has(text):
		return literal_global[text]

	# --- Tier 5: pattern global ---
	for entry in pattern_global:
		if DEBUG_STATS:
			_stats["regex_tries"] += 1
		var m: RegExMatch = entry.regex.search(text)
		if m != null:
			return entry.apply(m, _capture_translate)

	# --- Tier 6: static score (부분 컨텍스트 매칭, text 인덱스 사용) ---
	var result = _score_match_by_text_index(
		static_by_text, scene, parent, node_name, node_type, text, "static")
	if result != null:
		return result

	# --- Tier 7: scoped literal score ---
	result = _score_match_by_text_index(
		literal_scoped_by_text, scene, parent, node_name, node_type, text, "scoped literal")
	if result != null:
		return result

	# --- Tier 8: scoped pattern score ---
	result = _score_match_pattern_rows(
		pattern_scoped_rows, scene, parent, node_name, node_type, text, _capture_translate)
	if result != null:
		return result

	# --- Tier 9: substr (부분 문자열 치환, 최후 fallback) ---
	result = _apply_substr(text)
	if result != text:
		return result

	return null


# text 인덱스를 사용한 score 매칭. O(1) 조회 + O(k) 스코어링.
func _score_match_by_text_index(by_text: Dictionary, scene: String, parent: String,
		node_name: String, node_type: String, text: String, tier_label: String):
	if not by_text.has(text):
		return null
	var candidates: Array = by_text[text]
	var best_score: int = 0
	var best_entry = null
	var tie_count: int = 0
	for entry in candidates:
		var score: int = _compute_score(entry.location, entry.parent, entry.node_name, entry.node_type,
			scene, parent, node_name, node_type)
		if score <= 0:
			continue
		if score > best_score:
			best_score = score
			best_entry = entry
			tie_count = 1
		elif score == best_score:
			tie_count += 1
	if best_entry == null:
		return null
	if tie_count > 1:
		push_warning("[TransToVostok] score tie (%s tier, %d candidates) for text=%s" % [
			tier_label, tie_count, text
		])
	return best_entry.translation


# text 가 완전 일치하는 행 중 가장 높은 score 를 고른다. score>0 필수. (레거시, tier 8 용)
func _score_match_exact_rows(rows: Array, scene: String, parent: String,
		node_name: String, node_type: String, text: String, tier_label: String):
	var best_score: int = 0
	var best_entry = null
	var tie_count: int = 0

	for entry in rows:
		if entry.text != text:
			continue
		var score: int = _compute_score(entry.location, entry.parent, entry.node_name, entry.node_type,
			scene, parent, node_name, node_type)
		if score <= 0:
			continue
		if score > best_score:
			best_score = score
			best_entry = entry
			tie_count = 1
		elif score == best_score:
			tie_count += 1

	if best_entry == null:
		return null

	if tie_count > 1:
		push_warning("[TransToVostok] score tie (%s tier, %d candidates) for text=%s" % [
			tier_label, tie_count, text
		])

	return best_entry.translation


# 정규식이 매칭되는 scoped pattern 행 중 가장 높은 score 를 고른다. score>0 필수.
func _score_match_pattern_rows(rows: Array, scene: String, parent: String,
		node_name: String, node_type: String, text: String,
		translate_func: Callable = Callable()):
	var best_score: int = 0
	var best_entry = null
	var best_match: RegExMatch = null
	var tie_count: int = 0

	for entry in rows:
		var m: RegExMatch = entry.regex.search(text)
		if m == null:
			continue
		var score: int = _compute_score(entry.location, entry.parent, entry.node_name, entry.node_type,
			scene, parent, node_name, node_type)
		if score <= 0:
			continue
		if score > best_score:
			best_score = score
			best_entry = entry
			best_match = m
			tie_count = 1
		elif score == best_score:
			tie_count += 1

	if best_entry == null:
		return null

	if tie_count > 1:
		push_warning("[TransToVostok] score tie (scoped pattern tier, %d candidates) for text=%s" % [
			tie_count, text
		])

	return best_entry.apply(best_match, translate_func)


# 캡처 변수 번역: pattern을 제외한 전체 fallback 조회
func _translate_captured(scene: String, parent: String,
		node_name: String, node_type: String, value: String) -> String:
	if value.is_valid_int() or value.is_valid_float():
		return value
	var exact_key: String = scene + "\t" + parent + "\t" + node_name + "\t" + node_type + "\t" + value

	# Tier 1: static exact
	if static_exact_index.has(exact_key):
		return static_exact_index[exact_key]

	# Tier 2: scoped literal exact
	if literal_scoped_exact_index.has(exact_key):
		return literal_scoped_exact_index[exact_key]

	# Tier 3: SKIP (scoped pattern — 재귀 방지)

	# Tier 4: literal global
	if literal_global.has(value):
		return literal_global[value]

	# Tier 5: SKIP (pattern global — 재귀 방지)

	# Tier 6: static score
	var result = _score_match_by_text_index(
		static_by_text, scene, parent, node_name, node_type, value, "static-capture")
	if result != null:
		return result

	# Tier 7: scoped literal score
	result = _score_match_by_text_index(
		literal_scoped_by_text, scene, parent, node_name, node_type, value, "scoped-literal-capture")
	if result != null:
		return result

	# Tier 8: SKIP (scoped pattern score — 재귀 방지)

	# Tier 9: substr
	var substr_result: String = _apply_substr(value)
	if substr_result != value:
		return substr_result

	return value


# substr 부분 문자열 치환 (길이 내림차순 정렬 보장됨)
func _apply_substr(text: String) -> String:
	if substr_entries.size() == 0:
		return text
	var result: String = text
	for entry in substr_entries:
		var src: String = entry["text"]
		var dst: String = entry["translation"]
		if not (src in result):
			continue
		# Idempotency 가드: src 가 dst 의 substring 이면 변환 결과를 다시 입력해도 또 매치된다.
		# 예: "Hybrid" → "Hybride". 이 entry 를 적용하기 전 result 가 이미 변환된 형태인지 검사:
		# dst 가 result 안에 있고, 그 위치를 마스킹했을 때 src 가 더 이상 안 남으면 이미 적용됨 → 스킵.
		if src in dst:
			var stripped: String = result.replace(dst, "")
			if not (src in stripped):
				continue  # 이미 적용된 결과 — 재적용 금지
		result = result.replace(src, dst)
	return result


static func _compute_score(
		row_location: String, row_parent: String, row_name: String, row_type: String,
		node_location: String, node_parent: String, node_name: String, node_type: String) -> int:
	var s: int = 0
	if row_location == node_location:
		s += SCORE_LOCATION
	if row_parent == node_parent:
		s += SCORE_PARENT
	if row_name == node_name:
		s += SCORE_NAME
	if row_type == node_type:
		s += SCORE_TYPE
	return s


# ==========================================
# 유틸리티
# ==========================================

static func _get_scene_name(node: Node) -> String:
	var scene_owner: Node = node.owner if node.owner != null else node
	var path: String = scene_owner.scene_file_path
	if path == "":
		return ""
	path = path.trim_prefix("res://")
	if path.ends_with(".tscn"):
		path = path.substr(0, path.length() - 5)
	elif path.ends_with(".scn"):
		path = path.substr(0, path.length() - 4)
	return path


static func _get_parent_path(node: Node) -> String:
	var scene_owner: Node = node.owner if node.owner != null else null
	if scene_owner == null or scene_owner == node:
		return ""
	var parent: Node = node.get_parent()
	if parent == null:
		return ""
	return str(scene_owner.get_path_to(parent))
