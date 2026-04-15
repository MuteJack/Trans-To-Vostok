# Trans To Vostok - 런타임 번역 엔진
#
# 설계 개요:
#   1. translation.tsv            (일반 행, 점수 기반 매칭)
#   2. translation_literal.tsv    (#literal, 텍스트 전역 매칭, fallback 1순위)
#   3. translation_expression.tsv (#expression, 패턴/정규식, fallback 2순위)
#
# 매칭 점수:
#   location + 8, parent + 4, name + 2, type + 1
#
# 매칭 우선순위:
#   1) rows_by_text[text] 최고 점수 후보
#   2) #literal fallback (same text)
#   3) #expression 패턴 매칭
#   4) 일반 행 점수 0 (암묵적 text-only fallback)
#
# 런타임 구조 (DIO-KAMI 패턴 참고):
#   - 바인딩 테이블: 관심 노드만 등록, 트리 재순회 없음
#   - last 값 비교: 변경 없으면 조회 전부 스킵 (대부분의 호출이 여기서 조기 리턴)
#   - 결과/음성 캐시: 같은 (컨텍스트, text) 조합은 평생 1회만 매칭 체인 실행
#   - Priority (_process, 매 프레임) / Normal (타이머 배치) 분리

extends Node

# ==========================================
# 설정
# ==========================================

const LOCALE: String = "Korean"
const DATA_BASE: String = "res://Trans To Vostok"

const SCORE_LOCATION: int = 8
const SCORE_PARENT: int = 4
const SCORE_NAME: int = 2
const SCORE_TYPE: int = 1

# 번역 대상 속성
const TRANSLATABLE_PROPS: Array = ["text", "placeholder_text", "tooltip_text"]

# 노드 이름에 이 키워드가 포함되면 priority 처리 (매 프레임 체크)
const PRIORITY_NAME_KEYWORDS: Array = ["interact", "tooltip", "loading", "container"]

# 일반 바인딩 배치 처리
const NORMAL_BATCH_INTERVAL: float = 0.05
const NORMAL_BATCH_SIZE: int = 20


# ==========================================
# 데이터 클래스
# ==========================================

class PatternEntry:
	var regex: RegEx
	var template: String
	var placeholders: Array

	func apply(m: RegExMatch) -> String:
		var result: String = template
		for ph_name in placeholders:
			var value: String = m.get_string(ph_name)
			result = result.replace("{" + ph_name + "}", value)
		return result


# ==========================================
# 상태
# ==========================================

# 매칭 데이터
var rows_by_text: Dictionary = {}     # text → [row_dict, ...] (일반 행)
var literal_index: Dictionary = {}    # text → translated (#literal)
var patterns: Array = []              # [PatternEntry, ...] (#expression)

# 바인딩 테이블
# 각 항목: {node: WeakRef, prop: String, last: String}
var priority_bindings: Array = []
var normal_bindings: Array = []
var _normal_cursor: int = 0

# 캐시 (key = scene\tparent\tname\ttype\ttext)
var translation_cache: Dictionary = {}
var miss_cache: Dictionary = {}


# ==========================================
# 초기화
# ==========================================

func _ready() -> void:
	print("[TransToVostok] Initializing... locale=%s" % LOCALE)
	_load_translations()

	# 기존 트리 바인딩
	_bind_tree(get_tree().root)
	# 이후 추가되는 노드 자동 바인딩
	get_tree().node_added.connect(_on_node_added)

	# Normal 배치 타이머
	var timer: Timer = Timer.new()
	timer.name = "NormalBatchTimer"
	timer.wait_time = NORMAL_BATCH_INTERVAL
	timer.autostart = true
	timer.timeout.connect(_process_normal_batch)
	add_child(timer)

	print("[TransToVostok] Ready. priority=%d normal=%d" % [
		priority_bindings.size(), normal_bindings.size()
	])


# ==========================================
# TSV 로딩
# ==========================================

func _load_translations() -> void:
	var base: String = DATA_BASE + "/" + LOCALE
	_load_main_tsv(base + "/translation.tsv")
	_load_literal_tsv(base + "/translation_literal.tsv")
	_load_expression_tsv(base + "/translation_expression.tsv")

	var main_count: int = 0
	for arr in rows_by_text.values():
		main_count += arr.size()

	print("[TransToVostok] Loaded: %d main + %d literal + %d pattern" % [
		main_count, literal_index.size(), patterns.size()
	])


func _load_main_tsv(path: String) -> void:
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_warning("[TransToVostok] Cannot open: " + path)
		return

	var _header: PackedStringArray = f.get_csv_line("\t")
	while not f.eof_reached():
		var line: PackedStringArray = f.get_csv_line("\t")
		if line.size() < 6:
			continue
		var row: Dictionary = {
			"location": line[0],
			"parent": line[1],
			"name": line[2],
			"type": line[3],
			"text": line[4],
			"translated": line[5],
		}
		var text: String = row["text"]
		if not rows_by_text.has(text):
			rows_by_text[text] = []
		rows_by_text[text].append(row)
	f.close()


func _load_literal_tsv(path: String) -> void:
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_warning("[TransToVostok] Cannot open: " + path)
		return

	var _header: PackedStringArray = f.get_csv_line("\t")
	while not f.eof_reached():
		var line: PackedStringArray = f.get_csv_line("\t")
		if line.size() < 2:
			continue
		literal_index[line[0]] = line[1]
	f.close()


func _load_expression_tsv(path: String) -> void:
	var f: FileAccess = FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_warning("[TransToVostok] Cannot open: " + path)
		return

	var _header: PackedStringArray = f.get_csv_line("\t")
	while not f.eof_reached():
		var line: PackedStringArray = f.get_csv_line("\t")
		if line.size() < 2:
			continue
		var entry: PatternEntry = _compile_pattern(line[0], line[1])
		if entry != null:
			patterns.append(entry)
	f.close()


func _compile_pattern(original: String, translated: String) -> PatternEntry:
	var entry: PatternEntry = PatternEntry.new()
	entry.template = translated
	entry.placeholders = []

	# 1. 정규식 메타 문자 이스케이프 ({, }, *는 별도 처리)
	var pattern_str: String = original
	var meta: Array = ["\\", ".", "^", "$", "+", "?", "(", ")", "[", "]", "|"]
	for c in meta:
		pattern_str = pattern_str.replace(c, "\\" + c)

	# 2. {name} → named capture group
	var name_re: RegEx = RegEx.new()
	name_re.compile("\\{(\\w+)\\}")
	var matches: Array = name_re.search_all(pattern_str)
	for m in matches:
		entry.placeholders.append(m.get_string(1))
	pattern_str = name_re.sub(pattern_str, "(?<$1>.+?)", true)

	# 3. * → non-capturing wildcard
	pattern_str = pattern_str.replace("*", "(?:.+?)")

	entry.regex = RegEx.new()
	var err: int = entry.regex.compile("^" + pattern_str + "$")
	if err != OK:
		push_warning("[TransToVostok] Failed to compile pattern: " + original)
		return null
	return entry


# ==========================================
# 바인딩 관리
# ==========================================

func _bind_tree(root: Node) -> void:
	# 트리 전체를 한 번 순회하며 바인딩 등록 (초기화용)
	var stack: Array = [root]
	while stack.size() > 0:
		var n: Node = stack.pop_back()
		_bind_node(n)
		for child in n.get_children():
			stack.push_back(child)


func _on_node_added(node: Node) -> void:
	# node_added는 자식 노드마다 개별 발생 → 재귀 불필요
	_bind_node(node)


func _bind_node(node: Node) -> void:
	# 노드의 TRANSLATABLE_PROPS 중 존재하는 것만 바인딩으로 등록.
	# 이름에 priority 키워드가 포함되면 priority_bindings 에, 아니면 normal_bindings 에.
	var name_lower: String = node.name.to_lower()
	var is_priority: bool = false
	for kw in PRIORITY_NAME_KEYWORDS:
		if kw in name_lower:
			is_priority = true
			break

	for prop in TRANSLATABLE_PROPS:
		if not (prop in node):
			continue
		var b: Dictionary = {
			"node": weakref(node),
			"prop": prop,
			"last": "",
		}
		if is_priority:
			priority_bindings.append(b)
		else:
			normal_bindings.append(b)
		# 바인딩 등록 직후 1회 즉시 처리
		_apply_binding(b)


# ==========================================
# 런타임 처리
# ==========================================

func _process(_delta: float) -> void:
	# Priority 바인딩: 매 프레임 전수 체크 (역순 순회로 remove 안전)
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
	# Normal 바인딩: 0.05초마다 NORMAL_BATCH_SIZE 개씩 라운드로빈
	var size: int = normal_bindings.size()
	if size == 0:
		return

	var processed: int = 0
	while processed < NORMAL_BATCH_SIZE:
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
	# 핵심 조기 리턴 로직:
	#   1) 노드 유효성
	#   2) 속성 존재 + string 타입
	#   3) 빈 문자열 스킵
	#   4) 지난 스캔과 동일하면 스킵  ← 대부분의 호출이 여기서 종료
	var node = b["node"].get_ref()
	if node == null or not is_instance_valid(node):
		return
	var prop: String = b["prop"]
	if not (prop in node):
		return
	var cur = node.get(prop)
	if typeof(cur) != TYPE_STRING:
		return
	var cur_str: String = cur
	if cur_str == "":
		return
	if b["last"] == cur_str:
		return

	var translated = _lookup_cached(node, cur_str)
	if translated != null and translated != cur_str:
		node.set(prop, translated)
		b["last"] = translated
	else:
		# 번역 결과가 없거나 원문과 같으면 last에 원문을 저장해
		# 다음 스캔에 즉시 조기 리턴되도록 함
		b["last"] = cur_str


# ==========================================
# 캐시된 매칭 조회
# ==========================================

func _lookup_cached(node: Node, text: String):
	# 키 구성에 쓰이는 노드 컨텍스트. 캐시 히트 시 _find_translation_ctx 를 건너뛴다.
	var scene: String = _get_scene_name(node)
	var parent: String = _get_parent_path(node)
	var node_name: String = node.name
	var node_type: String = node.get_class()
	var key: String = scene + "\t" + parent + "\t" + node_name + "\t" + node_type + "\t" + text

	if miss_cache.has(key):
		return null
	if translation_cache.has(key):
		return translation_cache[key]

	var result = _find_translation_ctx(scene, parent, node_name, node_type, text)
	if result == null:
		miss_cache[key] = true
	else:
		translation_cache[key] = result
	return result


func _find_translation_ctx(scene: String, parent: String,
		node_name: String, node_type: String, text: String):
	# 매칭 우선순위:
	#   1) 점수 > 0 (특정 컨텍스트 매칭)
	#   2) #literal
	#   3) #expression
	#   4) 점수 = 0 (일반 행의 암묵적 fallback)
	var best_score: int = 0
	var best_trans_scored = null
	var text_only_fallback = null

	if rows_by_text.has(text):
		var candidates: Array = rows_by_text[text]
		for row in candidates:
			var score: int = 0
			if row["location"] == scene:
				score += SCORE_LOCATION
			if row["parent"] == parent:
				score += SCORE_PARENT
			if row["name"] == node_name:
				score += SCORE_NAME
			if row["type"] == node_type:
				score += SCORE_TYPE

			if score > best_score:
				best_score = score
				best_trans_scored = row["translated"]
			elif score == 0 and text_only_fallback == null:
				text_only_fallback = row["translated"]

		if best_trans_scored != null:
			return best_trans_scored

	if literal_index.has(text):
		return literal_index[text]

	for p in patterns:
		var m: RegExMatch = p.regex.search(text)
		if m != null:
			return p.apply(m)

	if text_only_fallback != null:
		return text_only_fallback

	return null


# ==========================================
# 유틸리티
# ==========================================

static func _get_scene_name(node: Node) -> String:
	# 노드의 owner가 포함된 씬 파일 경로를 반환 (예: "Scenes/Menu")
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
	# node의 owner 기준 부모 경로 (예: "Main/Buttons")
	# owner == node 자기자신이면 빈 문자열
	var scene_owner: Node = node.owner if node.owner != null else null
	if scene_owner == null or scene_owner == node:
		return ""
	var parent: Node = node.get_parent()
	if parent == null:
		return ""
	return str(scene_owner.get_path_to(parent))
