**Supported Languages**

- **English** (game's default)
- **Korean / 한국어** (Primary Target, texture reworked)
- **日本語 / Japanese** (Tutorial Billboard textures added)
- **Magyar / Hungarian** (Tutorial Billboard textures added) : Translation by Papp Csaba
- **Français / French** (Prototyped, Tutorial Billboard textures added)
- **Português (Brasil)** (Prototyped, texture pending)
- **Deutsch / German** (Prototyped, texture pending)
- **Español / Spanish (LatAm)** (Prototyped, texture pending)
- **简体中文 / Chineese (Simplified)** (Prototyped, texture pending)
- **繁體中文 / Chineese (Traditional)** (Prototyped, texture pending)
- **Русский / Russian** (Prototyped, texture pending)

> Most non-Korean languages are machine-translated drafts via DeepL/Claude API.
> Community refinement via [Crowdin](https://crowdin.com/project/trans-to-vostok) is always welcome.

**Compatible Mods** (tested — compatibility may not always be guaranteed)

- *Expanded Storage* by jakiepoo — [https://modworkshop.net/mod/56126](https://modworkshop.net/mod/56126)
- *Oldman's Immersive Overhaul* (ImmersiveXP) — [https://modworkshop.net/mod/50811](https://modworkshop.net/mod/50811)
- *Trader Refresh Hotkey* (temporary fix by metro) — [https://modworkshop.net/mod/55933](https://modworkshop.net/mod/55933)

---

# Trans To Vostok

A multilingual translation mod for Road to Vostok.

> **NOTE:** *This mod and its translation ToolBox ([GitHub](https://github.com/MuteJack/Trans-to-Vostok)) are currently under development.*

> **Translation contributions are accepted through [Crowdin](https://crowdin.com/project/trans-to-vostok).**
> Join and start translating directly in the browser — no setup required. [Trans to Vostok on Crowdin](https://crowdin.com/project/trans-to-vostok).
> Translation-only Pull Requests on [GitHub](https://github.com/MuteJack/Trans-to-Vostok) are no longer accepted; please use Crowdin instead.
> Maintainers periodically sync Crowdin → repository; changes ship with the next mod release.

![3_Trans2Vostok_Main_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/3_Trans2Vostok_Main_Korean.png)

## 1. Introduction

**Trans To Vostok** is a mod under development to support multilingual localization for Road to Vostok.
It aims to deliver **complete, non-missing translation** across all translatable game content — UI, items, quests, interactions, and more.

## 2. Key Features

### Main Features

1. **Game Translation** (core feature)
   - Translates in-game UI, tooltips, item names, event descriptions, trader dialogue, and more.
2. **Image / Texture Translation** (added in v0.3.0)
   - Replaces game textures with localized versions at runtime (e.g. Tutorial Billboard).
   - Composites translated overlays onto original textures at runtime (e.g. Road Signs — avoids shipping modified or original game assets).
   - **Note**: Translated textures are hand-crafted (reconstructed) and may include hand-drawn work or copyright-free assets, so some icons may differ slightly from the originals (e.g. the Performance icon and Permadeath skull icon on the Tutorial Billboards).
     ![9_Trans2Vostok_Texture_TutorialBillBoard2.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/9_Trans2Vostok_Texture_TutorialBillBoard2.png)
3. **UI Support**
   - Opens a language selection UI via the **`F9`** hotkey.
   - Switch languages at runtime without restarting the game.
   - Performance options (batch size / interval), Whitelist toggles, Mod-compatibility addon toggles, and the optional Substr Mode are all configured here.
     ![2_Trans2Vostok_Lang_Sel.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/2_Trans2Vostok_Lang_Sel.png)
4. **Priority Whitelist** (added in v0.3.1)
   - Path-keyword presets that force per-frame priority translation for specific UI areas (HUD map label, inventory, trader UI, etc.).
   - When another mod periodically overwrites game text faster than the default batch cycle can keep up (e.g. flickering), enabling the relevant preset eliminates it.
   - Toggle via the **Whitelist** tab in the F9 UI. All presets default OFF.
5. **Mod Compatibility Addons** (added in v0.5.0)
   - Per-mod runtime helpers that handle label patterns introduced by other mods (e.g. prefixes prepended to every tooltip).
   - Toggle in the **Addons** tab of the F9 UI.
   - Example: **ImmersiveXP** (Oldman's Immersive Overhaul) — the interact-dot feature is implemented as `{text}` → `\n.\n{text}`, which causes translation lookups to fail.

### Internal Mechanics

6. **Text Position Realignment**

   - When translation changes text length, **on-screen layout can shift** (e.g. `A: B` layouts like tooltip's "Weight: 0.8kg").
   - Measures the translated label's actual font width and auto-adjusts the Value node's offset.
     - Targets: `Label` nodes with a child `Value` Label (manual positioning)
     - Auto-aligns "label: [value]" patterns in tooltips, inventory stats, etc.
     - **Disabled in Substr Mode** — avoids interfering with game scene structure.
7. **1:1 Property-Based Translation** (Precision Matching)

   - Instead of simple text substitution, translation targets are specified directly via **Godot node structural identifiers**:
   - ``(location, parent, name, type, text) → translation``
     - `location`: Scene file path (e.g. `UI/Interface`)
     - `parent`: Parent node path within the scene (e.g. `Tools/Notes`)
     - `name`: Node name (e.g. `Hint`)
     - `type`: Godot node class (e.g. `Label`)
     - `text`: Original source text
   - **The same word can be translated differently depending on which UI/node it appears in** — prevents mismatches, enables context-aware translation.
     - Example: NVG (Night Vision Goggle) can show the full name in settings but "NVG" everywhere else.
8. **N-Tier Fallback Matching**

   - Looks up translations through 9 tiers, from specific context to generic substitution:

   | Tier | Match Method                                 | Notes                                |
   | ---- | -------------------------------------------- | ------------------------------------ |
   | 1    | **static exact** — all 5 fields match | All fields match exactly             |
   | 2    | **scoped literal exact**               | Dynamic text (runtime assignment)    |
   | 3    | **scoped pattern exact**               | Regex + scene context                |
   | 4    | **literal global**                     | Full text match (global)             |
   | 5    | **pattern global**                     | Regex (global)                       |
   | 6    | **static score**                       | Partial context match (+8/+4/+2/+1)  |
   | 7    | **scoped literal score**               | Dynamic text, partial context        |
   | 8    | **scoped pattern score**               | Regex + partial context              |
   | 9    | **substr**                             | Substring substitution (last resort) |
9. **Substr Mode** (not recommended for normal use)

   - Temporary fallback for when a game update breaks the structural matching of tiers 1–8.
     (Treats all literal/static entries as substr entries)
   - Toggle on/off via checkbox in the F9 UI.

## 3. Installation

> **NOTE:** This mod requires a mod loader such as MetroModLoader.

1. Install **MetroModLoader** or **VostokMods** for Godot:
   [https://modworkshop.net/mod/55623](https://modworkshop.net/mod/55623)
   ![1776508272457](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/1.Metro_MoadLoader.png)
2. Download `Trans To Vostok.zip` and copy it into the game's `mods/` folder.
   e.g. `C:\Program Files (x86)\Steam\steamapps\common\Road to Vostok\mods\`
   or: `D:\SteamLibrary\steamapps\common\Road to Vostok\mods\`
3. Launch the game — it starts in the default language (English).
4. Press **F9** to open the language selection UI and switch to your preferred language.
5. If some text **flickers** while another mod is active, open F9 → **Whitelist** tab and enable the relevant preset (e.g. *HUD Map Label* for ImmersiveXP).
   - This stems from the other mod refreshing a specific label every frame.
   - The **Whitelist** marks specific UI areas as "always re-translate every frame", eliminating the flicker.
6. If some text **isn't translating properly** while another mod is active, open F9 → **Addons** tab and enable the relevant addon (e.g. *ImmersiveXP* — handles the `\n.\n` / `\n\n` tooltip prefix).

## 4. Supported Languages

1. **English**: The game's default language.
2. **Korean (한국어)**: Directly translated and reviewed by the lead developer; retranslated and texture-reworked first on every game version bump. (Lead developer's native language.)
3. **French (Français)**: Added in v0.4.0 — DeepL initial machine translation (text only; texture pending).
4. **Português (Brasil)**: Added in v0.5.1
5. **Deutsch / Español (LatAm) / 日本語 / 简体中文 / 繁體中文**: Added in v0.5.3
6. **Русский**: Added in v0.6.1
7. **Hungarian (Magyar)**: Added in v0.6.2 (translation by Papp Csaba)
8. **Italiano / Hungarian**: Planned
9. Other languages: To be added based on development progress and community requests.

### 4.1. Text Translation / Proofreading (Crowdin)

All translations are managed through [Crowdin](https://crowdin.com/project/trans-to-vostok).

- Contribute translations: Sign up on [Crowdin](https://crowdin.com/project/trans-to-vostok) and start working directly in the browser (no setup required).
- Contribution support via the ToolBox ([GitHub Repo](https://github.com/MuteJack/Trans-to-Vostok)) is still under development.
- Credits are automatically added using the name configured on Crowdin.
- New language requests / general feedback: Submit a [GitHub issue](https://github.com/MuteJack/Trans-to-Vostok/issues) (to be published).

### 4.2. Text Translation (Local Environment, in preparation)

This environment is for contributors with development knowledge. ([GitHub Repository](https://github.com/MuteJack/Trans-to-Vostok))
A workflow guide will be published once the documentation is complete.

### 4.3. Texture Translation

All textures are currently hand-crafted by the lead developer.

- Texture text is managed via Crowdin through `Texture/{sheetname}.tsv`.
- Due to the hand-crafted nature, text in textures may differ slightly from Crowdin (e.g. length constraints).
- To contribute translated textures directly, workflow documentation is currently being prepared.
  - For now, send the file with the name you'd like credited to coldman1224@outlook.com and it will be manually reflected in the repo.
  - Or, if you have development knowledge (Git, [GitHub](https://github.com/MuteJack/Trans-to-Vostok)), submit via Pull Request.

## 5. Attribution

Translated texture assets are a mix of hand-crafted work, license-free assets, and third-party data sources. Per-file source credits are listed in **`Trans To Vostok/<locale>/Texture_Attribution.md`** inside the mod zip.

Per-locale translator credit (text + texture) is in **`Trans To Vostok/<locale>/Translation_Credit.md`**.

The project-wide author / translator / contributor list is in `AUTHORS.md` at the repository root.

All three files are auto-generated/updated by the repository Toolbox.

========================================

# Screenshots

**Trans to Vostok**
![4_Trans2Vostok_New_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/4_Trans2Vostok_New_Korean.png)

![5_Trans2Vostok_Cabin_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/5_Trans2Vostok_Cabin_Korean.png)

![6_Trans2Vostok_Settings_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/6_Trans2Vostok_Settings_Korean.png)

![7_Trans2Vostok_Tutorial_Crate.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/7_Trans2Vostok_Tutorial_Crate.png)

![8_Trans2Vostok_Texture_TutorialBillBoard1.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/8_Trans2Vostok_Texture_TutorialBillBoard1.png)

![10_Trans2Vostok_UI_WorldMap_Korean.png](https://raw.githubusercontent.com/MuteJack/Trans-to-Vostok/master/README/image/10_Trans2Vostok_UI_WorldMap_Korean.png)
