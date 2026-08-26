import json
import os


def find_matches(vanilla, query):
    """Case-insensitive substring search over a {form_id: name} dict.

    Returns a list of (form_id, name) tuples, sorted by name.
    """
    q = query.lower()
    return sorted(
        [(fid, name) for fid, name in vanilla.items() if q in name.lower()],
        key=lambda x: x[1]
    )


def resolve_item(vanilla, query, chooser=input):
    """Resolve a search query to a single (form_id, name).

    - No matches: raises LookupError.
    - Exactly one match, or exactly one case-insensitive exact-name match among
      several substring matches: returned directly, no prompt.
    - Multiple ambiguous matches (including same-name items with different
      form_ids): lists them and prompts via `chooser` for a numeric pick.
      `chooser` is injectable so this can be driven non-interactively.
    """
    matches = find_matches(vanilla, query)
    if not matches:
        raise LookupError(f'No items found matching "{query}"')

    exact = [m for m in matches if m[1].lower() == query.lower()]
    if len(exact) == 1:
        return exact[0]

    if len(matches) == 1:
        return matches[0]

    print(f'{len(matches)} matches for "{query}":')
    for i, (fid, name) in enumerate(matches, start=1):
        print(f'  [{i}] {fid:#010x}  {name}')

    while True:
        try:
            choice = chooser(f'Which one? (1-{len(matches)}, blank to cancel): ').strip()
        except EOFError:
            raise LookupError('Cancelled — no rule was added.')
        if not choice:
            raise LookupError('Cancelled — no rule was added.')
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            return matches[int(choice) - 1]
        print(f'  Enter a number from 1-{len(matches)}, or leave blank to cancel.')


def build_rule(form_id, vanilla_name, symbol_key, sort_tiers):
    """Build a custom_rules.json entry that applies the given sort tier to vanilla_name.

    Sets sort_tier (not display_name) so that apply_rule() handles all spacing
    and symbol logic consistently — the same path used for every mod-covered item.
    display_name is explicitly null so it doesn't short-circuit apply_rule().
    """
    if symbol_key not in sort_tiers:
        valid = ', '.join(sort_tiers)
        raise KeyError(f'Unknown symbol tier "{symbol_key}". Valid tiers: {valid}')

    return {
        'form_id':      f'{form_id:#010x}',
        'vanilla_name': vanilla_name,
        'base_name':    vanilla_name,
        'sort_tier':    symbol_key,
        'tags':         [],
        'tag_position': None,
        'display_name': None,
    }


def upsert_custom_rule(custom_rules_path, rule):
    """Load custom_rules.json (creating a fresh one if missing), upsert `rule` by
    form_id, and write the result back. Returns 'added' or 'updated'.
    """
    if custom_rules_path and os.path.exists(custom_rules_path):
        with open(custom_rules_path, encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {
            '_comment': (
                'Custom rules — field-level overrides on top of tidy_wasteland_analysis.json. '
                'For existing mod rules, only the fields you specify here will be changed. '
                "For new items the mod doesn't cover, add a complete entry. "
                'Use display_name to set the exact final string.'
            ),
            'rules': []
        }

    rules = data.setdefault('rules', [])
    for i, existing in enumerate(rules):
        if existing.get('form_id') == rule['form_id']:
            rules[i] = rule
            action = 'updated'
            break
    else:
        rules.append(rule)
        action = 'added'

    with open(custom_rules_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')

    return action
