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
var _substr_mode: bool = false
var _batch_size: int = DEFAULT_BATCH_SIZE
var _batch_interval: float = DEFAULT_BATCH_INTERVAL
var _translator_node: Node = null
var _texture_loader_node: Node = null
var _enabled_whitelist: Dictionary = {}   # {"hud/info/map": true, ...}
var _enabled_addons: Dictionary = {       # mod compatibility addons (default OFF)
	"immersivexp_prefix": false,
}
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
	config.set_value("translation", "substr_mode", _substr_mode)
	config.set_value("performance", "batch_size", _batch_size)
	config.set_value("performance", "batch_interval", _batch_interval)
	for key in _enabled_whitelist:
		config.set_value("whitelist", key, _enabled_whitelist[key])
	for key in _enabled_addons:
		config.set_value("addons", key, _enabled_addons[key])
	config.save(CONFIG_PATH)


func _load_config() -> void:
	var config: ConfigFile = ConfigFile.new()
	var loaded: bool = (config.load(CONFIG_PATH) == OK)
	if loaded:
		_current_locale = config.get_value("translation", "locale", DEFAULT_LOCALE)
		# 0.4.5: compatible_mode → substr_mode 로 키 이름 변경. 옛 설정 1회 마이그레이션.
		if config.has_section_key("translation", "compatible_mode"):
			_substr_mode = bool(config.get_value("translation", "compatible_mode"))
			config.set_value("translation", "substr_mode", _substr_mode)
			config.erase_section_key("translation", "compatible_mode")
			config.save(CONFIG_PATH)
		else:
			_substr_mode = config.get_value("translation", "substr_mode", false)
		_batch_size = config.get_value("performance", "batch_size", DEFAULT_BATCH_SIZE)
		_batch_interval = config.get_value("performance", "batch_interval", DEFAULT_BATCH_INTERVAL)
	# whitelist: translator.gd 의 WHITELIST_PRESETS 를 순회, config 값이 없으면 preset default 사용
	_enabled_whitelist.clear()
	var presets: Dictionary = _load_whitelist_presets()
	for key in presets:
		var default_val: bool = presets[key].get("default", false)
		var saved = config.get_value("whitelist", key, default_val) if loaded else default_val
		_enabled_whitelist[key] = bool(saved)
	# addons: 기본값은 모두 false. 저장된 값이 있으면 그걸 사용.
	for key in _enabled_addons.keys():
		var saved_addon = config.get_value("addons", key, false) if loaded else false
		_enabled_addons[key] = bool(saved_addon)


# WHITELIST_PRESETS 정의는 translator.gd 에 있으므로 스크립트 상수로 읽어옴.
# 언어/번역 엔진이 로드되기 전에도 UI 에서 프리셋 목록이 필요하므로 여기서 정적 로드.
func _load_whitelist_presets() -> Dictionary:
	var script: GDScript = load(TRANSLATOR_SCRIPT) as GDScript
	if script == null:
		return {}
	var constants: Dictionary = script.get_script_constant_map()
	return constants.get("WHITELIST_PRESETS", {})


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
	win.size = Vector2i(880, 540)
	win.min_size = Vector2i(720, 460)
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

	# --- 탭 컨테이너 ---
	var tabs: TabContainer = TabContainer.new()
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tabs.tab_alignment = TabBar.ALIGNMENT_LEFT
	root.add_child(tabs)

	# ============ General 탭 ============
	var body: HBoxContainer = HBoxContainer.new()
	body.name = "General"
	body.add_theme_constant_override("separation", 12)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tabs.add_child(body)

	# 왼쪽: 언어 목록 + Substr 모드
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

	# Substr 모드 체크박스 (선택된 locale 의 substr_mode_label 텍스트 사용)
	var substr_check: CheckBox = CheckBox.new()
	var substr_default: String = "Substr Mode"
	var _substr_texts: Array = []
	for loc in enabled_locales:
		# locale.json 의 새 키 substr_mode_label 우선, 옛 키 compatible 도 fallback (구 locale.json 호환)
		_substr_texts.append(loc.get("substr_mode_label", loc.get("compatible", substr_default)))

	# 현재 선택 locale 의 텍스트로 초기화
	substr_check.text = "  " + _substr_texts[pre_select] if pre_select < _substr_texts.size() else substr_default
	substr_check.button_pressed = _substr_mode
	substr_check.add_theme_font_size_override("font_size", 12)
	left.add_child(substr_check)

	# 언어 선택 변경 시 체크박스 텍스트 갱신
	item_list.item_selected.connect(func(idx):
		if idx < _substr_texts.size():
			substr_check.text = "  " + _substr_texts[idx]
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

	# ============ Whitelist 탭 ============
	var wl_checks: Dictionary = _build_whitelist_tab(tabs)

	# ============ Addons 탭 ============
	var addon_checks: Dictionary = _build_addons_tab(tabs)

	# ============ Info 탭 ============
	# Defensive: any failure inside _build_info_tab is contained — the tab
	# either renders fully or with a fallback placeholder; it never disrupts
	# other tabs / runtime.
	_build_info_tab(tabs)

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
	var prev_substr: bool = _substr_mode
	var prev_batch_size: int = _batch_size
	var prev_batch_interval: float = _batch_interval
	var prev_whitelist: Dictionary = _enabled_whitelist.duplicate()
	var prev_addons: Dictionary = _enabled_addons.duplicate()
	_substr_mode = substr_check.button_pressed
	_batch_size = int(size_spin.value)
	_batch_interval = float(interval_spin.value)
	# whitelist 체크박스 상태 수집
	for key in wl_checks:
		_enabled_whitelist[key] = (wl_checks[key] as CheckBox).button_pressed
	# addon 체크박스 상태 수집
	for key in addon_checks:
		_enabled_addons[key] = (addon_checks[key] as CheckBox).button_pressed
	var batch_changed: bool = (_batch_size != prev_batch_size
		or not is_equal_approx(_batch_interval, prev_batch_interval))
	var whitelist_changed: bool = (_enabled_whitelist.hash() != prev_whitelist.hash())
	var addons_changed: bool = (_enabled_addons.hash() != prev_addons.hash())

	var selected_items: PackedInt32Array = item_list.get_selected_items()
	if selected_items.size() > 0:
		var sel_idx: int = selected_items[0]
		if sel_idx >= 0 and sel_idx < enabled_locales.size():
			var selected_locale: String = enabled_locales[sel_idx].get("locale", DEFAULT_LOCALE)
			var locale_changed: bool = selected_locale != _current_locale
			var substr_changed: bool = _substr_mode != prev_substr
			if locale_changed or substr_changed or batch_changed or whitelist_changed or addons_changed or is_startup:
				_current_locale = selected_locale
				_save_config()
				if not is_startup:
					# 배치 파라미터만 바뀌었으면 재초기화 없이 즉시 반영
					if batch_changed and not locale_changed and not substr_changed and not whitelist_changed and not addons_changed:
						if _translator_node != null and _translator_node.has_method("set_batch_params"):
							_translator_node.set_batch_params(_batch_size, _batch_interval)
					else:
						_apply_locale()

	win.queue_free()
	_language_window = null
	_ok_button = null


# ==========================================
# Whitelist 탭 빌더
# ==========================================

# translator.gd 의 WHITELIST_PRESETS 를 읽어 좌측 패널에 체크박스 목록 생성.
# 반환값: {key: CheckBox} — OK 버튼 처리 시 상태를 수집하기 위함.
# 우측 패널은 향후 "사용자 커스텀 키워드" 용으로 예약 (지금은 placeholder).
func _build_whitelist_tab(tabs: TabContainer) -> Dictionary:
	var checks: Dictionary = {}

	var tab_body: HBoxContainer = HBoxContainer.new()
	tab_body.name = "Whitelist"
	tab_body.add_theme_constant_override("separation", 12)
	tab_body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tabs.add_child(tab_body)

	# --- 왼쪽: 프리셋 체크박스 리스트 ---
	var wl_left: VBoxContainer = VBoxContainer.new()
	wl_left.add_theme_constant_override("separation", 8)
	wl_left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	wl_left.size_flags_stretch_ratio = 1.0
	tab_body.add_child(wl_left)

	var wl_title: Label = Label.new()
	wl_title.text = "Additional Priority Whitelist"
	wl_title.add_theme_font_size_override("font_size", 14)
	wl_left.add_child(wl_title)

	var wl_hint: Label = Label.new()
	wl_hint.text = "Enable if another mod overwrites in-game text periodically (e.g. HUD map name flicker with ImmersiveXP)."
	wl_hint.add_theme_font_size_override("font_size", 10)
	wl_hint.modulate = Color(0.55, 0.55, 0.55)
	wl_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	wl_left.add_child(wl_hint)

	wl_left.add_child(HSeparator.new())

	# 스크롤 컨테이너 (프리셋 많아질 경우 대비)
	var wl_scroll: ScrollContainer = ScrollContainer.new()
	wl_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	wl_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	wl_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	wl_left.add_child(wl_scroll)

	var wl_list: VBoxContainer = VBoxContainer.new()
	wl_list.add_theme_constant_override("separation", 10)
	wl_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	wl_scroll.add_child(wl_list)

	var presets: Dictionary = _load_whitelist_presets()
	if presets.is_empty():
		var empty_label: Label = Label.new()
		empty_label.text = "(No whitelist presets defined)"
		empty_label.add_theme_font_size_override("font_size", 11)
		empty_label.modulate = Color(0.45, 0.45, 0.45)
		wl_list.add_child(empty_label)
	else:
		for key in presets:
			var meta: Dictionary = presets[key]
			var nick: String = meta.get("nickname", key)
			var desc: String = meta.get("description", "")
			var row: VBoxContainer = VBoxContainer.new()
			row.add_theme_constant_override("separation", 2)
			wl_list.add_child(row)

			var check: CheckBox = CheckBox.new()
			check.text = "  %s" % nick
			check.add_theme_font_size_override("font_size", 12)
			check.button_pressed = _enabled_whitelist.get(key, false)
			row.add_child(check)
			checks[key] = check

			if desc != "":
				var desc_label: Label = Label.new()
				desc_label.text = "     " + desc
				desc_label.add_theme_font_size_override("font_size", 10)
				desc_label.modulate = Color(0.45, 0.45, 0.45)
				desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
				row.add_child(desc_label)

			var mod_list: Array = meta.get("mod_list", [])
			if mod_list.size() > 0:
				var mod_label: Label = Label.new()
				mod_label.text = "     Used with: " + ", ".join(mod_list)
				mod_label.add_theme_font_size_override("font_size", 10)
				mod_label.modulate = Color(0.55, 0.7, 0.55)
				row.add_child(mod_label)

			var key_label: Label = Label.new()
			key_label.text = "     keyword: " + key
			key_label.add_theme_font_size_override("font_size", 9)
			key_label.modulate = Color(0.35, 0.35, 0.35)
			row.add_child(key_label)

	# --- 세로 구분선 ---
	tab_body.add_child(VSeparator.new())

	# --- 오른쪽: 일괄 제어 패널 ---
	var wl_right: VBoxContainer = VBoxContainer.new()
	wl_right.add_theme_constant_override("separation", 8)
	wl_right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	wl_right.size_flags_stretch_ratio = 1.0
	tab_body.add_child(wl_right)

	var actions_title: Label = Label.new()
	actions_title.text = "Bulk Actions"
	actions_title.add_theme_font_size_override("font_size", 14)
	wl_right.add_child(actions_title)

	var actions_hint: Label = Label.new()
	actions_hint.text = "Toggle all whitelist presets at once."
	actions_hint.add_theme_font_size_override("font_size", 10)
	actions_hint.modulate = Color(0.55, 0.55, 0.55)
	actions_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	wl_right.add_child(actions_hint)

	wl_right.add_child(HSeparator.new())

	# Activate All — 모든 preset 켜기
	var btn_all: Button = Button.new()
	btn_all.text = "Activate All"
	btn_all.add_theme_font_size_override("font_size", 12)
	btn_all.pressed.connect(func():
		for key in checks:
			(checks[key] as CheckBox).button_pressed = true
	)
	wl_right.add_child(btn_all)

	# Deactivate All — 모든 preset 끄기
	var btn_none: Button = Button.new()
	btn_none.text = "Deactivate All"
	btn_none.add_theme_font_size_override("font_size", 12)
	btn_none.pressed.connect(func():
		for key in checks:
			(checks[key] as CheckBox).button_pressed = false
	)
	wl_right.add_child(btn_none)

	# 하단 — 향후 사용자 커스텀 키워드 입력 영역 placeholder
	var spacer: Control = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	wl_right.add_child(spacer)

	var future_label: Label = Label.new()
	future_label.text = "Custom keyword input — planned for a future version"
	future_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	future_label.add_theme_font_size_override("font_size", 10)
	future_label.modulate = Color(0.35, 0.35, 0.35)
	future_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	wl_right.add_child(future_label)

	return checks


# ==========================================
# Addons 탭 빌더
# ==========================================
#
# 각 mod 호환성 addon 의 on/off 체크박스 + 우측 Bulk Actions.
# 좌측: 알려진 mod 별 addon 항목 (현재는 ImmersiveXP prefix 처리만).
# 우측: Activate All / Deactivate All (Whitelist 탭과 동일한 패턴).
# 기본값은 모두 OFF — 사용자가 해당 mod 를 실제로 사용 중일 때만 활성화.
func _build_addons_tab(tabs: TabContainer) -> Dictionary:
	var checks: Dictionary = {}

	var tab_body: HBoxContainer = HBoxContainer.new()
	tab_body.name = "Addons"
	tab_body.add_theme_constant_override("separation", 12)
	tab_body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tabs.add_child(tab_body)

	# --- 왼쪽: addon 체크박스 리스트 ---
	var ad_left: VBoxContainer = VBoxContainer.new()
	ad_left.add_theme_constant_override("separation", 8)
	ad_left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ad_left.size_flags_stretch_ratio = 1.0
	tab_body.add_child(ad_left)

	var ad_title: Label = Label.new()
	ad_title.text = "Mod Compatibility Addons"
	ad_title.add_theme_font_size_override("font_size", 14)
	ad_left.add_child(ad_title)

	var ad_hint: Label = Label.new()
	ad_hint.text = "Enable an addon only if you have the corresponding mod installed. Default: all OFF."
	ad_hint.add_theme_font_size_override("font_size", 10)
	ad_hint.modulate = Color(0.55, 0.55, 0.55)
	ad_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ad_left.add_child(ad_hint)

	ad_left.add_child(HSeparator.new())

	# 스크롤 컨테이너 (향후 addon 항목 늘어날 경우 대비)
	var ad_scroll: ScrollContainer = ScrollContainer.new()
	ad_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ad_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	ad_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	ad_left.add_child(ad_scroll)

	var ad_list: VBoxContainer = VBoxContainer.new()
	ad_list.add_theme_constant_override("separation", 10)
	ad_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ad_scroll.add_child(ad_list)

	# --- ImmersiveXP prefix 처리 addon ---
	var imxp_row: VBoxContainer = VBoxContainer.new()
	imxp_row.add_theme_constant_override("separation", 2)
	ad_list.add_child(imxp_row)

	var imxp_check: CheckBox = CheckBox.new()
	imxp_check.text = "  ImmersiveXP — Tooltip prefix handling"
	imxp_check.add_theme_font_size_override("font_size", 12)
	imxp_check.button_pressed = _enabled_addons.get("immersivexp_prefix", false)
	imxp_row.add_child(imxp_check)
	checks["immersivexp_prefix"] = imxp_check

	var imxp_desc: Label = Label.new()
	imxp_desc.text = "     Strip the `\\n.\\n` / `\\n\\n` prefix that Oldman's Immersive Overhaul (ImmersiveXP/HUD.gd) prepends to tooltip labels, so the inner text is translated through all match tiers (literal/static/scoped/pattern/substr). Reattaches the prefix afterward."
	imxp_desc.add_theme_font_size_override("font_size", 10)
	imxp_desc.modulate = Color(0.45, 0.45, 0.45)
	imxp_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	imxp_row.add_child(imxp_desc)

	var imxp_mod: Label = Label.new()
	imxp_mod.text = "     Used with: Oldman's Immersive Overhaul (modworkshop/50811)"
	imxp_mod.add_theme_font_size_override("font_size", 10)
	imxp_mod.modulate = Color(0.55, 0.7, 0.55)
	ad_list.add_child(imxp_mod)

	# --- 세로 구분선 ---
	tab_body.add_child(VSeparator.new())

	# --- 오른쪽: 일괄 제어 패널 ---
	var ad_right: VBoxContainer = VBoxContainer.new()
	ad_right.add_theme_constant_override("separation", 8)
	ad_right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ad_right.size_flags_stretch_ratio = 1.0
	tab_body.add_child(ad_right)

	var actions_title: Label = Label.new()
	actions_title.text = "Bulk Actions"
	actions_title.add_theme_font_size_override("font_size", 14)
	ad_right.add_child(actions_title)

	var actions_hint: Label = Label.new()
	actions_hint.text = "Toggle all mod compatibility addons at once."
	actions_hint.add_theme_font_size_override("font_size", 10)
	actions_hint.modulate = Color(0.55, 0.55, 0.55)
	actions_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ad_right.add_child(actions_hint)

	ad_right.add_child(HSeparator.new())

	# Activate All
	var btn_all: Button = Button.new()
	btn_all.text = "Activate All"
	btn_all.add_theme_font_size_override("font_size", 12)
	btn_all.pressed.connect(func():
		for key in checks:
			(checks[key] as CheckBox).button_pressed = true
	)
	ad_right.add_child(btn_all)

	# Deactivate All
	var btn_none: Button = Button.new()
	btn_none.text = "Deactivate All"
	btn_none.add_theme_font_size_override("font_size", 12)
	btn_none.pressed.connect(func():
		for key in checks:
			(checks[key] as CheckBox).button_pressed = false
	)
	ad_right.add_child(btn_none)

	return checks


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
	node._substr_mode = _substr_mode
	node.normal_batch_size = _batch_size
	node.normal_batch_interval = _batch_interval
	node.enabled_whitelist = _enabled_whitelist.duplicate()
	# Mod compatibility addons (default OFF)
	node.addon_immersivexp_prefix = _enabled_addons.get("immersivexp_prefix", false)
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


# ==========================================
# Info 탭 — Mod metadata view
# ==========================================
# Reads <pkg_root>/info.json (built by tools/utils/build_mod_info.py).
# Defensive at every step: missing file / malformed JSON / unexpected
# field types fall back to placeholder text. Failures here MUST NOT
# affect other tabs or runtime translation.

const INFO_JSON_PATH: String = "res://Trans To Vostok/info.json"


func _load_info_json() -> Dictionary:
	# Returns {} on any error. Caller uses .get() with defaults.
	if not FileAccess.file_exists(INFO_JSON_PATH):
		return {}
	var f: FileAccess = FileAccess.open(INFO_JSON_PATH, FileAccess.READ)
	if f == null:
		return {}
	var text: String = f.get_as_text()
	f.close()
	if text.is_empty():
		return {}
	var parsed: Variant = JSON.parse_string(text)
	if not (parsed is Dictionary):
		return {}
	return parsed


func _safe_get_string(d: Dictionary, key: String, fallback: String) -> String:
	if d.has(key) and d[key] is String:
		return d[key]
	return fallback


func _safe_get_array(d: Dictionary, key: String) -> Array:
	if d.has(key) and d[key] is Array:
		return d[key]
	return []


func _safe_get_dict(d: Dictionary, key: String) -> Dictionary:
	if d.has(key) and d[key] is Dictionary:
		return d[key]
	return {}


func _add_kv_row(parent: VBoxContainer, key_text: String, value_text: String) -> void:
	var line: Label = Label.new()
	line.text = key_text + " : " + value_text
	line.add_theme_font_size_override("font_size", 12)
	parent.add_child(line)


func _add_section_title(parent: VBoxContainer, title: String) -> void:
	var l: Label = Label.new()
	l.text = title
	l.add_theme_font_size_override("font_size", 13)
	l.modulate = Color(0.85, 0.85, 0.95)
	parent.add_child(l)


func _add_name_list(parent: VBoxContainer, names: Array, indent: String = "    ") -> void:
	if names.is_empty():
		var none_l: Label = Label.new()
		none_l.text = indent + "(none)"
		none_l.add_theme_font_size_override("font_size", 11)
		none_l.modulate = Color(0.55, 0.55, 0.55)
		parent.add_child(none_l)
		return
	for entry in names:
		var name: String = ""
		if entry is String:
			name = entry
		else:
			name = str(entry)
		if name.is_empty():
			continue
		var l: Label = Label.new()
		l.text = indent + "• " + name
		l.add_theme_font_size_override("font_size", 11)
		parent.add_child(l)


func _build_info_tab(tabs: TabContainer) -> void:
	var tab_body: HBoxContainer = HBoxContainer.new()
	tab_body.name = "Info"
	tab_body.add_theme_constant_override("separation", 12)
	tab_body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tabs.add_child(tab_body)

	var info: Dictionary = _load_info_json()
	var locales: Dictionary = _safe_get_dict(info, "locales")
	var current: Dictionary = _safe_get_dict(locales, _current_locale)

	# ===== Left: Mod Info =====
	var info_left: VBoxContainer = VBoxContainer.new()
	info_left.add_theme_constant_override("separation", 6)
	info_left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info_left.size_flags_stretch_ratio = 1.0
	tab_body.add_child(info_left)

	var meta_title: Label = Label.new()
	meta_title.text = "Mod Info"
	meta_title.add_theme_font_size_override("font_size", 14)
	info_left.add_child(meta_title)

	info_left.add_child(HSeparator.new())

	_add_kv_row(info_left, "Mod Version    ",
		_safe_get_string(info, "mod_version", "(unknown)"))
	_add_kv_row(info_left, "Built          ",
		_safe_get_string(info, "build_date", "(unknown)"))
	_add_kv_row(info_left, "Target Game Ver",
		_safe_get_string(info, "target_game_version", "(unknown)"))

	var locale_title: Label = Label.new()
	locale_title.text = "Selected Locale: " + _current_locale
	locale_title.add_theme_font_size_override("font_size", 12)
	locale_title.modulate = Color(0.85, 0.85, 0.95)
	info_left.add_child(locale_title)

	_add_kv_row(info_left, "Translation Upd",
		_safe_get_string(current, "translation_updated", "(unknown)"))

	if info.is_empty():
		var fallback_hint: Label = Label.new()
		fallback_hint.text = "(info.json not found — fallback values shown)"
		fallback_hint.add_theme_font_size_override("font_size", 10)
		fallback_hint.modulate = Color(0.7, 0.55, 0.45)
		fallback_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		info_left.add_child(fallback_hint)

	# ===== Vertical separator =====
	tab_body.add_child(VSeparator.new())

	# ===== Right: Contributors =====
	var info_right: VBoxContainer = VBoxContainer.new()
	info_right.add_theme_constant_override("separation", 6)
	info_right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info_right.size_flags_stretch_ratio = 1.0
	tab_body.add_child(info_right)

	var contrib_title: Label = Label.new()
	contrib_title.text = "Contributors"
	contrib_title.add_theme_font_size_override("font_size", 14)
	info_right.add_child(contrib_title)

	info_right.add_child(HSeparator.new())

	var contrib_scroll: ScrollContainer = ScrollContainer.new()
	contrib_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	contrib_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	contrib_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	info_right.add_child(contrib_scroll)

	var contrib_list: VBoxContainer = VBoxContainer.new()
	contrib_list.add_theme_constant_override("separation", 2)
	contrib_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	contrib_scroll.add_child(contrib_list)

	# Project-wide sections (locale-agnostic)
	_add_section_title(contrib_list, "Lead Developer")
	_add_name_list(contrib_list, _safe_get_array(info, "lead_developer"))

	_add_section_title(contrib_list, "Code Contributors")
	_add_name_list(contrib_list, _safe_get_array(info, "code_contributors"))

	var ack: Array = _safe_get_array(info, "acknowledgments")
	if not ack.is_empty():
		_add_section_title(contrib_list, "Acknowledgments")
		_add_name_list(contrib_list, ack)

	var spacer: Label = Label.new()
	spacer.text = ""
	contrib_list.add_child(spacer)

	# Per-locale sections (current locale)
	_add_section_title(contrib_list, "Translators (" + _current_locale + ")")
	_add_name_list(contrib_list, _safe_get_array(current, "translators"))

	_add_section_title(contrib_list, "Translation Contributors (" + _current_locale + ")")
	_add_name_list(contrib_list, _safe_get_array(current, "translation_contributors"))

	_add_section_title(contrib_list, "Image Reworkers (" + _current_locale + ")")
	_add_name_list(contrib_list, _safe_get_array(current, "texture_reworkers"))

	_add_section_title(contrib_list, "Image Contributors (" + _current_locale + ")")
	_add_name_list(contrib_list, _safe_get_array(current, "texture_contributors"))
