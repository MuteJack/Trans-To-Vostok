# Crowdin_Mirror

**Staging / cache area for Crowdin sync.** Mirrors Crowdin's authoritative
state locally so we can inspect, debug, and re-run sync steps without
hitting Crowdin's API repeatedly.

> **Not git-tracked** (see `.gitignore`). Contents are regenerable from
> canonical xlsx / TSV via `tools/crowdin/` adapters. Crowdin itself is
> the source-of-truth for translation work in progress.

## Layout

```
Crowdin_Mirror/
├── source/                          # English source pushed to Crowdin
│   ├── Translation/
│   │   ├── Main.tsv
│   │   ├── Interface.tsv
│   │   └── ...
│   ├── Glossary/
│   │   └── Main.tsv
│   └── Texture/
│       ├── Tutorial.tsv
│       └── UI.tsv
└── translations/                    # Translations pulled from Crowdin
    ├── Korean/
    │   ├── Translation/
    │   ├── Glossary/
    │   └── Texture/
    ├── French/
    └── Portuguese_BR/
```

## TSV columns (Crowdin push format)

| Column | Crowdin role | Source |
| --- | --- | --- |
| `identifier` | string identifier (file-unique) | composite of filename:parent:name:type:property:unique_id (or text-hash for global rows) |
| `source_phrase` | source text | `text` (English) |
| `context` | context for translators | `DESCRIPTION` (English unified) |
| `labels` | filter / group tags | `WHERE;SUB;KIND` (semicolon-separated) |
| `max_length` | length limit | (currently empty) |

## Workflow

```
[push]
  Translations/Template/<cat>/      # canonical structure (TSV)
        ↓ build_source.py
  Crowdin_Mirror/source/            # this directory (regenerated)
        ↓ crowdin upload sources    # via Crowdin CLI
  Crowdin (DB)

[pull]
  Crowdin (DB)
        ↓ crowdin download          # via Crowdin CLI
  Crowdin_Mirror/translations/      # this directory (regenerated)
        ↓ apply_to_xlsx.py
  Translations/<locale>/Translation.xlsx (translation column updated)
```

## Regenerating content

Anything under `source/` can be rebuilt from `Translations/Template/`:

```powershell
python tools/crowdin/build_source.py
```

Anything under `translations/` is the result of `crowdin download` — re-run
to refresh:

```powershell
crowdin download
```

## Why not git-tracked?

- Crowdin push/pull cycles produce frequent diffs (translation updates,
  new strings) that would clutter git history.
- Crowdin itself stores the authoritative state with full history.
- Local mirror is regenerable — losing it is not catastrophic.
- If Crowdin ever needs to be replaced, export from Crowdin to TMX/CSV
  is a one-time operation, not a per-cycle concern.
