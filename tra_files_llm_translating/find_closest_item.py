#!/usr/bin/env python3
"""Select paired item statistics as formatting examples, without using item lore."""
import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from functools import lru_cache
import json
import math
from pathlib import Path
import re

from tra_format import parse_tra, read_text

REFERENCE = Path(__file__).resolve().parent / 'reference'
DEFAULT_ENGLISH = REFERENCE / 'bg1-english.tra'
DEFAULT_RUSSIAN = REFERENCE / 'bgee.tra'
ENGLISH_HEADING = re.compile(r'^[ \t]*STATISTICS[ \t]*:[ \t]*\r?$', re.I | re.M)
RUSSIAN_HEADING = re.compile(r'^[ \t]*ПАРАМЕТРЫ[ \t]*:[ \t]*\r?$', re.I | re.M)
# Labels can contain digits (THAC0), parentheses and nested indentation.
LABEL = re.compile(r'^[ \t]*(?:[–—•-][ \t]*)?([^\W\d_][^:\r\n]*):', re.M)
SHORT_LABELS = {
    'chance to score a critical hit': ('Chance', 'Critical Hit'),
    'creates a globe of anti-magic around the user': ('Anti-magic',),
    'damage done to user': ('Damage',),
    'resistance to magic damage': ('Magic Damage Resistance',),
    'resistance to missile damage': ('Missile Damage Resistance',),
}
KEYWORD_FORMS = {
    'anti-magic': ('anti-magic', 'antimagic', 'anti magic'),
    'magic damage resistance': ('magic damage resistance', 'resistance to magic damage'),
    'missile damage resistance': ('missile damage resistance', 'resistance to missile damage'),
}

ITEM_INSTRUCTION = (
    'This line is an item description. Use the paired English/Russian STATISTICS '
    'example ONLY as a template for statistics terminology, headings, section order, '
    'indentation and layout. Translate STATISTICS as ПАРАМЕТРЫ. Include every target '
    'property and restriction, including fields absent from the example. Do not add '
    'example-only sections or copy its values, abilities, requirements or item identity. '
    'Preserve the target numbers, signs, percentages, dice expressions and engine tokens. '
    'Requirements may reorder naturally, e.g. 5 Strength becomes Сила 5. Use the glossary '
    'as usual. Translate the narrative before STATISTICS faithfully under the ordinary '
    'translation rules; the template applies ONLY to statistics. Do not rewrite the '
    'narrative to resemble the reference. Return the complete item description.'
)


def statistics_section(text, *, russian=False):
    """Return the heading and everything after it; never include narrative prose."""
    match = (RUSSIAN_HEADING if russian else ENGLISH_HEADING).search(text)
    return text[match.start():].strip().replace('\r\n', '\n') if match else None


def statistics_labels(section):
    """All colon-labelled fields/sections, normalized only for matching."""
    labels = {}
    for match in LABEL.finditer(section or ''):
        label = ' '.join(match[1].split())
        if label.casefold() in {'statistics', 'параметры'}:
            continue
        resistance = re.fullmatch(r'Target receives ((?:Acid|Cold|Electrical|Fire) Resistance)', label, re.I)
        if resistance:
            label = resistance[1].title()
        if label.casefold().startswith('damage type ('):
            concepts = ('Damage Type',)
        else:
            concepts = SHORT_LABELS.get(label.casefold(), (label,))
        labels.update((concept.casefold(), concept) for concept in concepts)
        if label.casefold().startswith('save vs.') or label.casefold() == 'saving throws':
            labels['save'] = 'Save'
    return labels


def statistics_parts(text):
    """Split translated/source item text without relaxing narrative validation."""
    match = ENGLISH_HEADING.search(text) or RUSSIAN_HEADING.search(text)
    return (text[:match.start()], text[match.end():]) if match else None


def statistics_numbers(text):
    """A conservative inventory, allowing reordered requirements and decimal commas."""
    text = text.replace('−', '-').replace('–', '-').replace('—', '-')
    dice = re.compile(r'(?<!\w)\d+\s*[dDдДкК]\s*\d+(?:\s*[+-]\s*\d+)?')
    expressions = [re.sub(r'\s+', '', value).lower().replace('д', 'd').replace('к', 'd')
                   for value in dice.findall(text)]
    remaining = dice.sub(' ', text)
    numbers = re.findall(r'(?<![\w])[-+]?\d+(?:[.,]\d+)?\s*%?', remaining)
    return Counter(expressions + [value.strip().replace(' ', '').replace(',', '.') for value in numbers])


@dataclass(frozen=True)
class ItemTemplate:
    reference: int
    english: str
    russian: str
    keywords: frozenset
    kind: str | None = None


class ItemTemplateIndex:
    def __init__(self, english=DEFAULT_ENGLISH, russian=DEFAULT_RUSSIAN):
        self.english_path, self.russian_path = Path(english), Path(russian)
        en = parse_tra(read_text(english), allow_references=True)
        ru = parse_tra(read_text(russian), allow_references=True)
        self.templates = []
        self.skipped = []
        self.english_labels, self.russian_labels = {}, {}
        self.frequencies, self.russian_frequencies = Counter(), Counter()
        for number, entry in sorted(en.items()):
            section = statistics_section(entry.variants[0].text) if entry.variants else None
            if section is None:
                continue
            translated = ru.get(number)
            target = (statistics_section(translated.variants[0].text, russian=True)
                      if translated and translated.variants else None)
            if not target:
                self.skipped.append(number)
                continue
            labels, ru_labels = statistics_labels(section), statistics_labels(target)
            self.english_labels.update(labels)
            self.russian_labels.update(ru_labels)
            self.russian_frequencies.update(ru_labels.keys())
            self.templates.append(ItemTemplate(number, section, target, frozenset(), self.kind(labels.keys())))
        if not self.templates:
            raise ValueError('Item references contain no paired STATISTICS/ПАРАМЕТРЫ descriptions')
        self.patterns = []
        for key in sorted(self.english_labels):
            for form in KEYWORD_FORMS.get(key, (key,)):
                pattern = r'(?<!\w)' + r'\s+'.join(re.escape(part) for part in form.split()) + r'(?!\w)'
                self.patterns.append((key, re.compile(pattern, re.I)))
        originals, self.templates = self.templates, []
        for item in originals:
            keys = frozenset(self.keywords(item.english))
            self.frequencies.update(keys)
            self.templates.append(ItemTemplate(item.reference, item.english, item.russian, keys, item.kind))

    def keywords(self, section):
        """Recognize concepts anywhere in statistics, longest non-overlapping match first."""
        spans = [(match.start(), match.end(), key) for key, pattern in self.patterns
                 for match in pattern.finditer(section)]
        occupied, found = set(), set()
        for start, end, key in sorted(spans, key=lambda span: (-(span[1] - span[0]), span[0], span[2])):
            positions = set(range(start, end))
            if not positions & occupied:
                found.add(key)
                occupied.update(positions)
        # Unknown target labels remain visible in diagnostics, without turning
        # familiar phrases containing known concepts into new long keywords.
        for key, label in statistics_labels(section).items():
            if key not in self.english_labels and not any(pattern.search(label) for _, pattern in self.patterns):
                found.add(key)
        return found

    def keyword_inventory(self):
        def entries(labels, frequencies):
            return [{'keyword': labels[key], 'normalized': key, 'items': frequencies[key]}
                    for key in sorted(labels)]
        return {'paired_items': len(self.templates), 'skipped_unpaired': self.skipped,
                'english': entries(self.english_labels, self.frequencies),
                'russian': entries(self.russian_labels, self.russian_frequencies)}

    @staticmethod
    def kind(keys):
        keys = set(keys)
        if keys & {'damage', 'speed factor', 'proficiency type'}:
            return 'weapon'
        if 'armor class' in keys:
            return 'armor'
        return None

    def closest(self, text):
        section = statistics_section(text)
        if section is None:
            return None
        # Lore and differing line endings cannot affect template selection.
        return self._closest_statistics(section)

    @lru_cache(maxsize=2048)
    def _closest_statistics(self, section):
        keys = frozenset(self.keywords(section))
        source_kind = self.kind(statistics_labels(section))
        count = len(self.templates)
        def weight(key):
            return 1 + math.log((count + 1) / (self.frequencies[key] + 1))
        target_weight = sum(map(weight, keys))
        def rank(item):
            overlap = sum(map(weight, keys & item.keywords))
            # Weighted F2 favors coverage, with a penalty for unrelated sections.
            denominator = 4 * target_weight + sum(map(weight, item.keywords))
            score = 5 * overlap / denominator if denominator else 0
            a, b = source_kind, item.kind
            if a and a != b:
                score *= 0.7
            return score, len(keys & item.keywords), -len(item.english), -item.reference
        selected = max(self.templates, key=rank)
        return {'reference': f'@{selected.reference}', 'score': round(rank(selected)[0], 6),
                'matched_keywords': sorted(keys & selected.keywords),
                'unmatched_keywords': sorted(keys - selected.keywords),
                'extra_keywords': sorted(selected.keywords - keys),
                'english_statistics': selected.english, 'russian_statistics': selected.russian}


def source_items(path, tra_ref=None):
    path = Path(path)
    if path.suffix.casefold() == '.tra':
        entries = parse_tra(read_text(path), allow_references=True)
        if tra_ref is not None and tra_ref not in entries:
            raise ValueError(f'{path}: missing @{tra_ref}')
        for number, entry in entries.items():
            if (tra_ref is None or number == tra_ref) and entry.variants:
                yield f'@{number}', entry.variants[0].text
    elif path.suffix.casefold() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            column = next((name for name in ('Dialogue_Text', 'Text', 'English_Text')
                           if name in (reader.fieldnames or [])), None)
            if not column:
                raise ValueError(f'{path}: no Dialogue_Text, Text or English_Text column')
            for i, row in enumerate(reader, 1):
                yield row.get('Additional_Info') or row.get('Reference') or str(i), row[column]
    else:
        yield path.name, read_text(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', help='Target .tra, dialogue/unused .csv, or description text file')
    parser.add_argument('--tra-ref', type=int, help='Select one source TRA entry by number')
    parser.add_argument('--reference-english', default=DEFAULT_ENGLISH, type=Path)
    parser.add_argument('--reference-russian', default=DEFAULT_RUSSIAN, type=Path)
    parser.add_argument('--list-keywords', action='store_true', help='List all observed English/Russian statistics labels')
    parser.add_argument('--output', type=Path, help='Write JSON to this file instead of stdout')
    args = parser.parse_args(argv)
    if not args.list_keywords and not args.source:
        parser.error('provide a source file or --list-keywords')
    if args.tra_ref is not None and (not args.source or Path(args.source).suffix.casefold() != '.tra'):
        parser.error('--tra-ref requires a source .tra file')
    try:
        index = ItemTemplateIndex(args.reference_english, args.reference_russian)
        result = index.keyword_inventory() if args.list_keywords else [
            {'source': identifier, **match}
            for identifier, text in source_items(args.source, args.tra_ref)
            if (match := index.closest(text)) is not None]
        output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            args.output.write_text(output, encoding='utf-8')
        else:
            print(output, end='')
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
