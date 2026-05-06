# Trans To Vostok — Mod compatibility addon module
#
# Per-mod runtime helpers for label-text patterns that other mods inject
# (typically prefixes prepended to existing label text). Each addon is
# feature-gated via translator_ui's "Addons" tab so that users only
# enable the ones for mods they actually have installed.
#
# Currently supported:
#   - ImmersiveXP (Oldman's Immersive Overhaul, modworkshop/50811)
#     ImmersiveXP/HUD.gd:30,32 prepends one of the following prefixes
#     to tooltip-style labels (interact-dot feature):
#         "\n\n"   (when aiming)
#         "\n.\n"  (interact-dot mode, default)
#     We detect and strip these before translation lookup so that ALL
#     tiers (static / literal_scoped / pattern_scoped / literal_global
#     / pattern_global / score-based / substr) hit the inner text.
#     The prefix is reattached to the translated result.
#
# Helpers are static — translator.gd holds the on/off state and calls
# these helpers conditionally.

# Note: not using `class_name ModAddon` because ModLoader-mounted mods
# are not registered in Godot's global class cache. Callers must
# `preload("res://Trans To Vostok/mod_addon.gd")` instead.
extends Node


# ImmersiveXP HUD.gd 가 prepend 하는 prefix 형태.
# 긴 것을 먼저 시도해야 (`"\n.\n"` 이 `"\n\n"` 보다 먼저 매치되도록).
const IMMERSIVEXP_PREFIXES: Array = ["\n.\n", "\n\n"]


# 입력 텍스트의 시작이 ImmersiveXP prefix 면 strip 한 inner text 와 prefix 자체를
# 반환. 만약 누적 (e.g. "\n.\n\n.\nGeneralist") 되어도 모두 strip 되어 inner 까지 도달.
# 일치 안 하면 stripped=text, prefix="" 그대로 반환.
#
# 반환: {"stripped": String, "prefix": String}
static func strip_immersivexp_prefix(text: String) -> Dictionary:
	var stripped: String = text
	var total_prefix: String = ""
	var changed: bool = true
	while changed:
		changed = false
		for prefix in IMMERSIVEXP_PREFIXES:
			if stripped.begins_with(prefix):
				stripped = stripped.substr(prefix.length())
				total_prefix += prefix
				changed = true
				break
	return {"stripped": stripped, "prefix": total_prefix}
