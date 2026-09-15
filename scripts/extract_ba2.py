import os
import struct
import zlib

MAGIC = b'BTDX'
TYPE_GNRL = b'GNRL'


def _read_header_and_records(f):
    """Read BA2 header + file records; return (records, name_table_offset)."""
    magic = f.read(4)
    if magic != MAGIC:
        raise ValueError(f'Not a BA2 file (magic: {magic!r})')

    _version          = struct.unpack('<I', f.read(4))[0]
    arch_type         = f.read(4)
    if arch_type != TYPE_GNRL:
        raise ValueError(
            f'Unsupported BA2 type: {arch_type!r} — only GNRL archives are supported'
        )

    num_files         = struct.unpack('<I', f.read(4))[0]
    name_table_offset = struct.unpack('<Q', f.read(8))[0]

    records = []
    for _ in range(num_files):
        _name_hash = struct.unpack('<I', f.read(4))[0]
        _ext       = f.read(4)
        _dir_hash  = struct.unpack('<I', f.read(4))[0]
        _flags     = struct.unpack('<I', f.read(4))[0]
        offset     = struct.unpack('<Q', f.read(8))[0]
        packed     = struct.unpack('<I', f.read(4))[0]
        unpacked   = struct.unpack('<I', f.read(4))[0]
        _align     = struct.unpack('<I', f.read(4))[0]
        records.append({'offset': offset, 'packed': packed, 'unpacked': unpacked})

    return records, name_table_offset


def _extract_record(f, record):
    """Seek to record and return its (possibly compressed) bytes."""
    f.seek(record['offset'])
    if record['packed'] > 0:
        return zlib.decompress(f.read(record['packed']))
    return f.read(record['unpacked'])


def extract_multiple_from_ba2(ba2_path, file_map):
    """Extract multiple files from a BA2 in a single archive pass.

    file_map: {internal_archive_path: output_filesystem_path}
              e.g. {"strings/seventysix_en.dlstrings": "/path/to/out.dlstrings"}

    Returns: {internal_path: bytes_written} for every matched file.
    Raises FileNotFoundError if any requested file was not found.
    """
    targets = {k.replace('\\', '/').lower(): (k, v) for k, v in file_map.items()}

    with open(ba2_path, 'rb') as f:
        records, name_table_offset = _read_header_and_records(f)

        f.seek(name_table_offset)
        matched = {}
        all_names = []
        for record in records:
            length = struct.unpack('<H', f.read(2))[0]
            name   = f.read(length).decode('utf-8', errors='replace')
            all_names.append(name)
            norm = name.replace('\\', '/').lower()
            if norm in targets:
                matched[norm] = (record, targets[norm][1])

        results = {}
        for norm, (record, out_path) in matched.items():
            data = _extract_record(f, record)
            out_dir = os.path.dirname(out_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(out_path, 'wb') as out:
                out.write(data)
            results[norm] = len(data)

    not_found = set(targets.keys()) - set(matched.keys())
    if not_found:
        stem_hints = {}
        for missing_norm in not_found:
            stem = missing_norm.split('/')[-1]
            close = [n for n in all_names if stem in n.lower()]
            if close:
                stem_hints[missing_norm] = close
        detail = '; '.join(
            f'{k}' + (f' (close: {v[0]})' if v else '')
            for k, v in stem_hints.items()
        ) or ', '.join(not_found)
        raise FileNotFoundError(f'Files not found in archive: {detail}')

    return results


def extract_from_ba2(ba2_path, target_file, output_path):
    """Extract a single file from a Bethesda BA2 (GNRL) archive."""
    results = extract_multiple_from_ba2(ba2_path, {target_file: output_path})
    norm = target_file.replace('\\', '/').lower()
    print(f'Extracted {results[norm]:,} bytes -> {output_path}')


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
