import struct
import zlib

MAGIC = b'BTDX'
TYPE_GNRL = b'GNRL'


def extract_from_ba2(ba2_path, target_file, output_path):
    """Extract a single file from a Bethesda BA2 (GNRL) archive."""
    target_normalized = target_file.replace('\\', '/').lower()

    with open(ba2_path, 'rb') as f:
        # --- Header (24 bytes) ---
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError(f'Not a BA2 file (magic: {magic!r})')

        _version  = struct.unpack('<I', f.read(4))[0]
        arch_type = f.read(4)
        if arch_type != TYPE_GNRL:
            raise ValueError(
                f'Unsupported BA2 type: {arch_type!r} — only GNRL archives are supported'
            )

        num_files         = struct.unpack('<I', f.read(4))[0]
        name_table_offset = struct.unpack('<Q', f.read(8))[0]

        # --- File records (36 bytes each) ---
        records = []
        for _ in range(num_files):
            _name_hash = struct.unpack('<I', f.read(4))[0]
            _ext       = f.read(4)
            _dir_hash  = struct.unpack('<I', f.read(4))[0]
            _flags     = struct.unpack('<I', f.read(4))[0]
            offset     = struct.unpack('<Q', f.read(8))[0]
            packed     = struct.unpack('<I', f.read(4))[0]
            unpacked   = struct.unpack('<I', f.read(4))[0]
            _align     = struct.unpack('<I', f.read(4))[0]  # 0xBAADF00D sentinel
            records.append({'offset': offset, 'packed': packed, 'unpacked': unpacked})

        # --- Name table: scan for our target ---
        f.seek(name_table_offset)
        match_record = None
        all_names    = []
        for record in records:
            length = struct.unpack('<H', f.read(2))[0]
            name   = f.read(length).decode('utf-8', errors='replace')
            all_names.append(name)
            if name.replace('\\', '/').lower() == target_normalized:
                match_record = record

        if match_record is None:
            stem  = target_normalized.split('/')[-1]
            close = [n for n in all_names if stem in n.lower()]
            hint  = ('\nClose matches:\n  ' + '\n  '.join(close)) if close else ''
            raise FileNotFoundError(f'File not found in archive: {target_file}{hint}')

        # --- Extract (decompress if needed) ---
        f.seek(match_record['offset'])
        if match_record['packed'] > 0:
            data = zlib.decompress(f.read(match_record['packed']))
        else:
            data = f.read(match_record['unpacked'])

    with open(output_path, 'wb') as out:
        out.write(data)

    print(f'Extracted {len(data):,} bytes -> {output_path}')


if __name__ == '__main__':
    import argparse
    import os

    arg_parser = argparse.ArgumentParser(
        description='Extract a single file from a Bethesda BA2 (GNRL) archive.'
    )
    arg_parser.add_argument(
        '--ba2',
        default=os.environ.get('FO76_BA2_LOCALIZATION'),
        metavar='PATH',
        help='Path to the .ba2 archive (default: $FO76_BA2_LOCALIZATION)'
    )
    arg_parser.add_argument(
        '--file',
        default='strings/seventysix_en.strings',
        metavar='NAME',
        help='Internal path of file to extract (default: strings/seventysix_en.strings)'
    )
    arg_parser.add_argument(
        '--output',
        default=os.environ.get('FO76_VANILLA_STRINGS'),
        metavar='PATH',
        help='Destination path for extracted file (default: $FO76_VANILLA_STRINGS)'
    )
    args = arg_parser.parse_args()

    missing = []
    if not args.ba2:
        missing.append('--ba2 (or set $FO76_BA2_LOCALIZATION)')
    if not args.output:
        missing.append('--output (or set $FO76_VANILLA_STRINGS)')
    if missing:
        arg_parser.error('Missing required arguments:\n  ' + '\n  '.join(missing))

    extract_from_ba2(args.ba2, args.file, args.output)
