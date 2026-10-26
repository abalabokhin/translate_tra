"""Shared validation and atomic file writing for the dialogue translation pipeline."""

import csv
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path

DIALOGUE_COLUMNS = ['Actor', 'Line_ID', 'Predecessors', 'Dialogue_Text',
                    'TRA_Reference', 'Additional_Info']
TRANSLATION_COLUMNS = ['Russian_Male', 'Russian_Female']
# Engine substitutions, printf substitutions, literal escapes and colour controls.
TOKEN_PATTERN = re.compile(
    r'<[^<>\r\n]+>|%[A-Za-z_][\w]*%|%(?:\d+\$)?[-+0 #]*\d*(?:\.\d+)?[sdifouxXeEgGc]|'
    r'\\[nrt]|\^[A-Za-z0-9]|[\x00-\x08\x0b\x0c\x0e-\x1f]'
)


def validate_text(source, translated, label='translation'):
    if not isinstance(translated, str):
        raise ValueError(f'{label}: expected a string')
    if bool(source.strip()) != bool(translated.strip()):
        raise ValueError(f'{label}: empty/nonempty text does not match the source')
    if Counter(TOKEN_PATTERN.findall(source)) != Counter(TOKEN_PATTERN.findall(translated)):
        raise ValueError(f'{label}: engine placeholders or formatting tokens changed')
    for marker in ('\n', '*', '[', ']'):
        if source.count(marker) != translated.count(marker):
            raise ValueError(f'{label}: changed number of {marker!r} markers')
    quote_chars = '\"«»“”„'
    if sum(source.count(c) for c in quote_chars) != sum(translated.count(c) for c in quote_chars):
        raise ValueError(f'{label}: changed number of quotation marks')


def parse_reference(value):
    """Return a case-insensitive TRA key; reject paths and ambiguous references."""
    match = re.fullmatch(r'(?:TRA:)?([^:/\\]+\.tra):@(\d+)', value, re.IGNORECASE)
    if not match:
        raise ValueError(f'Invalid TRA reference: {value!r}')
    return match[1].casefold(), int(match[2])


def female_source(row, male):
    """Distinguish an explicitly empty original female string from no variant."""
    if row.get('Source_Has_Female') == '1' or row.get('Source_Female_Text'):
        return row['Source_Female_Text']
    return male


def read_csv(path, required):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader, None)
        if not header or len(set(header)) != len(header) or not set(required) <= set(header):
            raise ValueError(f'{path}: expected columns {required}')
        rows = []
        for row in reader:
            if not row:
                continue
            if len(row) != len(header):
                raise ValueError(f'{path}:{reader.line_num}: expected {len(header)} fields, got {len(row)}')
            rows.append(dict(zip(header, row)))
    return header, rows


def atomic_write(path, write):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=path.parent, delete=False) as handle:
            temp = Path(handle.name)
            write(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def write_csv(path, header, rows):
    def write(handle):
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    atomic_write(path, write)


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs)
