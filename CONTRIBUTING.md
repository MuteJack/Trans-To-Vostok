# Contributing to Trans To Vostok

Thank you for your interest in contributing to Trans To Vostok.

> **Note**: This document currently covers only the basic "how to be
> credited" flow. Detailed contribution guidelines (style, PR process,
> review checklist, license agreement, etc.) will be added later.

---

## How to be credited

Your name is added to `AUTHORS.md` (and `Translation_Credit.md` for the
locale you contributed to) **automatically** on the next build. Do NOT
edit `AUTHORS.md` directly — the Translators section is regenerated on
every build, and any direct edits there will be overwritten.

To be credited, edit the appropriate xlsx file:

### As a translator (text)

Edit `Trans To Vostok/<locale>/Translation.xlsx` → **MetaData** sheet:

| Role         | Field in MetaData          |
| ------------ | -------------------------- |
| Lead         | `Translator`               |
| Contributor  | `Contributor (Translate)`  |

For multiple names in one cell, separate by **line breaks** (`Alt+Enter`
inside the cell in Excel).

### As a texture / image worker

Edit `Trans To Vostok/<locale>/Texture.xlsx`:

| Role           | Column in any sheet  |
| -------------- | -------------------- |
| Primary rework | `Reworked by`        |
| Secondary help | `Contributors`       |

Same rule for multiple names: line break (`Alt+Enter`) inside the cell.

### As a code contributor (Python tools / GDScript)

There is no programmatic data source for code contributions, so this is
the only category that requires editing `AUTHORS.md` directly. Add an
entry under the **Code Contributors** section using this format:

```
- **Name (or handle)** <email or contact>
  - Brief description of contribution
```

This section sits OUTSIDE the auto-generated markers, so it is
preserved across builds.

---

## After editing

Run the build to regenerate the credit files:

```
python tools/build_mod_package.py
```

Or just commit the xlsx changes — the maintainer will run the build at
release time.

---

## (Reserved for future expansion)

The following areas of the contribution guide will be filled in later:

- Project overview and scope
- Code style guidelines
- Pull request checklist
- Translation style / glossary policy
- License agreement for contributions
- Review process

For now, please open an issue if you have any questions.
