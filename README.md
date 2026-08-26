# FO76 Tag Customizer

A toolkit for parsing, analyzing, and customizing item display strings in Fallout 76,
inspired by the [Tidy Wasteland Tags](https://www.nexusmods.com/fallout76/mods/3882) mod.

## Project Goals

- Parse Bethesda `.STRINGS` binary files into usable data
- Diff vanilla vs modded strings to reverse engineer tagging rules
- Compile a human-readable JSON config back into a valid `.STRINGS` file
- Eventually: a UI for visually customizing tags without touching binary files

## Project Structure

```
fo76-tag-customizer/
├── scripts/
│   ├── parser.py       # Binary .STRINGS file parser
│   ├── diff.py         # Vanilla vs modded diff and rule extractor
│   ├── compiler.py     # JSON rules + vanilla .STRINGS -> modded .STRINGS binary
│   └── extract_ba2.py  # Pulls the vanilla strings file straight out of a BA2 archive
├── data/
│   └── tidy_wasteland_analysis.json  # Extracted ruleset (generated)
├── run.py              # Unified CLI: parser / diff / find / compile / extract
├── README.md
└── requirements.txt
```

## Symbol Legend

Tidy Wasteland Tags works entirely by rewriting `display_name` strings — prepending
one of a fixed set of characters (rendered as icons by the mod's bundled font) and/or
bracket tags. Confirmed by cross-referencing the parsed data against the actual in-game
UI:

| Text char(s) | Renders as | Meaning |
|---|---|---|
| `¬` / `¬¬` / `¬¬¬` | ★ / ★★ / ★★★ | Rare / Very Rare / Ultra Rare |
| `±` | Ⓒ | Valuable |
| `·` | ⊕ | Important |
| `¢` | ⚛ | Atom Shop exclusive |
| `¤` | ☢ | Cut/Illegal/Dev — not legitimately obtainable (the largest category, ~44% of rules) |
| `¶` | stacked-papers icon | Worth-reading magazine, paired with a `Mag: ` name prefix |
| `[Q]` | `[Q]` | Quest item (bracket tag, not a font glyph) |

Only the rarity stars (`¬`) repeat/stack; every other symbol is a single-occurrence flag.
See `scripts/diff.py`'s `SORT_SYMBOLS`/`SORT_TIERS` for the canonical mapping.

## Setup

1. Install Python 3.12+
2. Clone this repo
3. Create a virtual environment: `python -m venv .venv`
4. Activate it: `.\.venv\Scripts\activate`
5. Install dependencies: `pip install -r requirements.txt`

## Required Files

The following files are **not included** in this repo as they are copyrighted game assets.
You will need to provide them yourself:

- **Vanilla strings**: extracted from `SeventySix - Localization.ba2` using BAMgr FOE
- **Modded strings**: from your Fallout 76 Data directory with Tidy Wasteland Tags installed

Update the paths at the bottom of each script to match your local setup:

```
Vanilla: C:\Users\mshie\Documents\Mod Tools\strings\Vanilla\strings\seventysix_en.strings
Modded:  C:\Users\mshie\Documents\Mod Tools\strings\Modded\SeventySix_en.STRINGS
```

## Usage

All scripts are also exposed through the unified `run.py` CLI (reads the same
`FO76_*` env vars as defaults — see `custom_rules.json`'s companion `fo76-env.ps1`):

```
python run.py parser  --strings <path>
python run.py diff    --vanilla <path> --modded <path> --output <path>
python run.py find    "item name substring"
python run.py tag     "item name" --symbol <tier>   # search + write a custom_rules.json entry
python run.py compile --vanilla <path> --rules <path> --output <path> [--custom-rules <path>] [--verify]
python run.py extract --ba2 <path> --output <path>
```

`tag` is the fast path for one-off customizations: it searches vanilla strings by
name, disambiguates automatically when there's exactly one exact-name match (or
prompts you to pick when there isn't), and adds/updates the corresponding entry in
`custom_rules.json` — no manual form_id lookup or JSON editing required. Valid
`--symbol` values are the `SORT_TIERS` keys from `scripts/diff.py` (see the Symbol
Legend above). Note: search runs over the *entire* `.STRINGS` table, which includes
non-item text (tooltips, icons, damage-mod strings) alongside real items, so generic
queries can turn up noisy results — exact or near-exact names work best.

## Roadmap

- [x] Binary `.STRINGS` parser
- [x] Vanilla vs modded diff tool
- [x] Rule extraction and JSON export
- [x] JSON config to `.STRINGS` compiler
- [x] BA2 extractor (no external tools needed to pull vanilla strings)
- [x] Field-level custom rule overrides (`custom_rules.json`)
- [x] `tag` command: search-by-name + auto-write custom rule (no manual form_id/JSON editing)
- [ ] PTS diff tool for patch compatibility checking
- [ ] Tag customizer UI (visual search/tag picker, likely the natural next step on top of `tag`)

## Acknowledgements

Tagging conventions and mod structure inspired by
[Tidy Wasteland Tags](https://www.nexusmods.com/fallout76/mods/3882) by the original mod author.
