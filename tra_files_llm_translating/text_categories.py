"""Contextual CSVs for BAF displays, journals, resource text and remaining TRA literals.

Uses the routing/usage scanner's physical TRA identities. Never searches arbitrary
TRA files to satisfy a reference. BAF parsing is structural (strings/comments,
balanced calls, IF/THEN/RESPONSE/END), independent of installer regex heuristics.
"""
from collections import defaultdict, Counter
from dataclasses import dataclass
import csv
import hashlib
import json
from pathlib import Path
import re
import struct

from translation_common import DIALOGUE_COLUMNS, write_csv, read_csv, parse_reference


EXTRA_COLUMNS = ['Source_Female_Text', 'Source_Has_Female', 'Text_Type',
                 'Speaker_Gender', 'Display_Target', 'Resource', 'Field',
                 'Source_Context', 'Usage_Context']
COLUMNS = DIALOGUE_COLUMNS + EXTRA_COLUMNS


def render(tokens):
    return ' '.join(json.dumps(t.value, ensure_ascii=False) if t.kind == 'string' else t.value
                    for t in tokens)


def word(token, value):
    return token.kind == 'word' and token.value.upper() == value


@dataclass
class Call:
    name: str
    args: list
    line: int


def calls(tokens):
    """Top-level action calls; nested object selectors remain argument tokens."""
    i = 0
    while i < len(tokens):
        if tokens[i].kind != 'word' or i + 1 == len(tokens) or tokens[i + 1].value != '(':
            i += 1
            continue
        start, depth, square, args = i + 2, 1, 0, []
        j = start
        while j < len(tokens):
            token = tokens[j]
            if token.kind == 'word':
                depth += (token.value == '(') - (token.value == ')')
                square += (token.value == '[') - (token.value == ']')
                if token.value == ',' and depth == 1 and square == 0:
                    args.append(tokens[start:j])
                    start = j + 1
                if depth == 0:
                    if start < j:
                        args.append(tokens[start:j])
                    break
            j += 1
        if depth:
            raise ValueError(f'Unclosed BAF action {tokens[i].value} at line {tokens[i].line}')
        yield Call(tokens[i].value, args, tokens[i].line)
        i = j + 1


def baf_responses(tokens):
    """Keep alternative RESPONSE branches separate; never invent a dialogue edge."""
    i, block = 0, 0
    while i < len(tokens):
        if not word(tokens[i], 'IF'):
            raise ValueError(f'Expected BAF IF at line {tokens[i].line}: {tokens[i].value!r}')
        block += 1
        start = i + 1
        depth = 0
        while i + 1 < len(tokens):
            i += 1
            t = tokens[i]
            if t.kind == 'word':
                depth += (t.value == '(') - (t.value == ')')
            if depth == 0 and word(t, 'THEN'):
                break
        else:
            raise ValueError(f'BAF block {block}: missing THEN')
        condition = render(tokens[start:i])
        i += 1
        response = 0
        while i < len(tokens) and not word(tokens[i], 'END'):
            if not word(tokens[i], 'RESPONSE'):
                raise ValueError(f'BAF block {block}: expected RESPONSE at line {tokens[i].line}')
            response += 1
            i += 1
            # Weight is a native number, not a TRA/TLK reference.
            if i >= len(tokens) or not re.fullmatch(r'#?\d+', tokens[i].value):
                raise ValueError(f'BAF block {block}: invalid RESPONSE weight')
            weight = tokens[i].value
            i += 1
            start, depth = i, 0
            while i < len(tokens):
                t = tokens[i]
                if depth == 0 and (word(t, 'RESPONSE') or word(t, 'END')):
                    break
                if t.kind == 'word':
                    depth += (t.value == '(') - (t.value == ')')
                i += 1
            yield block, response, weight, condition, tokens[start:i]
        if i >= len(tokens):
            raise ValueError(f'BAF block {block}: missing END')
        i += 1


@dataclass(frozen=True)
class Actor:
    name: str
    gender: str = 'unknown'
    kind: str = 'unknown'


class ActorIndex:
    """CRE script owners and ARE region owners, plus optional reviewed actor data."""
    def __init__(self, mod_root, cre_folders=(), actors_file=None):
        self.by_name = defaultdict(set)
        self.by_script = defaultdict(set)
        self.by_dialogue = defaultdict(set)
        self.genders = {}
        if actors_file:
            with Path(actors_file).open(encoding='utf-8-sig', newline='') as handle:
                for row in csv.reader(handle):
                    if len(row) >= 2:
                        self.genders[row[0].casefold()] = row[1]
        seen = set()
        # Mod resources have precedence over external game reference CREs.
        for root in [Path(mod_root)] + [Path(p) for p in cre_folders]:
            for path in sorted(root.rglob('*')):
                if path.suffix.casefold() != '.cre' or path.stem.casefold() in seen:
                    continue
                seen.add(path.stem.casefold())
                data = path.read_bytes()[:0x2d4]
                if len(data) < 0x2d4 or data[:8] != b'CRE V1.0':
                    continue
                identity = self.string(data, 0x280, 32) or path.stem.upper()
                gender = self.genders.get(identity.casefold(),
                            {1: 'MALE', 2: 'FEMALE', 3: 'OTHER', 4: 'NEITHER'}.get(data[0x275], 'unknown'))
                actor = Actor(identity, gender, 'creature')
                for alias in (identity, path.stem):
                    self.by_name[alias.casefold()].add(actor)
                dialogue = self.string(data, 0x2cc, 8)
                if dialogue and dialogue.casefold() != 'none':
                    self.by_dialogue[dialogue.casefold()].add(actor)
                for offset in (0x248, 0x250, 0x258, 0x260, 0x268):
                    script = self.string(data, offset, 8)
                    if script and script.casefold() != 'none':
                        self.by_script[script.casefold()].add(actor)
        for path in sorted(Path(mod_root).rglob('*')):
            if path.suffix.casefold() != '.are':
                continue
            data = path.read_bytes()
            if len(data) < 0x9c or data[:8] != b'AREAV1.0':
                continue
            area = Actor('AREA:' + path.stem.upper(), 'unknown', 'area')
            script = self.string(data, 0x94, 8)
            self.by_script[(script or path.stem).casefold()].add(area)
            count = struct.unpack_from('<H', data, 0x5a)[0]
            offset = struct.unpack_from('<I', data, 0x5c)[0]
            if offset + count * 0xc4 > len(data):
                continue
            for index in range(count):
                region = data[offset + index * 0xc4:offset + (index + 1) * 0xc4]
                name, script = self.string(region, 0, 32), self.string(region, 0x7c, 8)
                actor = Actor('REGION:' + name, 'unknown', 'object')
                self.by_name[name.casefold()].add(actor)
                if script:
                    self.by_script[script.casefold()].add(actor)

    @staticmethod
    def string(data, offset, length):
        return data[offset:offset + length].split(b'\0')[0].decode('ascii', errors='replace')

    def owner(self, script):
        owners = self.by_script.get(Path(script).stem.casefold(), set())
        return self.combine(owners, Actor('UNKNOWN:' + Path(script).stem, 'unknown', 'unknown'))

    def dialogue_gender(self, name):
        key = name.casefold()
        if re.fullmatch(r'player[2-6]', name, re.I):
            return 'unknown'
        if key in {'player', 'player1'}:
            return 'player'
        if key in self.genders:
            return self.genders[key]
        owners = self.by_dialogue.get(key) or self.by_name.get(key, set())
        genders = {actor.gender for actor in owners}
        return next(iter(genders)) if len(genders) == 1 else 'unknown'

    @staticmethod
    def combine(actors, fallback):
        if not actors:
            return fallback
        if len(actors) == 1:
            return next(iter(actors))
        actors = sorted(actors, key=lambda a: (a.name, a.gender))
        return Actor(';'.join(a.name for a in actors),
                     ';'.join(a.gender for a in actors), 'shared')

    def target(self, tokens, executor):
        if len(tokens) == 1:
            name = tokens[0].value
            if name.casefold() == 'myself':
                return executor
            if re.fullmatch(r'player[1-6]', name, flags=re.I):
                return Actor('Player' + name[-1], 'player' if name[-1] == '1' else 'unknown', 'party')
            fallback = Actor(name, self.genders.get(name.casefold(), 'unknown'))
            return self.combine(self.by_name.get(name.casefold(), set()), fallback)
        return Actor(render(tokens), 'unknown', 'selector')


class CategorizedTextBuilder:
    def __init__(self, parser, batch_size=40, cre_folders=(), actors_file=None):
        if not parser.usage:
            raise ValueError('Categorized extraction requires --tp2-file for reference routing')
        if batch_size < 1:
            raise ValueError('Category batch size must be positive')
        self.parser, self.usage = parser, parser.usage
        self.batch_size = batch_size
        self.inventory = {}
        for filename, entries in parser.tra_cache.items():
            path = (Path(parser.tra_folder) / filename).resolve()
            for number in entries:
                self.inventory[(path, number)] = self.usage.table(path)[number]
        self.actors = ActorIndex(self.usage.tp2.parent, cre_folders, actors_file)
        self.groups = defaultdict(list)
        self.claimed = set()
        self.native_tlk_uses = []
        self.hardcoded_context = []

    @staticmethod
    def safe(value):
        value = re.sub(r'[^A-Za-z0-9_#.-]+', '_', str(value)).strip('._').casefold() or 'unknown'
        if len(value) > 100:
            value = value[:80] + '_' + hashlib.sha256(value.encode()).hexdigest()[:8]
        return value

    def row(self, key, actor, text_type, location, **metadata):
        if key not in self.inventory:
            raise ValueError(f'{location}: resolved TRA {key[0]}:@{key[1]} is outside the supplied flat TRA folder')
        entry = self.inventory[key]
        row = dict.fromkeys(COLUMNS, '')
        row.update(Actor=actor.name, Speaker_Gender=actor.gender,
                   Dialogue_Text=entry.variants[0].text, TRA_Reference=f'@{key[1]}',
                   Additional_Info=f'TRA:{key[0].name}:@{key[1]}',
                   Source_Female_Text=entry.variants[1].text if len(entry.variants) == 2 else '',
                   Source_Has_Female='1' if len(entry.variants) == 2 else '', Text_Type=text_type,
                   Source_Context=location)
        row.update(metadata)
        self.claimed.add(key)
        return row

    def source_label(self, source):
        source = Path(source)
        try:
            return str(source.relative_to(self.usage.tp2.parent))
        except ValueError:
            try:
                return str(source.relative_to(self.usage.source_root))
            except ValueError:
                return str(source)

    def resolve(self, source, token):
        path, entry = self.usage.resolve(source, int(token.value[1:]))
        return (path, entry.number) if entry.variants else None

    def displays(self, source, actions, executor):
        for call in calls(actions):
            name = call.name.upper()
            if name == 'ACTIONOVERRIDE' and len(call.args) == 2:
                target = self.actors.target(call.args[0], executor)
                yield from self.displays(source, call.args[1], target)
            elif name == 'CUTSCENEID' and call.args:
                executor = self.actors.target(call.args[0], executor)
            elif name in {'DISPLAYSTRING', 'DISPLAYSTRINGHEAD', 'ADDMAPNOTE'} and len(call.args) >= 2:
                values = call.args[-1] if name == 'ADDMAPNOTE' else call.args[1]
                if len(values) == 1 and values[0].kind == 'ref':
                    key = self.resolve(source, values[0])
                    if key:
                        target = (Actor('NARRATOR') if name == 'ADDMAPNOTE'
                                  else self.actors.target(call.args[0], executor))
                        yield call, target, key
                elif len(values) == 1 and values[0].kind == 'string':
                    self.hardcoded_context.append(f'{self.source_label(source)}:{call.line}: {call.name}: {render(values)}')
                else:
                    self.native_tlk_uses.append(f'{self.source_label(source)}:{call.line}: {call.name}({render(values)})')

    def response_rows(self, source, group, owner, actions, context):
        previous = ''
        displays = list(self.displays(source, actions, owner))
        readonly = '; '.join(f'{call.name}: {render(call.args[1])}' for call in calls(actions)
                             if call.name.upper() in {'DISPLAYSTRING', 'DISPLAYSTRINGHEAD'}
                             and len(call.args) > 1 and len(call.args[1]) == 1 and call.args[1][0].kind == 'string')
        for call, target, key in displays:
            location = f'{self.source_label(source)}:{call.line}; {context}'
            if call.name.upper() == 'ADDMAPNOTE':
                row = self.row(key, Actor('NARRATOR'), 'map_label', location)
                self.groups['map_labels__' + self.safe(key[0].stem)].append(row)
                continue
            text = self.inventory[key].variants[0].text.strip()
            narrative = text.startswith('(') and text.endswith(')')
            actor = Actor('NARRATOR') if narrative else target
            text_type = 'notification' if narrative else 'baf_dialogue'
            row = self.row(key, actor, text_type, location, Display_Target=target.name)
            row['Line_ID'] = f'l{len(self.groups[group]) + 1}'
            row['Predecessors'] = previous
            previous = row['Line_ID']
            row['Source_Context'] += '; action: ' + call.name + '; actions: ' + ', '.join(c.name for c in calls(actions))
            if readonly:
                row['Source_Context'] += '; read-only hardcoded context (leave unchanged): ' + readonly
            self.groups[group].append(row)

    def baf_files(self):
        for source in sorted(self.usage.source_fallbacks):
            if source.suffix.casefold() not in {'.baf', '.d'}:
                continue
            try:
                identity = str(source.relative_to(self.usage.tp2.parent))
            except ValueError:
                identity = str(source)
            identity = hashlib.sha256(identity.casefold().encode()).hexdigest()[:8]
            prefix = f'baf__{self.safe(source.stem)}__{identity}'
            if source.suffix.casefold() == '.d':
                for index, (line, actions) in enumerate(self.usage.embedded_actions(source), 1):
                    # A CHAIN may involve several speakers. Without a proven
                    # action owner, Myself stays unknown rather than assuming
                    # the D filename identifies its executing actor.
                    self.response_rows(source, prefix + f'__d_action{index:04d}',
                                       Actor('UNKNOWN:' + source.stem), actions, f'D DO action at line {line}')
            else:
                owner = self.actors.owner(source)
                for block, response, weight, condition, actions in baf_responses(self.usage.tokens(source)):
                    self.response_rows(source, prefix + f'__b{block:04d}_r{response:02d}', owner, actions,
                                       f'block {block}, RESPONSE {weight}; conditions: {condition}')

    def resource_category(self, context):
        slot = context.get('slot', '').upper()
        if slot in {'FJ_INFO_POINT_STRREF', 'FJ_NAME_STRREF', 'FJ_TOOLTIP'}:
            return 'area_text'
        resources = context.get('resources', [])
        suffixes = {Path(resource).suffix.casefold() for resource in resources}
        names = slot in {'NAME1', 'NAME2', '0X8', '0X08', '0XC', '0X0C'}
        descriptions = slot in {'DESC', 'DESC1', 'DESC2', 'IDENTIFIED_DESC', 'UNIDENTIFIED_DESC', '0X50', '0X54'}
        if suffixes == {'.itm'}:
            return 'item_name' if names else 'item_description' if descriptions else 'item_text'
        if suffixes == {'.spl'}:
            return 'spell_name' if names else 'spell_description' if descriptions else 'spell_text'
        if suffixes == {'.cre'}:
            if names:
                return 'creature_name'
            if slot in {'BIO', 'BIOGRAPHY'}:
                return 'biography'
            # CRE V1 sound strrefs occupy 0xa4..0x230. Other numeric
            # offsets are deliberately not guessed to be character speech.
            numeric = (int(slot, 16 if slot.startswith('0X') else 10)
                       if re.fullmatch(r'(?:0X[0-9A-F]+|\d+)', slot) else None)
            if numeric is not None:
                return 'character_sound' if 0xa4 <= numeric <= 0x230 and numeric % 4 == 0 else 'resource_text'
            return 'character_sound' if slot else 'resource_text'
        if suffixes == {'.sto'} and names:
            return 'store_name'
        if context.get('command', '').startswith('STRING_SET'):
            return 'game_text'
        return 'name' if names else 'description' if descriptions else 'unclassified'

    def other_entries(self):
        used_d = self.parser.used_tra_entries
        excluded = self.parser.excluded_tra_entries
        for key, entry in sorted(self.inventory.items()):
            short = key[0].name.casefold(), key[1]
            if short in excluded:
                continue
            if key in self.usage.journal_entries and short not in used_d:
                contexts = self.usage.consumers.get(key, [])
                location = '; '.join(f"{self.source_label(c['source'])}:{c['line']}" for c in contexts)
                row = self.row(key, Actor('Player1', 'player', 'party'), 'journal', location)
                title = re.match(r'^([^\r\n]{1,120})\r?\n\s*\r?\n', entry.variants[0].text)
                group = 'journal__' + self.safe(key[0].stem)
                if title:
                    group += '__' + self.safe(title[1])
                self.groups[group].append(row)
                continue
            if key in self.claimed or short in used_d:
                continue
            contexts = self.usage.consumers.get(key, [])
            actionable = [context for context in contexts if context.get('command')]
            categories = {self.resource_category(context) for context in actionable}
            category = next(iter(categories)) if len(categories) == 1 else 'shared_text' if categories else 'unclassified'
            resources = sorted({r for context in actionable for r in context.get('resources', [])})
            actor = Actor('NARRATOR')
            if category in {'creature_name', 'character_sound', 'biography'}:
                actors = {self.actors.target([SimpleToken(Path(resource).stem)], Actor('UNKNOWN')) for resource in resources}
                actor = self.actors.combine(actors, Actor('UNKNOWN'))
            location = '; '.join(f"{self.source_label(c['source'])}:{c['line']} {c.get('command', '')} {c.get('slot', '')}" for c in contexts)
            row = self.row(key, actor, category, location, Resource='; '.join(resources),
                           Field='; '.join(sorted({c.get('slot', '') for c in actionable})))
            if category.startswith(('item_', 'spell_')) and resources:
                # Names and descriptions of one resource share a file.
                resource_group = 'item' if category.startswith('item_') else 'spell'
                for resource in resources:
                    group = resource_group + '__' + self.safe(Path(resource).stem)
                    self.groups[group].append(dict(row, Resource=resource))
                continue
            elif category in {'character_sound', 'biography'}:
                group = category + '__' + self.safe(actor.name) + '__' + self.safe(actor.gender)
            else:
                group = category + '__' + self.safe(key[0].stem) + '__' + self.safe(actor.gender)
            self.groups[group].append(row)

    def write(self, output_folder):
        output_folder = Path(output_folder)
        if (output_folder / '_unused_tra_lines.csv').exists() or (output_folder / '_extraction_manifest.json').exists():
            raise ValueError('Use a fresh CSV output folder for categorized extraction')
        self.baf_files()
        self.other_entries()
        # Attach every observed context to every copy of a shared physical string,
        # including strings already extracted from D dialogues.
        uses = defaultdict(list)
        existing = []
        for path in sorted(output_folder.glob('*.csv')):
            header, rows = read_csv(path, DIALOGUE_COLUMNS)
            existing.append((path, header, rows))
            for row in rows:
                row.setdefault('Text_Type', 'dialogue')
                if not row.get('Speaker_Gender'):
                    row['Speaker_Gender'] = ';'.join(
                        self.actors.dialogue_gender(name)
                        for name in row['Actor'].split(';'))
                if row['TRA_Reference']:
                    uses[parse_reference(row['Additional_Info'])].append(row)
        for rows in self.groups.values():
            for row in rows:
                uses[parse_reference(row['Additional_Info'])].append(row)
        for rows in uses.values():
            descriptions = sorted({f"{r['Actor']} [{r.get('Speaker_Gender') or 'see actors.csv'}]; "
                                   f"{r.get('Text_Type') or 'dialogue'}; {r.get('Source_Context', '')}" for r in rows})
            context = 'Same physical TRA string; one translation must suit all these uses: ' + ' | '.join(descriptions)
            for row in rows:
                row['Usage_Context'] = context if len(rows) > 1 else ''
        for path, header, rows in existing:
            write_csv(path, header + [column for column in ('Text_Type', 'Speaker_Gender', 'Usage_Context')
                                     if column not in header], rows)
        files = []
        for group, rows in sorted(self.groups.items()):
            whole_unit = group.startswith(('baf__', 'item__', 'spell__', 'character_sound__'))
            size = len(rows) if whole_unit else self.batch_size
            for offset in range(0, len(rows), size):
                chunk = rows[offset:offset + size]
                filename = group + ('' if whole_unit else f'__{offset // size + 1:03d}') + '.csv'
                for i, row in enumerate(chunk, 1):
                    if not row['Line_ID']:
                        row['Line_ID'] = str(i)
                write_csv(output_folder / filename, COLUMNS, chunk)
                files.append(filename)
        excluded = {key for key in self.inventory if (key[0].name.casefold(), key[1]) in self.parser.excluded_tra_entries}
        dialogue = {key for key in self.inventory if (key[0].name.casefold(), key[1]) in self.parser.used_tra_entries}
        missing = set(self.inventory) - excluded - dialogue - self.claimed
        if missing:
            raise ValueError(f'Unexported TRA entries: {sorted(missing)}')
        category_entries = defaultdict(set)
        for rows in self.groups.values():
            for row in rows:
                category_entries[row['Text_Type']].add(parse_reference(row['Additional_Info']))
        manifest = {'inventory': len(self.inventory), 'dialogue_entries': len(dialogue),
                    'categorized_entries': len(self.claimed), 'excluded_entries': len(excluded),
                    'exported_distinct_entries': len(dialogue | self.claimed),
                    'shared_with_dialogue_entries': len(dialogue & self.claimed),
                    'categories': dict(Counter(row['Text_Type'] for rows in self.groups.values() for row in rows)),
                    'distinct_entries_by_category': {name: len(keys) for name, keys in category_entries.items()},
                    'csv_files': files, 'all_csv_files': sorted(files + [p.name for p, _, _ in existing]),
                    'native_tlk_uses': self.native_tlk_uses,
                    'hardcoded_context': self.hardcoded_context,
                    'unclassified': [r['Additional_Info'] for rows in self.groups.values() for r in rows
                                     if r['Text_Type'] == 'unclassified']}
        (output_folder / '_extraction_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        print(f'Created {len(files)} categorized CSVs covering {len(self.claimed)} distinct TRA entries')
        return manifest


@dataclass
class SimpleToken:
    value: str
    kind: str = 'word'
