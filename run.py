import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from parser import parse_strings_file
from diff import build_rules, SORT_TIERS
from extract_ba2 import extract_from_ba2
from compiler import merge_rules, build_modified_strings, write_strings_file, verify_output
from tagger import resolve_item, build_rule, build_freeform_rule, upsert_custom_rule


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

    plans    = sum(1 for r in rules if 'plan:' in r['vanilla_name'].lower())
    renamed  = sum(1 for r in rules if r['display_name'])
    tagged   = sum(1 for r in rules if r['tags'])
    prefixed = sum(1 for r in rules if r['sort_tier'])
    both     = sum(1 for r in rules if r['tags'] and r['sort_tier'])
    print(f'  Plans:         {plans}')
    print(f'  Other items:   {len(rules) - plans}')
    print(f'  Renames:       {renamed}')
    print(f'  Tagged:        {tagged}')
    print(f'  Sort prefixed: {prefixed}')
    print(f'  Both:          {both}')


def cmd_find(args):
    strings = parse_strings_file(args.strings)
    query   = args.query.lower()
    hits    = sorted(
        [(fid, name) for fid, name in strings.items() if query in name.lower()],
        key=lambda x: x[1]
    )
    if not hits:
        print(f'No entries found matching "{args.query}"')
        return
    print(f'{len(hits)} match(es) for "{args.query}":')
    for fid, name in hits:
        print(f'  {fid:#010x}  {name}')


def cmd_compile(args):
    import json

    print('Reading vanilla strings...')
    vanilla = parse_strings_file(args.vanilla)
    print(f'  {len(vanilla):,} entries loaded')

    print('Reading rules...')
    with open(args.rules, encoding='utf-8') as f:
        data = json.load(f)
    sort_tiers = data['sort_tiers']
    rules      = data['rules']
    print(f'  {len(rules):,} rules loaded')

    if args.custom_rules:
        with open(args.custom_rules, encoding='utf-8') as f:
            custom = json.load(f)
        custom_list = custom.get('rules', [])
        rules = merge_rules(rules, custom_list)
        print(f'  {len(custom_list):,} custom rule(s) merged ({len(rules):,} total)')

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


def cmd_tag(args):
    vanilla = parse_strings_file(args.vanilla)

    try:
        form_id, vanilla_name = resolve_item(vanilla, args.query)
    except LookupError as e:
        print(str(e))
        return

    if args.symbol:
        try:
            rule = build_rule(form_id, vanilla_name, args.symbol, SORT_TIERS)
        except KeyError as e:
            print(str(e))
            return
        preview = f'sort_tier={args.symbol!r}'
    else:
        prefix = args.prefix or ''
        suffix = args.suffix or ''
        rule    = build_freeform_rule(form_id, vanilla_name, prefix, suffix)
        preview = repr(rule['display_name'])

    action = upsert_custom_rule(args.custom_rules, rule)
    print(f'{action.capitalize()} rule: {rule["form_id"]} -> {preview}')
    print(f'  ({args.custom_rules})')
    print("Run 'compile --custom-rules ...' to apply it to a .STRINGS file.")


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

    # find subcommand
    p_find = subparsers.add_parser('find', help='Search vanilla strings by name to look up form IDs')
    p_find.add_argument(
        'query',
        metavar='TEXT',
        help='Case-insensitive substring to search for'
    )
    p_find.add_argument(
        '--strings',
        default=os.environ.get('FO76_VANILLA_STRINGS'),
        metavar='PATH',
        help='Path to the .STRINGS file to search (default: $FO76_VANILLA_STRINGS)'
    )

    # compile subcommand
    p_compile = subparsers.add_parser('compile', help='Apply rules JSON to vanilla .STRINGS and write a modded binary')
    p_compile.add_argument(
        '--vanilla',
        default=os.environ.get('FO76_VANILLA_STRINGS'),
        metavar='PATH',
        help='Path to the vanilla .STRINGS file (default: $FO76_VANILLA_STRINGS)'
    )
    p_compile.add_argument(
        '--rules',
        default=os.environ.get('FO76_OUTPUT_JSON'),
        metavar='PATH',
        help='Path to the rules JSON file (default: $FO76_OUTPUT_JSON)'
    )
    p_compile.add_argument(
        '--output',
        default=os.environ.get('FO76_COMPILED_STRINGS'),
        metavar='PATH',
        help='Destination for the compiled .STRINGS file (default: $FO76_COMPILED_STRINGS)'
    )
    p_compile.add_argument(
        '--custom-rules',
        default=os.environ.get('FO76_CUSTOM_RULES'),
        metavar='PATH',
        help='Path to custom rules JSON for field-level overrides (default: $FO76_CUSTOM_RULES)'
    )
    p_compile.add_argument(
        '--verify',
        action='store_true',
        help='Re-parse output after writing to confirm all entries are correct'
    )

    # tag subcommand
    p_tag = subparsers.add_parser(
        'tag',
        help='Search vanilla strings by name and add/update a custom rule'
    )
    p_tag.add_argument(
        'query',
        metavar='NAME',
        help='Item name (or substring) to search for'
    )
    tag_mode = p_tag.add_mutually_exclusive_group(required=True)
    tag_mode.add_argument(
        '--symbol',
        choices=list(SORT_TIERS),
        metavar='TIER',
        help='Sort-tier symbol to apply (handles lead_spaces automatically): '
             + ', '.join(SORT_TIERS)
    )
    tag_mode.add_argument(
        '--prefix',
        metavar='TEXT',
        help='Free-form text to prepend to the item name (use with optional --suffix)'
    )
    p_tag.add_argument(
        '--suffix',
        metavar='TEXT',
        help='Free-form text to append to the item name (requires --prefix)'
    )
    p_tag.add_argument(
        '--vanilla',
        default=os.environ.get('FO76_VANILLA_STRINGS'),
        metavar='PATH',
        help='Path to the vanilla .STRINGS file to search (default: $FO76_VANILLA_STRINGS)'
    )
    p_tag.add_argument(
        '--custom-rules',
        default=os.environ.get('FO76_CUSTOM_RULES'),
        metavar='PATH',
        help='Path to custom rules JSON to update (default: $FO76_CUSTOM_RULES)'
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
    if args.command == 'find' and not args.strings:
        missing.append('--strings (or set $FO76_VANILLA_STRINGS)')
    if args.command == 'compile':
        if not args.vanilla:
            missing.append('--vanilla (or set $FO76_VANILLA_STRINGS)')
        if not args.rules:
            missing.append('--rules (or set $FO76_OUTPUT_JSON)')
        if not args.output:
            missing.append('--output (or set $FO76_COMPILED_STRINGS)')
    if args.command == 'tag':
        if not args.vanilla:
            missing.append('--vanilla (or set $FO76_VANILLA_STRINGS)')
        if not args.custom_rules:
            missing.append('--custom-rules (or set $FO76_CUSTOM_RULES)')
        if getattr(args, 'suffix', None) and not getattr(args, 'prefix', None):
            missing.append('--prefix is required when --suffix is used')
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
        'find':    cmd_find,
        'compile': cmd_compile,
        'tag':     cmd_tag,
        'extract': cmd_extract,
    }
    dispatch[args.command](args)


if __name__ == '__main__':
    main()
