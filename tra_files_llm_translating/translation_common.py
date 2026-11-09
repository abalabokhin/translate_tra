"""Shared validation and atomic file writing for the dialogue translation pipeline."""

import csv
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from find_closest_item import statistics_section, statistics_parts, statistics_numbers

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
    source_layout, translated_layout = source, translated
    if statistics_section(source) is not None:
        original_parts, translated_parts = statistics_parts(source), statistics_parts(translated)
        if translated_parts is None:
            raise ValueError(f'{label}: item statistics heading is missing')
        if statistics_numbers(original_parts[1]) != statistics_numbers(translated_parts[1]):
            raise ValueError(f'{label}: item statistics numbers, signs, percentages or dice changed')
        # Statistics can adopt reference spacing/quotes. Narrative keeps the
        # existing formatting checks; engine tokens are still checked globally.
        source_layout, translated_layout = original_parts[0], translated_parts[0]
    for marker in ('\n', '*', '[', ']'):
        a, b = (source_layout, translated_layout) if marker == '\n' else (source, translated)
        if a.count(marker) != b.count(marker):
            raise ValueError(f'{label}: changed number of {marker!r} markers')
    quote_chars = '\"«»“”„'
    if sum(source_layout.count(c) for c in quote_chars) != sum(translated_layout.count(c) for c in quote_chars):
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


def merge_dialogue_rows(rows):
    """Return prompt rows and Line_ID -> 1-based slot, merging shared TRA strings."""
    slot, first, uses = {}, {}, []  # Line_ID -> prompt index; merge key -> index; index-1 -> rows
    for row in rows[1:]:
        key = parse_reference(row[5]) if row[4] else row[1]
        if key not in first:
            first[key] = len(first) + 1
            uses.append([])
        slot[row[1]] = first[key]
        uses[slot[row[1]] - 1].append(row)
    prompt_rows = [rows[0]]
    for i, same in enumerate(uses, 1):
        source_pairs = {(r[3], female_source(dict(zip(rows[0], r)), r[3])) for r in same}
        if len(source_pairs) != 1:
            raise ValueError(f'Conflicting source text for reused TRA string {same[0][5]}')
        speakers, predecessors = [], []
        for row in same:
            if row[0] not in speakers:
                speakers.append(row[0])
            for predecessor in filter(None, row[2].split(';')):
                predecessor = uses[slot[predecessor] - 1][0][1] if predecessor in slot else predecessor
                if predecessor != same[0][1] and predecessor not in predecessors:
                    predecessors.append(predecessor)
        merged = [';'.join(speakers), same[0][1], ';'.join(predecessors)] + same[0][3:]
        if 'Speaker_Gender' in rows[0]:
            column = rows[0].index('Speaker_Gender')
            by_actor = {}
            for row in same:
                names, genders = row[0].split(';'), row[column].split(';')
                if len(names) != len(genders):
                    genders = ['unknown'] * len(names)
                for name, gender in zip(names, genders):
                    if name in by_actor and by_actor[name] != gender:
                        by_actor[name] = 'unknown'
                    else:
                        by_actor[name] = gender
            merged[column] = ';'.join(by_actor.get(name, 'unknown') for speaker in speakers for name in speaker.split(';'))
        for name in ('Source_Context', 'Usage_Context', 'Display_Target', 'Resource', 'Field'):
            if name in rows[0]:
                column = rows[0].index(name)
                merged[column] = ' | '.join(dict.fromkeys(row[column] for row in same if row[column]))
        if 'Addressee' in rows[0]:
            column = rows[0].index('Addressee')
            if len({r[column] for r in same}) > 1:
                merged[column] = ''  # No single listener fact applies to every use.
        prompt_rows.append(merged)
    return prompt_rows, slot
