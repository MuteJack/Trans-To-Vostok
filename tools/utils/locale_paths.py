"""Shared path resolution for per-locale canonical TSV directories.

Centralizes the convention `Translations/<locale>/<CANONICAL_SUBDIR>/<category>/`
so all tools (rebuild_xlsx, apply_to_repo, build_source, push_diff, etc.) stay
consistent if the layout changes again.

Layout (post 0.6.0 cleanup):
    Translations/
        <locale>/
            Translation.xlsx        (working copy, gitignored)
            Texture.xlsx            (working copy, gitignored)
            tsv/                    ← canonical TSV root for this locale
                Translation/
                    Main.tsv
                    Items.tsv
                    ...
                    _sheet_order.txt
                Texture/
                    Tutorial.tsv
                    UI.tsv
                    Signs.tsv
                    Structures.tsv
                    _sheet_order.txt
            textures/               (PNG source assets, hand-authored)
            .log/                   (validation logs, gitignored)
"""
from pathlib import Path

# Subdirectory under Translations/<locale>/ that holds canonical TSV trees.
# Single source of truth — change this and every tool follows.
CANONICAL_SUBDIR = "tsv"


def canonical_dir(translations_root: Path, locale: str, category: str) -> Path:
    """Return the canonical TSV directory for one (locale, category) pair.

    Example:
        canonical_dir(REPO/"Translations", "Korean", "Translation")
            -> REPO/"Translations"/"Korean"/"tsv"/"Translation"
    """
    return translations_root / locale / CANONICAL_SUBDIR / category


def canonical_root(translations_root: Path, locale: str) -> Path:
    """Return the canonical TSV root for one locale (parent of all categories).

    Example:
        canonical_root(REPO/"Translations", "Korean")
            -> REPO/"Translations"/"Korean"/"tsv"
    """
    return translations_root / locale / CANONICAL_SUBDIR
