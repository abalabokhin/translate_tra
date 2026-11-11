"""Read TRA literals without matching entries inside comments or other strings.

Tracks literal spans so updates preserve comments, whitespace and sound references.
Supports ~...~, "...", %...%, ~~~~~...~~~~~, concatenation and gender pairs.
References can optionally be inspected as metadata, without executing WeiDU.
See TRA_FORMAT.md and TRA.ebnf for syntax, sources and deliberate boundaries.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import chardet

ENTRY_START = re.compile(r'@(-?[0-9]+)')
REFERENCE = re.compile(r'[#@]-?[0-9]+')
FORCED_REFERENCE = re.compile(r'!(-?[0-9]+)')
LINE_END = re.compile(r'[\r\n]')
BARE_STRING = re.compile(r'[0-9A-Za-z_][0-9A-Za-z_#.-]*')
# Dlexer supplies TRA's String token too. Its exact uppercase keywords are
# reserved; ordinary bare identifiers (including EXIT2) are literal strings.
RESERVED_STRINGS = set('''ADD_STATE_TRIGGER ADD_TRANS_ACTION ADD_TRANS_TRIGGER
ALTER_TRANS APPEND APPENDI APPEND_EARLY AT A_S_T A_T_T BEGIN BRANCH CHAIN CHAIN2
CHAIN3 COPY_TRANS COPY_TRANS_LATE DO END EXTEND EXTEND_BOTTOM EXTEND_BOTTOM_REGEXP
EXTEND_TOP EXTEND_TOP_REGEXP EXTERN EXIT FLAGS GOTO IF IF_FILE_EXISTS INTERJECT
INTERJECT_COPY_TRANS INTERJECT_COPY_TRANS2 INTERJECT_COPY_TRANS3 INTERJECT_COPY_TRANS4
I_C_T I_C_T2 I_C_T3 I_C_T4 JOURNAL REPLACE REPLACE_ACTION_TEXT
REPLACE_ACTION_TEXT_PROCESS REPLACE_ACTION_TEXT_PROCESS_REGEXP
REPLACE_ACTION_TEXT_REGEXP REPLACE_SAY REPLACE_STATE_TRIGGER REPLACE_TRIGGER_TEXT
REPLACE_TRIGGER_TEXT_REGEXP REPLACE_TRANS_ACTION REPLACE_TRANS_TRIGGER REPLY
R_A_T R_A_T_P_R R_S_T R_T_T SAFE SAY SET_WEIGHT SOLVED_JOURNAL THEN UNLESS
UNSOLVED_JOURNAL WEIGHT'''.split())


def _bare_string(content, pos):
    match = BARE_STRING.match(content, pos)
    return match if match and match[0] not in RESERVED_STRINGS else None


@dataclass
class TraVariant:
    text: str
    start: int
    text_end: int
    end: int
    delimiter: str
    sound: str | None
    parts: list[tuple[int, int, str]]


@dataclass
class TraEntry:
    number: int
    variants: list[TraVariant]
    reference: str | None = None
    forced_references: tuple[int, ...] = ()


def read_text(path):
    raw = Path(path).read_bytes()
    try:
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        # Recent chardet versions sample only the first 200 KB by default. A
        # long ASCII header must not hide legacy characters later in the file.
        try:
            encoding = chardet.detect(raw, max_bytes=len(raw))['encoding']
        except TypeError:
            # Older versions inspect the complete input and lack max_bytes.
            encoding = chardet.detect(raw)['encoding']
        if not encoding:
            raise ValueError(f'Cannot detect encoding of {path}')
        return raw.decode(encoding)


def _trivia(content, pos):
    while pos < len(content):
        if content[pos].isspace():
            pos += 1
        elif content.startswith('//', pos):
            # WeiDU files can use CRLF, LF or legacy CR line endings.
            end = LINE_END.search(content, pos + 2)
            pos = len(content) if end is None else end.end()
        elif content.startswith('/*', pos):
            depth = 1
            pos += 2
            while depth:
                if pos >= len(content):
                    raise ValueError('Unterminated TRA block comment')
                if content.startswith('/*', pos):
                    depth += 1
                    pos += 2
                elif content.startswith('*/', pos):
                    depth -= 1
                    pos += 2
                else:
                    pos += 1
        else:
            break
    return pos


def _literal(content, pos):
    delimiter = '~~~~~' if content.startswith('~~~~~', pos) else content[pos:pos + 1]
    if delimiter not in ('~', '"', '%', '~~~~~'):
        bare = _bare_string(content, pos)
        if bare:
            return bare[0], bare.end(), ''
        raise ValueError(f'Expected TRA string at character {pos}')
    end = content.find(delimiter, pos + len(delimiter))
    if end < 0:
        raise ValueError(f'Unterminated TRA string at character {pos}')
    return content[pos + len(delimiter):end], end + len(delimiter), delimiter


def _variant(content, start):
    text, text_end, delimiter = _literal(content, start)
    parts = [(start, text_end, delimiter)]
    pos = _trivia(content, text_end)
    while content[pos:pos + 1] == '^':
        part_start = _trivia(content, pos + 1)
        part, text_end, part_delimiter = _literal(content, part_start)
        parts.append((part_start, text_end, part_delimiter))
        text += part
        pos = _trivia(content, text_end)
    end = text_end
    sound = None
    if content[pos:pos + 1] == '[':
        sound_end = content.find(']', pos + 1)
        if sound_end < 0:
            raise ValueError(f'Unterminated sound reference at character {pos}')
        sound = content[pos:sound_end + 1]
        end = sound_end + 1
    return TraVariant(text, start, text_end, end, delimiter, sound, parts)


def parse_tra(content, *, allow_references=False, duplicate_policy='error'):
    """Read physical entries without game/runtime evaluation.

    Defaults suit safe literal-only updating: duplicate IDs and nonliteral values
    fail. Inspection/name collection may opt into reference metadata and WeiDU's
    last-definition-wins policy. Referenced entries have no literal variants.
    """
    if duplicate_policy not in ('error', 'last'):
        raise ValueError('duplicate_policy must be error or last')
    entries = {}
    pos = _trivia(content, 1 if content.startswith('\ufeff') else 0)
    while pos < len(content):
        match = ENTRY_START.match(content, pos)
        if not match:
            raise ValueError(f'Unsupported TRA syntax at character {pos}: {content[pos:pos + 30]!r}')
        number = int(match[1])
        if number in entries and duplicate_policy == 'error':
            raise ValueError(f'Duplicate TRA entry @{number}')
        equals = _trivia(content, match.end())
        if content[equals:equals + 1] != '=':
            raise ValueError(f'Expected = after TRA entry @{number} at character {equals}')
        start = _trivia(content, equals + 1)
        forced = []
        while (force := FORCED_REFERENCE.match(content, start)) is not None:
            forced.append(int(force[1]))
            start = _trivia(content, force.end())
        reference = REFERENCE.match(content, start)
        dynamic = content[start:start + 1] == '('
        if (forced or reference or dynamic) and not allow_references:
            raise ValueError(f'TRA entry @{number} requires reference inspection; '
                             'cannot safely update as a literal-only entry')
        if reference:
            entries[number] = TraEntry(number, [], reference[0], tuple(forced))
            pos = _trivia(content, reference.end())
            continue
        if dynamic:
            # AT takes one String token, not a runtime-evaluated expression.
            at = _trivia(content, start + 1)
            token = re.match(r'AT\b', content[at:])
            if token is None:
                raise ValueError(f'Expected AT in TRA reference at character {at}')
            variable_start = _trivia(content, at + token.end())
            _, variable_end, _ = _literal(content, variable_start)
            close = _trivia(content, variable_end)
            if content[close:close + 1] != ')':
                raise ValueError(f'Expected ) in TRA reference at character {close}')
            entries[number] = TraEntry(number, [], content[start:close + 1], tuple(forced))
            pos = _trivia(content, close + 1)
            continue
        first = _variant(content, start)
        variants = [first]
        pos = _trivia(content, first.end)
        if content[pos:pos + 1] in ('~', '"', '%') or _bare_string(content, pos):
            second = _variant(content, pos)
            variants.append(second)
            pos = _trivia(content, second.end)
        entries[number] = TraEntry(number, variants, forced_references=tuple(forced))
    return entries


def literal(text, preferred='~'):
    for delimiter in dict.fromkeys((preferred, '~', '"', '%', '~~~~~')):
        if delimiter not in text:
            return delimiter + text + delimiter
    raise ValueError('Translation contains every supported TRA delimiter')


def replace_entry(content, entry, male, female):
    """Replace literal spans only; retain both original sound variants if present."""
    if entry.reference is not None or entry.forced_references:
        raise ValueError(f'Cannot rewrite reference-valued TRA entry @{entry.number}')
    first = entry.variants[0]
    def translated_parts(variant, text):
        # Keep concatenation operators and comments in place; the translation
        # lives in the first literal and the remaining literals become empty.
        return [(start, end, literal(text if i == 0 else '', delimiter))
                for i, (start, end, delimiter) in enumerate(variant.parts)]
    edits = translated_parts(first, male)
    if len(entry.variants) == 2:
        second = entry.variants[1]
        edits.extend(translated_parts(second, female))
    elif male != female:
        sound = f' {first.sound}' if first.sound is not None else ''
        edits.append((first.end, first.end, ' ' + literal(female, first.delimiter) + sound))
    for start, end, value in sorted(edits, key=lambda edit: edit[0], reverse=True):
        content = content[:start] + value + content[end:]
    return content
