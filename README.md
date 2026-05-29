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
│   ├── parser.py     # Binary .STRINGS file parser
│   └── diff.py       # Vanilla vs modded diff and rule extractor
├── data/
│   └── tidy_wasteland_analysis.json  # Extracted ruleset (generated)
├── README.md
└── requirements.txt
```

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

Parse a strings file:
```
python scripts/parser.py
```

Generate analysis JSON from vanilla + modded diff:
```
python scripts/diff.py
```

## Roadmap

- [x] Binary `.STRINGS` parser
- [x] Vanilla vs modded diff tool
- [x] Rule extraction and JSON export
- [ ] JSON config to `.STRINGS` compiler
- [ ] PTS diff tool for patch compatibility checking
- [ ] Tag customizer UI

## Acknowledgements

Tagging conventions and mod structure inspired by
[Tidy Wasteland Tags](https://www.nexusmods.com/fallout76/mods/3882) by the original mod author.
