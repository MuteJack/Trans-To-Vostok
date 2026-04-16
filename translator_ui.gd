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
const CONFIG_PATH: String = "user://trans_to_vostok.cfg"
const DEFAULT_LOCALE: String = "English"

var _locale_data: Dictionary = {}
var _current_locale: String = DEFAULT_LOCALE
var _translator_node: Node = null
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
	config.save(CONFIG_PATH)


func _load_config() -> void:
	var config: ConfigFile = ConfigFile.new()
	if config.load(CONFIG_PATH) == OK:
		_current_locale = config.get_value("translation", "locale", DEFAULT_LOCALE)


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
	win.size = Vector2i(480, 320)
	win.min_size = Vector2i(320, 220)
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
	root.add_child(item_list)

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
	var selected_items: PackedInt32Array = item_list.get_selected_items()
	if selected_items.size() > 0:
		var sel_idx: int = selected_items[0]
		if sel_idx >= 0 and sel_idx < enabled_locales.size():
			var selected_locale: String = enabled_locales[sel_idx].get("locale", DEFAULT_LOCALE)
			if selected_locale != _current_locale or is_startup:
				_current_locale = selected_locale
				_save_config()
				if not is_startup:
					_apply_locale()

	win.queue_free()
	_language_window = null
	_ok_button = null


# ==========================================
# 번역 엔진 관리
# ==========================================

func _apply_locale() -> void:
	if _translator_node != null:
		_translator_node.shutdown()
		_translator_node.queue_free()
		_translator_node = null

	if _current_locale == DEFAULT_LOCALE:
		print("[TransToVostok UI] Locale: %s (no translation)" % _current_locale)
		return

	var script: GDScript = load(TRANSLATOR_SCRIPT) as GDScript
	if script == null:
		push_warning("[TransToVostok UI] Cannot load: " + TRANSLATOR_SCRIPT)
		return

	var node: Node = Node.new()
	node.name = "Translator"
	node.set_script(script)
	node._locale = _current_locale
	add_child(node)
	node._initialize()
	_translator_node = node
	print("[TransToVostok UI] Locale: %s — translator loaded" % _current_locale)
