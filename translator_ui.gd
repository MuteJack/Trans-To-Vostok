# Trans To Vostok — 언어 선택 UI + 번역 엔진 관리
#
# - 모드 로드 시 언어 선택 창 표시
# - F9 으로 언어 변경 가능
# - English 선택 시 translator.gd 비활성 (오버헤드 0)
# - 선택한 언어를 user://trans_to_vostok.cfg 에 저장 (재시작 시 유지)

extends Node

const DATA_BASE: String = "res://Trans To Vostok"
const LOCALE_JSON: String = DATA_BASE + "/locale.json"
const TRANSLATOR_SCRIPT: String = DATA_BASE + "/translator.gd"
const TEXTURE_LOADER_SCRIPT: String = DATA_BASE + "/texture_loader.gd"
const CONFIG_PATH: String = "user://trans_to_vostok.cfg"
const DEFAULT_LOCALE: String = "English"

const DEFAULT_BATCH_SIZE: int = 512
const DEFAULT_BATCH_INTERVAL: float = 0.01

var _locale_data: Dictionary = {}
var _current_locale: String = DEFAULT_LOCALE
var _compatible_mode: bool = false
var _batch_size: int = DEFAULT_BATCH_SIZE
var _batch_interval: float = DEFAULT_BATCH_INTERVAL
var _translator_node: Node = null
var _texture_loader_node: Node = null
var _language_window: Window = null
var _ok_button: Button = null
var _prev_mouse_mode: int = Input.MOUSE_MODE_VISIBLE


func _ready() -> void:
	await get_tree().process_frame
	_locale_data = _load_locale_json()
	_load_config()
	await _show_language_ui(true)
	_apply_locale()


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_F9:
			if _language_window != null:
				_close_language_ui()
			else:
				_show_language_ui(false)


func _close_language_ui() -> void:
	if _ok_button != null:
		_ok_button.pressed.emit()


# ==========================================
# locale.json 로딩
# ==========================================

func _load_locale_json() -> Dictionary:
	var f: FileAccess = FileAccess.open(LOCALE_JSON, FileAccess.READ)
	if f == null:
		push_warning("[TransToVostok UI] Cannot open: " + LOCALE_JSON)
		return {"message": "Select Language", "locales": []}
	var data = JSON.parse_string(f.get_as_text())
	f.close()
	if data is Dictionary:
		return data
	return {"message": "Select Language", "locales": []}


# ==========================================
# 설정 저장/로드
# ==========================================

func _save_config() -> void:
	var config: ConfigFile = ConfigFile.new()
	config.set_value("translation", "locale", _current_locale)
	config.set_value("translation", "compatible_mode", _compatible_mode)
	config.set_value("performance", "batch_size", _batch_size)
	config.set_value("performance", "batch_interval", _batch_interval)
	config.save(CONFIG_PATH)


func _load_config() -> void:
	var config: ConfigFile = ConfigFile.new()
	if config.load(CONFIG_PATH) == OK:
		_current_locale = config.get_value("translation", "locale", DEFAULT_LOCALE)
		_compatible_mode = config.get_value("translation", "compatible_mode", false)
		_batch_size = config.get_value("performance", "batch_size", DEFAULT_BATCH_SIZE)
		_batch_interval = config.get_value("performance", "batch_interval", DEFAULT_BATCH_INTERVAL)


# ==========================================
# 다크 테마 (modloader 참고)
# ==========================================

func _make_dark_theme() -> Theme:
	var t: Theme = Theme.new()

	var bg_color: Color = Color(0.05, 0.05, 0.05)
	var border_color: Color = Color(0.28, 0.28, 0.28)
	var hover_color: Color = Color(0.12, 0.12, 0.12)
	var selected_color: Color = Color(0.15, 0.25, 0.15)
	var font_color: Color = Color(0.85, 0.85, 0.85)

	# Button normal
	var btn_n: StyleBoxFlat = StyleBoxFlat.new()
	btn_n.bg_color = bg_color
	btn_n.border_color = border_color
	btn_n.set_border_width_all(1)
	btn_n.set_content_margin_all(8)
	t.set_stylebox("normal", "Button", btn_n)

	# Button hover
	var btn_h: StyleBoxFlat = btn_n.duplicate()
	btn_h.bg_color = hover_color
	btn_h.border_color = Color(0.5, 0.5, 0.5)
	t.set_stylebox("hover", "Button", btn_h)

	# Button pressed
	var btn_p: StyleBoxFlat = btn_n.duplicate()
	btn_p.bg_color = selected_color
	t.set_stylebox("pressed", "Button", btn_p)

	# ItemList
	var item_bg: StyleBoxFlat = StyleBoxFlat.new()
	item_bg.bg_color = Color(0.03, 0.03, 0.03)
	item_bg.border_color = border_color
	item_bg.set_border_width_all(1)
	t.set_stylebox("panel", "ItemList", item_bg)
	t.set_color("font_color", "ItemList", font_color)
	t.set_color("font_selected_color", "ItemList", Color(1.0, 1.0, 1.0))

	# ItemList selected
	var item_sel: StyleBoxFlat = StyleBoxFlat.new()
	item_sel.bg_color = selected_color
	t.set_stylebox("selected", "ItemList", item_sel)
	t.set_stylebox("selected_focus", "ItemList", item_sel.duplicate())

	# Label
	t.set_color("font_color", "Label", font_color)

	# Panel
	var panel_bg: StyleBoxFlat = StyleBoxFlat.new()
	panel_bg.bg_color = Color(0.02, 0.02, 0.02)
	t.set_stylebox("panel", "Panel", panel_bg)

	return t


# ==========================================
# 언어 선택 UI (modloader 스타일)
# ==========================================

func _show_language_ui(is_startup: bool) -> void:
	var locales: Array = _locale_data.get("locales", [])
	if locales.is_empty():
		push_warning("[TransToVostok UI] No locales in locale.json")
		return

	# 활성화된 locale 필터링 + 메시지 합성
	var enabled_locales: Array = []
	var messages: Array = []
	for loc in locales:
		if loc.get("enabled", false):
			enabled_locales.append(loc)
			var msg: String = loc.get("message", "")
			if msg != "" and msg not in messages:
				messages.append(msg)
	if enabled_locales.is_empty():
		return
	# --- Window ---
	var win: Window = Window.new()
	win.title = "Select Language"
	win.size = Vector2i(720, 500)
	win.min_size = Vector2i(560, 440)
	win.always_on_top = true
	win.transparent = true
	win.transparent_bg = true
	get_tree().root.add_child(win)
	win.popup_centered()

	var win_style: StyleBoxFlat = StyleBoxFlat.new()
	win_style.bg_color = Color(0.0, 0.0, 0.0)
	win.add_theme_stylebox_override("panel", win_style)
	win.add_theme_stylebox_override("embedded_border", win_style.duplicate())
	win.add_theme_stylebox_override("embedded_unfocused_border", win_style.duplicate())

	# --- 배경 ---
	var bg: Panel = Panel.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg_style: StyleBoxFlat = StyleBoxFlat.new()
	bg_style.bg_color = Color(0.0, 0.0, 0.0, 0.85)
	bg_style.border_color = Color(0.4, 0.4, 0.4)
	bg_style.set_border_width_all(1)
	bg.add_theme_stylebox_override("panel", bg_style)
	win.add_child(bg)

	# --- 마진 ---
	var margin: MarginContainer = MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 16)
	margin.add_theme_constant_override("margin_right", 16)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.theme = _make_dark_theme()
	win.add_child(margin)

	# --- 레이아웃 ---
	var root: VBoxContainer = VBoxContainer.new()
	root.add_theme_constant_override("separation", 10)
	margin.add_child(root)

	# 제목
	var title_label: Label = Label.new()
	title_label.text = "Select Language"
	title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title_label.add_theme_font_size_override("font_size", 18)
	root.add_child(title_label)

	# 구분선
	root.add_child(HSeparator.new())

	# --- 본문 좌/우 분할 ---
	var body: HBoxContainer = HBoxContainer.new()
	body.add_theme_constant_override("separation", 12)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(body)

	# 왼쪽: 언어 목록 + 호환 모드
	var left: VBoxContainer = VBoxContainer.new()
	left.add_theme_constant_override("separation", 8)
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.size_flags_stretch_ratio = 2.0
	body.add_child(left)

	var lang_title: Label = Label.new()
	lang_title.text = "Languages"
	lang_title.add_theme_font_size_override("font_size", 14)
	left.add_child(lang_title)

	# 언어 목록 (ItemList, 스크롤 가능)
	var item_list: ItemList = ItemList.new()
	item_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	item_list.custom_minimum_size = Vector2(0, 120)
	item_list.auto_height = false
	item_list.allow_reselect = false
	item_list.select_mode = ItemList.SELECT_SINGLE
	item_list.add_theme_font_size_override("font_size", 16)

	var pre_select: int = 0
	for i in enabled_locales.size():
		var loc: Dictionary = enabled_locales[i]
		var display: String = loc.get("display", loc.get("locale", "???"))
		var locale_id: String = loc.get("locale", "")
		var msg: String = loc.get("message", "")
		var label: String = "%s (%s) — %s" % [display, locale_id, msg]
		item_list.add_item(label)
		if locale_id == _current_locale:
			pre_select = i

	item_list.select(pre_select)
	item_list.ensure_current_is_visible()
	left.add_child(item_list)

	# 호환 모드 체크박스 (선택된 locale 의 compatible 텍스트 사용)
	var compat_check: CheckBox = CheckBox.new()
	var compat_default: String = "Compatible Mode"
	var _compat_texts: Array = []
	for loc in enabled_locales:
		_compat_texts.append(loc.get("compatible", compat_default))

	# 현재 선택 locale 의 텍스트로 초기화
	compat_check.text = "  " + _compat_texts[pre_select] if pre_select < _compat_texts.size() else compat_default
	compat_check.button_pressed = _compatible_mode
	compat_check.add_theme_font_size_override("font_size", 12)
	left.add_child(compat_check)

	# 언어 선택 변경 시 체크박스 텍스트 갱신
	item_list.item_selected.connect(func(idx):
		if idx < _compat_texts.size():
			compat_check.text = "  " + _compat_texts[idx]
	)

	# 세로 구분선
	body.add_child(VSeparator.new())

	# 오른쪽: 성능 설정 패널
	var right: VBoxContainer = VBoxContainer.new()
	right.add_theme_constant_override("separation", 8)
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.size_flags_stretch_ratio = 1.0
	right.custom_minimum_size = Vector2(200, 0)
	body.add_child(right)

	var perf_title: Label = Label.new()
	perf_title.text = "Performance"
	perf_title.add_theme_font_size_override("font_size", 14)
	right.add_child(perf_title)

	# Batch Size
	var size_label: Label = Label.new()
	size_label.text = "Batch Size"
	size_label.add_theme_font_size_override("font_size", 11)
	size_label.modulate = Color(0.7, 0.7, 0.7)
	right.add_child(size_label)

	var size_row: HBoxContainer = HBoxContainer.new()
	size_row.add_theme_constant_override("separation", 8)
	right.add_child(size_row)

	var size_spin: SpinBox = SpinBox.new()
	size_spin.min_value = 1
	size_spin.max_value = 4096
	size_spin.step = 1
	size_spin.value = _batch_size
	size_spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	size_row.add_child(size_spin)

	var size_rec: Label = Label.new()
	size_rec.text = "Default: %d" % DEFAULT_BATCH_SIZE
	size_rec.add_theme_font_size_override("font_size", 10)
	size_rec.modulate = Color(0.5, 0.5, 0.5)
	size_rec.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	size_row.add_child(size_rec)

	var size_desc: Label = Label.new()
	size_desc.text = " - Number of Properties checked per tick.\n"
	size_desc.add_theme_font_size_override("font_size", 10)
	size_desc.modulate = Color(0.45, 0.45, 0.45)
	size_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right.add_child(size_desc)

	# Intervals [s]
	var interval_label: Label = Label.new()
	interval_label.text = "Intervals [s]"
	interval_label.add_theme_font_size_override("font_size", 11)
	interval_label.modulate = Color(0.7, 0.7, 0.7)
	right.add_child(interval_label)

	var interval_row: HBoxContainer = HBoxContainer.new()
	interval_row.add_theme_constant_override("separation", 8)
	right.add_child(interval_row)

	var interval_spin: SpinBox = SpinBox.new()
	interval_spin.min_value = 0.005
	interval_spin.max_value = 1.0
	interval_spin.step = 0.005
	interval_spin.value = _batch_interval
	interval_spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	interval_row.add_child(interval_spin)

	var interval_rec: Label = Label.new()
	interval_rec.text = "Default: %.2f" % DEFAULT_BATCH_INTERVAL
	interval_rec.add_theme_font_size_override("font_size", 10)
	interval_rec.modulate = Color(0.5, 0.5, 0.5)
	interval_rec.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	interval_row.add_child(interval_rec)

	var interval_desc: Label = Label.new()
	interval_desc.text = "  - Delay between each tick.\n"
	interval_desc.add_theme_font_size_override("font_size", 10)
	interval_desc.modulate = Color(0.45, 0.45, 0.45)
	interval_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right.add_child(interval_desc)

	# 가로줄 + 종합 설명
	right.add_child(HSeparator.new())

	var perf_hint: Label = Label.new()
	perf_hint.text = "Larger Batch Size, Smaller Interval will make translation faster, but may cause performance issue."
	perf_hint.add_theme_font_size_override("font_size", 10)
	perf_hint.modulate = Color(0.45, 0.45, 0.45)
	perf_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right.add_child(perf_hint)

	# 기본값 복원 버튼
	var spacer: Control = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right.add_child(spacer)

	var reset_btn: Button = Button.new()
	reset_btn.text = "Reset Defaults"
	reset_btn.add_theme_font_size_override("font_size", 11)
	reset_btn.pressed.connect(func():
		size_spin.value = DEFAULT_BATCH_SIZE
		interval_spin.value = DEFAULT_BATCH_INTERVAL
	)
	right.add_child(reset_btn)

	# 구분선
	root.add_child(HSeparator.new())

	# 하단 바
	var bottom: HBoxContainer = HBoxContainer.new()
	bottom.add_theme_constant_override("separation", 10)
	root.add_child(bottom)

	var hint_label: Label = Label.new()
	hint_label.text = "Press F9 to change language later."
	hint_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hint_label.add_theme_font_size_override("font_size", 11)
	hint_label.modulate = Color(0.45, 0.45, 0.45)
	bottom.add_child(hint_label)

	var ok_btn: Button = Button.new()
	ok_btn.name = "OKButton"
	ok_btn.text = "  OK  "
	ok_btn.custom_minimum_size = Vector2(100, 36)
	bottom.add_child(ok_btn)

	# X 버튼 = OK
	win.close_requested.connect(func(): ok_btn.pressed.emit())

	# 더블클릭 = OK
	item_list.item_activated.connect(func(_idx): ok_btn.pressed.emit())

	_language_window = win
	_ok_button = ok_btn

	# 마우스 표시 (인게임에서 캡처 상태일 수 있으므로)
	_prev_mouse_mode = Input.get_mouse_mode()
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

	await ok_btn.pressed

	# 마우스 복원
	Input.set_mouse_mode(_prev_mouse_mode)

	# 선택 결과 처리
	var prev_compatible: bool = _compatible_mode
	var prev_batch_size: int = _batch_size
	var prev_batch_interval: float = _batch_interval
	_compatible_mode = compat_check.button_pressed
	_batch_size = int(size_spin.value)
	_batch_interval = float(interval_spin.value)
	var batch_changed: bool = (_batch_size != prev_batch_size
		or not is_equal_approx(_batch_interval, prev_batch_interval))

	var selected_items: PackedInt32Array = item_list.get_selected_items()
	if selected_items.size() > 0:
		var sel_idx: int = selected_items[0]
		if sel_idx >= 0 and sel_idx < enabled_locales.size():
			var selected_locale: String = enabled_locales[sel_idx].get("locale", DEFAULT_LOCALE)
			var locale_changed: bool = selected_locale != _current_locale
			var compat_changed: bool = _compatible_mode != prev_compatible
			if locale_changed or compat_changed or batch_changed or is_startup:
				_current_locale = selected_locale
				_save_config()
				if not is_startup:
					# 배치 파라미터만 바뀌었으면 재초기화 없이 즉시 반영
					if batch_changed and not locale_changed and not compat_changed:
						if _translator_node != null and _translator_node.has_method("set_batch_params"):
							_translator_node.set_batch_params(_batch_size, _batch_interval)
					else:
						_apply_locale()

	win.queue_free()
	_language_window = null
	_ok_button = null


# ==========================================
# 번역 엔진 관리
# ==========================================

func _apply_locale() -> void:
	# 기존 엔진 정리 (텍스트 + 텍스처 둘 다)
	if _texture_loader_node != null:
		_texture_loader_node.shutdown()
		_texture_loader_node.queue_free()
		_texture_loader_node = null
	if _translator_node != null:
		_translator_node.shutdown()
		_translator_node.queue_free()
		_translator_node = null
		# 게임이 텍스트를 원본으로 재설정할 시간 확보
		await get_tree().create_timer(0.5).timeout

	if _current_locale == DEFAULT_LOCALE:
		print("[TransToVostok UI] Locale: %s (no translation)" % _current_locale)
		return

	# 1. 텍스트 번역 엔진
	var script: GDScript = load(TRANSLATOR_SCRIPT) as GDScript
	if script == null:
		push_warning("[TransToVostok UI] Cannot load: " + TRANSLATOR_SCRIPT)
		return

	var node: Node = Node.new()
	node.name = "Translator"
	node.set_script(script)
	node._locale = _current_locale
	node._compatible_mode = _compatible_mode
	node.normal_batch_size = _batch_size
	node.normal_batch_interval = _batch_interval
	add_child(node)
	node._initialize()
	_translator_node = node
	print("[TransToVostok UI] Locale: %s — translator loaded" % _current_locale)

	# 2. 텍스처 교체 엔진 (이미지 폴더가 있는 로케일만 동작)
	var tex_script: GDScript = load(TEXTURE_LOADER_SCRIPT) as GDScript
	if tex_script == null:
		push_warning("[TransToVostok UI] Cannot load: " + TEXTURE_LOADER_SCRIPT)
		return

	var tex_node: Node = Node.new()
	tex_node.name = "TextureLoader"
	tex_node.set_script(tex_script)
	tex_node._locale = _current_locale
	add_child(tex_node)
	tex_node._initialize()
	_texture_loader_node = tex_node
