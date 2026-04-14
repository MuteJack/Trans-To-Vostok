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
#   4) 원본 유지

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

# 주기적 스캔 주기 (초). 동적으로 변경되는 텍스트를 재번역하기 위함.
const SCAN_INTERVAL: float = 0.2


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

# text → [row_dict, ...] (일반 행)
var rows_by_text: Dictionary = {}
# text → translated (#literal)
var literal_index: Dictionary = {}
# [PatternEntry, ...] (#expression)
var patterns: Array = []


# ==========================================
# 초기화
# ==========================================

func _ready() -> void:
	print("[TransToVostok] Initializing... locale=%s" % LOCALE)
	_load_translations()
	_periodic_scan()

	# 주기적 재스캔 타이머
	var timer: Timer = Timer.new()
	timer.name = "TranslationScanTimer"
	timer.wait_time = SCAN_INTERVAL
	timer.autostart = true
	timer.timeout.connect(_periodic_scan)
	add_child(timer)

	print("[TransToVostok] Ready. Scanning every %.2fs" % SCAN_INTERVAL)


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

	# 헤더 스킵
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
# 씬 트리 스캔
# ==========================================

func _periodic_scan() -> void:
	# /root 전체 스캔 (current_scene + 모든 autoload 포함).
	# Loader 같은 autoload 안의 Label도 커버해야 하므로 current_scene만 스캔하면 안 됨.
	_scan_node(get_tree().root)
	
	# Deprecated due to Loading {Scene} don't work:
	# var root: Node = get_tree().current_scene
	# if root == null:
		# root = get_tree().root
	# _scan_node(root)


func _scan_node(node: Node) -> void:
	_translate_node(node)
	for child in node.get_children():
		_scan_node(child)


# ==========================================
# 번역 적용
# ==========================================

func _translate_node(node: Node) -> void:
	for prop in TRANSLATABLE_PROPS:
		if not (prop in node):
			continue
		var current = node.get(prop)
		if typeof(current) != TYPE_STRING:
			continue
		var current_str: String = current
		if current_str == "":
			continue

		var translated = _find_translation(node, current_str)
		if translated != null and translated != current_str:
			node.set(prop, translated)


func _find_translation(node: Node, text: String):
	# 매칭 우선순위:
	#   1) 점수 > 0 (특정 컨텍스트 매칭)
	#   2) #literal
	#   3) #expression
	#   4) 점수 = 0 (일반 행의 암묵적 fallback)
	#   5) 번역 없음

	var best_score: int = 0
	var best_trans_scored = null     # 점수 > 0 후보
	var text_only_fallback = null     # 점수 0 후보 (최후 fallback)

	# 1. 일반 매칭 (점수 계산)
	if rows_by_text.has(text):
		var candidates: Array = rows_by_text[text]

		var scene_name: String = _get_scene_name(node)
		var parent_path: String = _get_parent_path(node)
		var node_name: String = node.name
		var node_type: String = node.get_class()

		for row in candidates:
			var score: int = 0
			if row["location"] == scene_name:
				score += SCORE_LOCATION
			if row["parent"] == parent_path:
				score += SCORE_PARENT
			if row["name"] == node_name:
				score += SCORE_NAME
			if row["type"] == node_type:
				score += SCORE_TYPE

			if score > best_score:
				best_score = score
				best_trans_scored = row["translated"]
			elif score == 0 and text_only_fallback == null:
				# 점수 0은 최후 fallback으로만 사용
				text_only_fallback = row["translated"]

		if best_trans_scored != null:
			return best_trans_scored

	# 2. #literal fallback (점수 0보다 우선)
	if literal_index.has(text):
		return literal_index[text]

	# 3. #expression 패턴 매칭
	for p in patterns:
		var m: RegExMatch = p.regex.search(text)
		if m != null:
			return p.apply(m)

	# 4. 점수 0 일반 매칭 (암묵적 fallback)
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
