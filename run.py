import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from parser import parse_strings_file
from diff import build_rules, SORT_TIERS
from extract_ba2 import extract_from_ba2


def cmd_parser(args):
    strings = parse_strings_file(args.strings)
    print(f'Total entries: {len(strings)}')

    plans = {fid: name for fid, name in strings.items() if 'plan:' in name.lower()}
    print(f'Plan entries: {len(plans)}')
    for form_id, text in list(plans.items())[:20]:
        print(f'  {form_id:#010x}: {text}')


def cmd_diff(args):
    import json

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


def cmd_extract(args):
    extract_from_ba2(args.ba2, args.file, args.output)


def main():
    parser = argparse.ArgumentParser(
        prog='run.py',
        description='FO76 Tag Customizer — unified entry point'
    )
    subparsers = parser.add_subparsers(dest='command', metavar='SCRIPT', required=True)

    # parser subcommand
    p_parser = subparsers.add_parser('parser', help='Parse a .STRINGS file and print a summary')
    p_parser.add_argument(
        '--strings',
        default=os.environ.get('FO76_MODDED_STRINGS'),
        metavar='PATH',
        help='Path to the .STRINGS file (default: $FO76_MODDED_STRINGS)'
    )

    # diff subcommand
    p_diff = subparsers.add_parser('diff', help='Diff vanilla vs modded .STRINGS and export rules to JSON')
    p_diff.add_argument(
        '--vanilla',
        default=os.environ.get('FO76_VANILLA_STRINGS'),
        metavar='PATH',
        help='Path to the vanilla .STRINGS file (default: $FO76_VANILLA_STRINGS)'
    )
    p_diff.add_argument(
        '--modded',
        default=os.environ.get('FO76_MODDED_STRINGS'),
        metavar='PATH',
        help='Path to the modded .STRINGS file (default: $FO76_MODDED_STRINGS)'
    )
    p_diff.add_argument(
        '--output',
        default=os.environ.get('FO76_OUTPUT_JSON'),
        metavar='PATH',
        help='Path for the output JSON file (default: $FO76_OUTPUT_JSON)'
    )

    # extract subcommand
    p_extract = subparsers.add_parser('extract', help='Extract vanilla strings from a BA2 archive')
    p_extract.add_argument(
        '--ba2',
        default=os.environ.get('FO76_BA2_LOCALIZATION'),
        metavar='PATH',
        help='Path to the .ba2 archive (default: $FO76_BA2_LOCALIZATION)'
    )
    p_extract.add_argument(
        '--file',
        default='strings/seventysix_en.strings',
        metavar='NAME',
        help='Internal path to extract (default: strings/seventysix_en.strings)'
    )
    p_extract.add_argument(
        '--output',
        default=os.environ.get('FO76_VANILLA_STRINGS'),
        metavar='PATH',
        help='Destination path for extracted file (default: $FO76_VANILLA_STRINGS)'
    )

    args = parser.parse_args()

    # Validate that required paths were resolved (via flag or env var)
    missing = []
    if args.command == 'parser' and not args.strings:
        missing.append('--strings (or set $FO76_MODDED_STRINGS)')
    if args.command == 'diff':
        if not args.vanilla:
            missing.append('--vanilla (or set $FO76_VANILLA_STRINGS)')
        if not args.modded:
            missing.append('--modded (or set $FO76_MODDED_STRINGS)')
        if not args.output:
            missing.append('--output (or set $FO76_OUTPUT_JSON)')
    if args.command == 'extract':
        if not args.ba2:
            missing.append('--ba2 (or set $FO76_BA2_LOCALIZATION)')
        if not args.output:
            missing.append('--output (or set $FO76_VANILLA_STRINGS)')
    if missing:
        parser.error('Missing required arguments:\n  ' + '\n  '.join(missing))

    dispatch = {
        'parser':  cmd_parser,
        'diff':    cmd_diff,
        'extract': cmd_extract,
    }
    dispatch[args.command](args)


if __name__ == '__main__':
    main()
