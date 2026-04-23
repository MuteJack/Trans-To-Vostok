# Trans To Vostok - 런타임 텍스처 교체 엔진
#
# 동작 방식:
#   1. 초기화 시 "res://Trans To Vostok/<locale>/textures/" 를 재귀 스캔
#   2. 발견된 상대 경로를 _available Dictionary 에 등록
#   3. 씬 트리 순회 + node_added 시그널로 관심 노드 수집
#      - TextureRect / Sprite2D / Sprite3D 의 .texture
#      - MeshInstance3D 의 ShaderMaterial 파라미터 (sampler2D)
#   4. 노드의 원본 텍스처 경로가 _available 에 있으면 번역본으로 교체
#   5. 원본 참조는 _bindings 에 저장 → shutdown 시 복원
#
# 검증 책임 분리:
#   - 런타임: 파일 존재 체크만. 없으면 원본 유지 (크래시 없음)
#   - 빌드 시: Python 도구가 textures.tsv ↔ 실제 파일 교차 검증
#
# 언어 전환:
#   - translator_ui.gd 가 언어 변경 시 shutdown() 호출 → 원본 복원
#   - 새 인스턴스를 add_child 하여 다른 로케일로 재초기화
#
# 배포 구조:
#   Korean/
#     textures/
#       UI/Sprites/World_Map.png                      # 원본 res:// 경로 미러링
#       Assets/Tutorial/Billboards/Files/TX_Tutorial_Maps.png
#       ...

extends Node

# ==========================================
# 설정
# ==========================================

var _locale: String = "Korean"
var _initialized: bool = false

const DATA_BASE: String = "res://Trans To Vostok"
const IMAGE_EXTENSIONS: Array = ["png", "jpg", "jpeg", "webp"]

# 셰이더 파라미터 중 텍스처일 가능성이 있는 이름 (확장 가능).
# Godot 4 는 shader_parameter/ 프리픽스를 get_property_list 로 얻을 수 있어
# 일반적으로는 자동 검출하지만, 확실한 파라미터만 취급하도록 제한.
const SHADER_TEXTURE_PREFIX: String = "shader_parameter/"


# ==========================================
# 런타임 상태
# ==========================================

# "UI/Sprites/World_Map.png" 등 상대 경로 집합
var _available: Dictionary = {}

# 이미지 루트: "res://Trans To Vostok/Korean/images/"
var _texture_root: String = ""

# 바인딩 목록. 각 항목은 타입에 따라 다른 필드:
#   texture_prop: {type, node(weakref), prop, orig(Texture2D)}
#   shader_param: {type, material(weakref), param_name, orig(Texture2D)}
var _bindings: Array = []


# ==========================================
# 생명주기
# ==========================================

func _ready() -> void:
	# translator_ui.gd 가 _locale 을 설정한 뒤 add_child 하므로
	# _ready 시점에 _locale 이 세팅되어 있어야 함.
	if _locale == "" or _locale == "English":
		return
	_initialize()


func _initialize() -> void:
	if _initialized:
		return
	_initialized = true
	_texture_root = "%s/%s/textures/" % [DATA_BASE, _locale]
	print("[TextureLoader] Initializing... locale=%s" % _locale)

	_scan_available_images()
	if _available.is_empty():
		print("[TextureLoader] No images for locale '%s' — skipping" % _locale)
		return

	_bind_tree(get_tree().root)
	get_tree().node_added.connect(_on_node_added)

	print("[TextureLoader] Ready. Available=%d, Bindings=%d" % [
		_available.size(), _bindings.size()
	])


func shutdown() -> void:
	if get_tree().node_added.is_connected(_on_node_added):
		get_tree().node_added.disconnect(_on_node_added)

	var restored: int = 0
	for b in _bindings:
		match b.get("type", ""):
			"texture_prop":
				var node = b["node"].get_ref()
				if node == null or not is_instance_valid(node):
					continue
				if b["prop"] in node:
					node.set(b["prop"], b["orig"])
					restored += 1
			"shader_param":
				var mat = b["material"].get_ref()
				if mat == null or not is_instance_valid(mat):
					continue
				mat.set_shader_parameter(b["param_name"], b["orig"])
				restored += 1

	_bindings.clear()
	_available.clear()
	_initialized = false
	print("[TextureLoader] Shutdown — %d textures restored" % restored)


# ==========================================
# 이미지 스캔
# ==========================================

func _scan_available_images() -> void:
	_available.clear()
	_recursive_scan("")


func _recursive_scan(rel: String) -> void:
	var full: String = _texture_root + rel
	var dir: DirAccess = DirAccess.open(full)
	if dir == null:
		return
	dir.list_dir_begin()
	while true:
		var name: String = dir.get_next()
		if name.is_empty():
			break
		if name == "." or name == "..":
			continue
		var child: String = rel + name
		if dir.current_is_dir():
			_recursive_scan(child + "/")
		else:
			var ext: String = name.get_extension().to_lower()
			if ext in IMAGE_EXTENSIONS:
				_available[child] = true
	dir.list_dir_end()


# ==========================================
# 텍스처 로드 (CheatMenu 패턴 참고)
# ==========================================

func _load_mod_png(path: String) -> Texture2D:
	var img: Image = Image.new()
	var err: int = img.load(path)
	if err == OK and not img.is_empty():
		return ImageTexture.create_from_image(img)

	# Fallback: raw bytes 를 수동 decode (mod 경로 특수 케이스 대비)
	if FileAccess.file_exists(path):
		var bytes: PackedByteArray = FileAccess.get_file_as_bytes(path)
		if bytes.size() > 0:
			var img2: Image = Image.new()
			var ext: String = path.get_extension().to_lower()
			var err2: int = FAILED
			if ext == "png":
				err2 = img2.load_png_from_buffer(bytes)
			elif ext == "jpg" or ext == "jpeg":
				err2 = img2.load_jpg_from_buffer(bytes)
			elif ext == "webp":
				err2 = img2.load_webp_from_buffer(bytes)
			if err2 == OK and not img2.is_empty():
				return ImageTexture.create_from_image(img2)
	return null


# ==========================================
# 바인딩
# ==========================================

func _bind_tree(root: Node) -> void:
	_bind_node(root)
	for child in root.get_children():
		_bind_tree(child)


func _on_node_added(node: Node) -> void:
	_bind_node(node)


func _bind_node(node: Node) -> void:
	# 2D: TextureRect / Sprite2D / NinePatchRect
	if node is TextureRect or node is Sprite2D or node is NinePatchRect:
		_try_bind_texture_property(node, "texture")
		return

	# 3D: Sprite3D
	if node is Sprite3D:
		_try_bind_texture_property(node, "texture")
		return

	# 3D 메시: ShaderMaterial 의 sampler2D 파라미터
	if node is MeshInstance3D:
		_try_bind_mesh_shaders(node)
		return


func _try_bind_texture_property(node: Node, prop: String) -> void:
	var tex = node.get(prop)
	if tex == null or not (tex is Texture2D):
		return
	var rel: String = _resource_path_to_rel(tex.resource_path)
	if rel == "" or not _available.has(rel):
		return
	var new_tex: Texture2D = _load_mod_png(_texture_root + rel)
	if new_tex == null:
		push_warning("[TextureLoader] Failed to load %s" % (_texture_root + rel))
		return
	_bindings.append({
		"type": "texture_prop",
		"node": weakref(node),
		"prop": prop,
		"orig": tex,
	})
	node.set(prop, new_tex)


func _try_bind_mesh_shaders(mesh_node: MeshInstance3D) -> void:
	var mesh: Mesh = mesh_node.mesh
	if mesh == null:
		return
	var count: int = mesh.get_surface_count()
	for i in range(count):
		var mat: Material = mesh_node.get_active_material(i)
		if mat is ShaderMaterial:
			_try_bind_shader_material(mat)


func _try_bind_shader_material(mat: ShaderMaterial) -> void:
	# ShaderMaterial 의 shader_parameter/* 중 Texture2D 인 것만 교체
	for prop_info in mat.get_property_list():
		var pname: String = prop_info.get("name", "")
		if not pname.begins_with(SHADER_TEXTURE_PREFIX):
			continue
		var param_name: String = pname.substr(SHADER_TEXTURE_PREFIX.length())
		var value = mat.get_shader_parameter(param_name)
		if not (value is Texture2D):
			continue
		var rel: String = _resource_path_to_rel(value.resource_path)
		if rel == "" or not _available.has(rel):
			continue
		var new_tex: Texture2D = _load_mod_png(_texture_root + rel)
		if new_tex == null:
			continue
		# 동일 material 의 동일 param 에 이미 바인딩이 있는지 (공유 material 대비)
		if _is_shader_already_bound(mat, param_name):
			continue
		_bindings.append({
			"type": "shader_param",
			"material": weakref(mat),
			"param_name": param_name,
			"orig": value,
		})
		mat.set_shader_parameter(param_name, new_tex)


func _is_shader_already_bound(mat: ShaderMaterial, param_name: String) -> bool:
	for b in _bindings:
		if b.get("type", "") != "shader_param":
			continue
		var m = b["material"].get_ref()
		if m == mat and b["param_name"] == param_name:
			return true
	return false


# ==========================================
# 유틸
# ==========================================

func _resource_path_to_rel(resource_path: String) -> String:
	# "res://UI/Sprites/World_Map.png" -> "UI/Sprites/World_Map.png"
	if resource_path == "" or not resource_path.begins_with("res://"):
		return ""
	return resource_path.substr(len("res://"))
