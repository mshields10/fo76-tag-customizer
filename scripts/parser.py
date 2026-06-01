import struct


def parse_strings_file(filepath):
    """Parse a Bethesda .STRINGS binary file into a dict of {form_id: string}"""
    with open(filepath, 'rb') as f:
        num_entries, data_size = struct.unpack('<II', f.read(8))

        entries = []
        for _ in range(num_entries):
            form_id, offset = struct.unpack('<II', f.read(8))
            entries.append((form_id, offset))

        data_block = f.read(data_size)

    results = {}
    for form_id, offset in entries:
        end = data_block.index(b'\x00', offset)
        string = data_block[offset:end].decode('utf-8', errors='replace')
        results[form_id] = string

    return results


if __name__ == '__main__':
    import argparse

    arg_parser = argparse.ArgumentParser(description='Parse a Bethesda .STRINGS binary file.')
    arg_parser.add_argument('--strings', required=True, metavar='PATH', help='Path to the .STRINGS file')
    args = arg_parser.parse_args()

    strings = parse_strings_file(args.strings)
    print(f'Total entries: {len(strings)}')

    plans = {fid: name for fid, name in strings.items() if 'plan:' in name.lower()}
    print(f'Plan entries: {len(plans)}')
    for form_id, text in list(plans.items())[:20]:
        print(f'  {form_id:#010x}: {text}')