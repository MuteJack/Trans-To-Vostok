# Trans To Vostok - 런타임 텍스처 교체 엔진
#
# 동작 방식:
#   1. 초기화 시 "res://Trans To Vostok/<locale>/textures/" 를 재귀 스캔
#   2. 발견된 상대 경로를 _available Dictionary 에 등록
#   3. <locale>/texture_meta.json 로드 → 파일별 method 정보 (replace | blend)
#   4. 씬 트리 순회 + node_added 시그널로 관심 노드 수집
#      - TextureRect / Sprite2D / Sprite3D 의 .texture
#      - MeshInstance3D 의 ShaderMaterial 파라미터 (sampler2D)
#   5. 노드의 원본 텍스처 경로가 _available 에 있으면:
#      - method=replace : 번역본으로 교체 (mod PNG 통째로)
#      - method=blend   : 원본 위에 mod PNG (투명 배경 + 번역 텍스트) 를
#                         Image.blend_rect 로 합성. 원본의 PBR 정보 보존,
#                         mod 측은 본인 작업물 (텍스트 픽셀) 만 ship.
#   6. 원본 참조는 _bindings 에 저장 → shutdown 시 복원
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

# 메타 정보 (texture_meta.json 으로부터): rel_path -> "replace" | "blend"
# 항목 없으면 기본 "replace".
var _meta: Dictionary = {}

# blend 결과 캐시: rel_path -> ImageTexture (한 번 합성하면 동일 sign 모든
# 인스턴스에서 재사용). 키는 mod-side rel path.
var _blend_cache: Dictionary = {}

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

	_load_texture_meta()

	_bind_tree(get_tree().root)
	get_tree().node_added.connect(_on_node_added)

	var blend_count: int = 0
	for v in _meta.values():
		if v == "blend":
			blend_count += 1
	print("[TextureLoader] Ready. Available=%d (blend=%d), Bindings=%d" % [
		_available.size(), blend_count, _bindings.size()
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
	_meta.clear()
	_blend_cache.clear()
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
# 메타 로드 (텍스처별 method)
# ==========================================

func _load_texture_meta() -> void:
	_meta.clear()
	var meta_path: String = "%s/%s/texture_meta.json" % [DATA_BASE, _locale]
	if not FileAccess.file_exists(meta_path):
		# 메타 없으면 모든 항목 디폴트 "replace" 로 처리됨
		return
	var f: FileAccess = FileAccess.open(meta_path, FileAccess.READ)
	if f == null:
		push_warning("[TextureLoader] Could not open %s" % meta_path)
		return
	var raw: String = f.get_as_text()
	f.close()
	var parsed = JSON.parse_string(raw)
	if not (parsed is Dictionary):
		push_warning("[TextureLoader] %s not a JSON object" % meta_path)
		return
	for k in parsed.keys():
		var v = parsed[k]
		if v is String and (v == "replace" or v == "blend"):
			_meta[String(k)] = v


func _method_for(rel: String) -> String:
	return _meta.get(rel, "replace")


# ==========================================
# 텍스처 로드 (CheatMenu 패턴 참고)
# ==========================================

func _load_mod_png(path: String) -> Texture2D:
	var img: Image = _load_mod_image(path)
	if img == null:
		return null
	return ImageTexture.create_from_image(img)


func _load_mod_image(path: String) -> Image:
	var img: Image = Image.new()
	var err: int = img.load(path)
	if err == OK and not img.is_empty():
		return img

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
				return img2
	return null


# ==========================================
# 텍스처 합성 (blend)
# ==========================================

# 원본 텍스처 위에 mod overlay PNG 를 alpha-blend 한 합성 ImageTexture 를 반환.
# 동일 rel 에 대해 한 번만 합성하고 캐시 (여러 sign 인스턴스가 동일 material 공유 시 효율).
# 실패 시 null. 호출자는 null 일 때 원본 유지 (no-op).
func _composite_blend(orig_tex: Texture2D, rel: String) -> Texture2D:
	if _blend_cache.has(rel):
		return _blend_cache[rel]

	if orig_tex == null:
		return null

	# 원본 Image 확보. 압축 텍스처 (.ctex) 일 수 있어 get_image() 호출 후 decompress.
	var orig_img: Image = orig_tex.get_image()
	if orig_img == null or orig_img.is_empty():
		push_warning("[TextureLoader] blend: orig texture has no Image for %s" % rel)
		return null
	if orig_img.is_compressed():
		var derr: int = orig_img.decompress()
		if derr != OK:
			push_warning("[TextureLoader] blend: failed to decompress orig for %s" % rel)
			return null
	if orig_img.get_format() != Image.FORMAT_RGBA8:
		orig_img.convert(Image.FORMAT_RGBA8)

	# Overlay (mod 측 투명 배경 + 텍스트 PNG)
	var overlay_img: Image = _load_mod_image(_texture_root + rel)
	if overlay_img == null:
		push_warning("[TextureLoader] blend: failed to load overlay %s" % rel)
		return null
	if overlay_img.get_format() != Image.FORMAT_RGBA8:
		overlay_img.convert(Image.FORMAT_RGBA8)

	# Overlay 가 원본과 다른 크기면 경고 후 진행 (좌상단 정렬, 잘리거나 일부만 덮음).
	# mod 작업 가이드: overlay 는 원본과 동일 해상도여야 자연스러움.
	if overlay_img.get_size() != orig_img.get_size():
		push_warning("[TextureLoader] blend: size mismatch for %s orig=%s overlay=%s" % [
			rel, orig_img.get_size(), overlay_img.get_size()
		])

	var rect: Rect2i = Rect2i(Vector2i.ZERO, overlay_img.get_size())
	orig_img.blend_rect(overlay_img, rect, Vector2i.ZERO)

	var result: ImageTexture = ImageTexture.create_from_image(orig_img)
	_blend_cache[rel] = result
	return result


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
	var new_tex: Texture2D
	match _method_for(rel):
		"blend":
			new_tex = _composite_blend(tex, rel)
		_:
			new_tex = _load_mod_png(_texture_root + rel)
	if new_tex == null:
		push_warning("[TextureLoader] Failed to bind %s" % (_texture_root + rel))
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
		var new_tex: Texture2D
		match _method_for(rel):
			"blend":
				new_tex = _composite_blend(value, rel)
			_:
				new_tex = _load_mod_png(_texture_root + rel)
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
