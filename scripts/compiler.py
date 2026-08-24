import struct
import json
from parser import parse_strings_file


def apply_rule(vanilla_name, rule, sort_tiers):
    """Reconstruct the modded string from a rule's components.

    Handles three cases:
      - Pure rename:   display_name is set, use it directly
      - Tags only:     insert [Tag1][Tag2] at the correct position
      - Sort only:     prepend the sort symbol
      - Tags + sort:   both of the above
    """
    # Pure rename — display_name is the complete corrected name
    if rule.get('display_name'):
        return rule['display_name']

    result   = rule.get('base_name') or vanilla_name
    tags     = rule.get('tags') or []
    tag_pos  = rule.get('tag_position')
    tier     = rule.get('sort_tier')
    symbol   = sort_tiers.get(tier, {}).get('symbol', '') if tier else ''

    # Insert tags
    if tags:
        tag_str = ''.join(f'[{t}]' for t in tags)
        if tag_pos == 'after_prefix':
            # Insert right after the first ": "  (e.g. "Plan: [Tag] Item Name")
            idx = result.find(': ')
            if idx != -1:
                result = result[:idx + 2] + tag_str + ' ' + result[idx + 2:]
            else:
                result = tag_str + ' ' + result
        else:
            # before_plan: tags precede the whole string
            result = tag_str + ' ' + result

    # Prepend sort symbol
    if symbol:
        result = symbol + ' ' + result

    return result


def merge_rules(base_rules, custom_rules):
    """Merge custom rules into base rules with field-level overrides.

    For each custom entry:
      - If its form_id already exists in base_rules: overwrite only the fields
        present in the custom entry (lets you change just sort_tier or just tags
        without touching the rest of the rule).
      - If its form_id is new: insert the entry wholesale (covers items the mod
        doesn't handle at all).

    Custom rules always win on any field they specify.
    """
    merged = {r['form_id']: dict(r) for r in base_rules}

    for custom in custom_rules:
        fid = custom['form_id']
        if fid in merged:
            merged[fid].update({k: v for k, v in custom.items()})
        else:
            merged[fid] = dict(custom)

    return list(merged.values())


def build_modified_strings(vanilla, rules, sort_tiers):
    """Apply rules to a vanilla strings dict.

    Returns:
        modified (dict):  {form_id (int): string}
        stats    (dict):  counts of applied/skipped rules
    """
    modified = dict(vanilla)

    rule_map = {int(r['form_id'], 16): r for r in rules}

    stats = {'applied': 0, 'skipped_missing': 0}
    for fid, rule in rule_map.items():
        if fid not in vanilla:
            stats['skipped_missing'] += 1
            continue
        modified[fid] = apply_rule(vanilla[fid], rule, sort_tiers)
        stats['applied'] += 1

    return modified, stats


def write_strings_file(strings, output_path):
    """Write a {form_id (int): string} dict to a Bethesda .STRINGS binary.

    Format:
        [uint32] num_entries
        [uint32] data_block_size
        [uint32 form_id + uint32 offset] x num_entries
        [null-terminated UTF-8 strings]
    """
    entries = sorted(strings.items())  # stable ordering by form_id

    # Build data block and record offsets
    data_parts     = []
    offsets        = []
    current_offset = 0

    for _fid, text in entries:
        encoded = text.encode('utf-8') + b'\x00'
        offsets.append(current_offset)
        data_parts.append(encoded)
        current_offset += len(encoded)

    data_block      = b''.join(data_parts)
    num_entries     = len(entries)
    data_block_size = len(data_block)

    with open(output_path, 'wb') as f:
        f.write(struct.pack('<II', num_entries, data_block_size))
        for (fid, _), offset in zip(entries, offsets):
            f.write(struct.pack('<II', fid, offset))
        f.write(data_block)

    return num_entries, data_block_size


def verify_output(output_path, expected):
    """Parse the written file and confirm every entry matches expected."""
    parsed = parse_strings_file(output_path)
    mismatches = [
        (fid, expected[fid], parsed.get(fid))
        for fid in expected
        if parsed.get(fid) != expected[fid]
    ]
    return mismatches


if __name__ == '__main__':
    import argparse
    import os

    arg_parser = argparse.ArgumentParser(
        description='Compile a rules JSON + vanilla .STRINGS into a modded .STRINGS binary.'
    )
    arg_parser.add_argument(
        '--vanilla',
        default=os.environ.get('FO76_VANILLA_STRINGS'),
        metavar='PATH',
        help='Path to the vanilla .STRINGS file (default: $FO76_VANILLA_STRINGS)'
    )
    arg_parser.add_argument(
        '--rules',
        default=os.environ.get('FO76_OUTPUT_JSON'),
        metavar='PATH',
        help='Path to the rules JSON file (default: $FO76_OUTPUT_JSON)'
    )
    arg_parser.add_argument(
        '--output',
        default=os.environ.get('FO76_COMPILED_STRINGS'),
        metavar='PATH',
        help='Destination path for the compiled .STRINGS file (default: $FO76_COMPILED_STRINGS)'
    )
    arg_parser.add_argument(
        '--verify',
        action='store_true',
        help='Re-parse the output file after writing and confirm all entries are correct'
    )
    args = arg_parser.parse_args()

    missing = []
    if not args.vanilla:
        missing.append('--vanilla (or set $FO76_VANILLA_STRINGS)')
    if not args.rules:
        missing.append('--rules (or set $FO76_OUTPUT_JSON)')
    if not args.output:
        missing.append('--output (or set $FO76_COMPILED_STRINGS)')
    if missing:
        arg_parser.error('Missing required arguments:\n  ' + '\n  '.join(missing))

    print('Reading vanilla strings...')
    vanilla = parse_strings_file(args.vanilla)
    print(f'  {len(vanilla):,} entries loaded')

    print('Reading rules...')
    with open(args.rules, encoding='utf-8') as f:
        data = json.load(f)
    sort_tiers = data['sort_tiers']
    rules      = data['rules']
    print(f'  {len(rules):,} rules loaded')

    print('Applying rules...')
    modified, stats = build_modified_strings(vanilla, rules, sort_tiers)
    print(f'  {stats["applied"]:,} rules applied')
    if stats['skipped_missing']:
        print(f'  {stats["skipped_missing"]:,} rules skipped (form_id not in vanilla file)')

    print('Writing output...')
    num_entries, data_size = write_strings_file(modified, args.output)
    print(f'  {num_entries:,} entries, {data_size:,} bytes data block -> {args.output}')

    if args.verify:
        print('Verifying...')
        mismatches = verify_output(args.output, modified)
        if mismatches:
            print(f'  FAILED: {len(mismatches)} mismatches found!')
            for fid, expected, actual in mismatches[:10]:
                print(f'    {fid:#010x}: expected {expected!r}, got {actual!r}')
        else:
            print(f'  OK: all {num_entries:,} entries verified')
