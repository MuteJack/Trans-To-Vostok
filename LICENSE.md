# Trans To Vostok — Licensing Overview

This repository contains content under multiple licenses, depending on the
asset type. **You must check the appropriate license before redistributing
or modifying any part of this repository.**

| Asset Type                                | License        | File                  |
| ----------------------------------------- | -------------- | --------------------- |
| Code (Python tools, GDScript, batch)      | Apache 2.0     | `LICENSE-CODE`        |
| Translation text (Translation, Glossary)  | CC BY 4.0      | `LICENSE-TRANSLATION` |
| Texture / Image assets                    | CC BY 4.0      | `LICENSE-TEXTURE`     |

For the contributor / translator name list referenced by these licenses,
see [`AUTHORS.md`](AUTHORS.md).

For Apache 2.0 attribution (which legally requires preservation), see
[`NOTICE`](NOTICE).

## Important Disclaimers

### Original Game Content
The **Road to Vostok** game itself, its in-game source text, and its
original assets are NOT covered by any license in this repository. They
remain the copyright of the Road to Vostok game developers. The licenses
here apply ONLY to the translation work and tooling produced by this
project — not to the original material being translated.

### Texture Asset Disclaimers
Texture and image assets may incorporate data from third-party sources
(Copernicus Sentinel-2, National Land Survey of Finland, etc.). These
upstream sources retain their own license terms and attribution
requirements that you must preserve in any redistribution. See
`LICENSE-TEXTURE` for details and per-file attribution in
`Trans To Vostok/<locale>/Texture_Attribution.md`.

The image assets are provided **without warranty of any kind**. The
authors and contributors are not responsible for any consequences arising
from their use, modification, or redistribution.

## License Summary (informal — see individual files for legal terms)

- **Code (Apache 2.0)**: Free use, modification, and redistribution,
  including for commercial purposes. The `NOTICE` file with attribution
  must be preserved in derivative works.
- **Translation text (CC BY 4.0)**: Free use, modification, and
  redistribution. Attribution to the author / translators / contributors
  is required.
- **Textures (CC BY 4.0)**: Same as translation text, plus you must
  preserve upstream third-party attributions and accept the warranty
  disclaimer.

## What is a "Derivative"?

For licensing purposes, a "derivative" is any work that is **based on or
incorporates** parts of this repository. It is NOT the same as merely
using the mod.

**Counts as a derivative (license obligations apply):**
- Forking this repository and redistributing your modified version.
- Copying our Python tools / GDScript code into another project.
- Reusing our translation text in another translation project.
- Including our textures / images in another mod or game.
- Re-uploading this mod (modified or unmodified) on another platform.

**Does NOT count as a derivative (no obligations):**
- Installing and playing the game with this mod.
- Running our tools on your own files (the tools' output is yours).
- Writing your own translation independently, without copying ours.
- Reviewing, criticizing, or referencing this mod in articles / videos.

## What Must Be Preserved When Redistributing

The exact set depends on which parts of this repository your derivative
includes. Keep only what corresponds to content you actually carry over.

| Content included in your derivative | Files you MUST preserve                                                                                  |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Code (any Python / GDScript / batch) | `LICENSE-CODE` + `NOTICE` + relevant entries in `AUTHORS.md`                                             |
| Translation text (any locale)        | `LICENSE-TRANSLATION` + that locale's `Translation_Credit.md`                                            |
| Texture / image assets               | `LICENSE-TEXTURE` + that locale's `Texture_Attribution.md` + that locale's `Translation_Credit.md`       |
| The whole repo as-is                 | All license files + `NOTICE` + `AUTHORS.md` + every locale's `Texture_Attribution.md` & `Translation_Credit.md` |

**You may remove**:
- Entries in `AUTHORS.md`, `NOTICE`, `Translation_Credit.md`, or
  `Texture_Attribution.md` that refer to content you have **fully
  removed** from your derivative.
- License files for content types you do not include (e.g., if your
  derivative uses only the code, you do not need `LICENSE-TEXTURE`).

**You may NOT remove**:
- License files for content types still present in your derivative.
- Attribution entries for content still present.
- Upstream third-party attributions in `Texture_Attribution.md` for
  images you still distribute (Copernicus / MML / etc. — these are
  required by the upstream sources, not by us, and apply regardless of
  this repository's license).

## Upstream Attributions Are Separate

Some texture assets incorporate data from external sources whose
licenses require attribution **independently of this repository's
license**. Even if you replace `LICENSE-TEXTURE` with your own license
in your derivative, you must still preserve the upstream attribution
notes in `Texture_Attribution.md` for any images of those sources you
continue to distribute.

Currently identified upstream sources include (non-exhaustive):
- **Copernicus Sentinel-2** satellite data
- **National Land Survey of Finland (Maanmittauslaitos / MML)** map data
- Various Pixabay, Texturelabs, and other image source contributions

See `Trans To Vostok/<locale>/Texture_Attribution.md` for the per-file
list as it stands at the time of distribution.

## Questions

If you have questions about licensing, please open an issue on the
project's repository or contact the author.
