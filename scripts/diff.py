import struct
import re
import json
from parser import parse_strings_file


SORT_SYMBOLS = {
    '¤':   'rare',
    '¬':   'mid',
    '¬¬':  'common',
    '¬¬¬': 'basic',
    '±':   'lowest',
}

SORT_TIERS = {
    'rare':   {'symbol': '¤',   'description': 'Rare/valuable plans'},
    'mid':    {'symbol': '¬',   'description': 'Mid tier plans'},
    'common': {'symbol': '¬¬',  'description': 'Common craftable mods'},
    'basic':  {'symbol': '¬¬¬', 'description': 'Basic/low value plans'},
    'lowest': {'symbol': '±',   'description': 'Lowest priority'}
}


def extract_components(vanilla, modded):
    """Decompose a modded string into sort_prefix, tags, and base_name"""
    sort_prefix = ''
    remainder = modded

    # Extract sort prefix (special unicode chars before item name)
    prefix_match = re.match(r'^([¢¤¬±\s]+)(.+)$', modded)
    if prefix_match:
        sort_prefix = prefix_match.group(1).strip()
        remainder = prefix_match.group(2).strip()

    # Extract bracketed tags
    tags = re.findall(r'\[([^\]]+)\]', remainder)

    # Clean base name - remove tags and fix whitespace
    base_name = re.sub(r'\[[^\]]+\]\s*', '', remainder).strip()
    base_name = re.sub(r'\s+', ' ', base_name).strip()

    # Detect tag position
    tag_position = None
    if tags:
        if re.search(r'^Plan:\s*\[', remainder):
            tag_position = 'after_prefix'
        else:
            tag_position = 'before_plan'

    # Detect rename (name changed but no tags or sort prefix)
    display_name = None
    if base_name.lower() != vanilla.lower() and not tags and not sort_prefix:
        display_name = base_name

    return {
        'sort_tier':    SORT_SYMBOLS.get(sort_prefix),
        'tags':         tags,
        'tag_position': tag_position,
        'display_name': display_name,
        'base_name':    base_name
    }


def build_rules(vanilla: dict, modded: dict) -> list:
    """Generate a list of rules by diffing vanilla and modded string dicts"""
    rules = []
    for fid in vanilla:
        v_name = vanilla[fid]
        m_name = modded.get(fid, v_name)
        if 'plan:' not in v_name.lower():
            continue
        if v_name == m_name:
            continue

        components = extract_components(v_name, m_name)
        rules.append({
            'form_id':      f'{fid:#010x}',
            'vanilla_name': v_name,
            'modded_name':  m_name,
            **components
        })
    return rules


if __name__ == '__main__':
    import argparse

    arg_parser = argparse.ArgumentParser(description='Diff vanilla vs modded .STRINGS and export rules to JSON.')
    arg_parser.add_argument('--vanilla', required=True, metavar='PATH', help='Path to the vanilla .STRINGS file')
    arg_parser.add_argument('--modded',  required=True, metavar='PATH', help='Path to the modded .STRINGS file')
    arg_parser.add_argument('--output',  required=True, metavar='PATH', help='Path for the output JSON file')
    args = arg_parser.parse_args()

    vanilla = parse_strings_file(args.vanilla)
    modded  = parse_strings_file(args.modded)
    rules   = build_rules(vanilla, modded)

    output = {
        'sort_tiers': SORT_TIERS,
        'total_rules': len(rules),
        'rules': rules
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f'Exported {len(rules)} rules to {args.output}')

    renamed  = sum(1 for r in rules if r['display_name'])
    tagged   = sum(1 for r in rules if r['tags'])
    prefixed = sum(1 for r in rules if r['sort_tier'])
    both     = sum(1 for r in rules if r['tags'] and r['sort_tier'])
    print(f'  Renames:       {renamed}')
    print(f'  Tagged:        {tagged}')
    print(f'  Sort prefixed: {prefixed}')
    print(f'  Both:          {both}')