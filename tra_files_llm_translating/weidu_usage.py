"""Static TRA routing and conservative installer-only usage analysis.

This is a focused WeiDU scanner, not an installer interpreter. Unknown constructs
keep entries eligible for translation. No installer, macro or patch is executed.
"""
import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
import fnmatch
from itertools import product

from tra_format import parse_tra, read_text

TOKEN_PATTERN = re.compile(r'@-?\d+|-?0[xX][0-9A-Fa-f]+|-\d+|'
                           r'[A-Za-z0-9_#][A-Za-z0-9_#./\\-]*|=>|==|!=|<=|>=|\|\||&&|[^\s]')
LINE_END = re.compile(r'[\r\n]')
DEFINITIONS = {'DEFINE_ACTION_FUNCTION', 'DEFINE_PATCH_FUNCTION',
               'DEFINE_ACTION_MACRO', 'DEFINE_PATCH_MACRO', 'DEFINE_DIMORPHIC_FUNCTION'}
FUNCTION_CALLS = {'LAF', 'LPF', 'LAUNCH_ACTION_FUNCTION', 'LAUNCH_PATCH_FUNCTION'}
MACRO_CALLS = {'LAM', 'LPM', 'LAUNCH_ACTION_MACRO', 'LAUNCH_PATCH_MACRO'}


def block_end(tokens, start):
    """Match BEGIN/END and function-call blocks without reading quoted code."""
    depth = 1
    for index in range(start + 1, len(tokens)):
        token = tokens[index]
        if token.kind != 'word':
            continue
        command = token.value.upper()
        if command == 'BEGIN' or command in FUNCTION_CALLS or command == 'WITH':
            depth += 1
        elif command == 'END':
            previous = tokens[index - 1].value.upper() if index and tokens[index - 1].kind == 'word' else ''
            following = (tokens[index + 1].value if index + 1 < len(tokens)
                         and tokens[index + 1].kind == 'word'
                         and tokens[index + 1].line == token.line else '')
            # END is also a valid integer variable, commonly used for buffer
            # offsets. These operand positions cannot close a WeiDU block.
            if following in {'=', '+', '-', '*', '/', '<', '>', '==', '!='} or previous in {
                    'SET', 'OUTER_SET', '(', '+', '-', '*', '/', '=',
                    'INSERT_BYTES', 'DELETE_BYTES', 'WRITE_ASCII', 'WRITE_ASCIIE',
                    'WRITE_ASCII_TERMINATE', 'WRITE_BYTE', 'WRITE_SHORT', 'WRITE_LONG'}:
                continue
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f'Unclosed {tokens[start].value} block at line {tokens[start].line}')


def definition_ranges(tokens):
    result = []
    index = 0
    while index < len(tokens):
        if tokens[index].kind == 'word' and tokens[index].value.upper() in DEFINITIONS:
            opening = next((i for i in range(index + 2, len(tokens))
                            if tokens[i].kind == 'word' and tokens[i].value.upper() == 'BEGIN'), None)
            if opening is None:
                raise ValueError(f'Function definition without BEGIN at line {tokens[index].line}')
            closing = block_end(tokens, opening)
            result.append((index, opening, closing))
            index = closing + 1
        else:
            index += 1
    return result


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int


def tokenize(text):
    """Ignore nested comments; keep quoted strings separate from commands/@IDs."""
    result = []
    pos = 0
    line = 1
    while pos < len(text):
        start = pos
        if text[pos].isspace():
            pos += 1
        elif text.startswith('//', pos):
            end = LINE_END.search(text, pos)
            pos = len(text) if end is None else end.start()
        elif text.startswith('/*', pos):
            depth = 1
            pos += 2
            while pos < len(text) and depth:
                if text.startswith('/*', pos):
                    depth += 1
                    pos += 2
                elif text.startswith('*/', pos):
                    depth -= 1
                    pos += 2
                else:
                    pos += 1
            if depth:
                raise ValueError(f'Unclosed comment at line {line}')
        elif text[pos] in '~"%':
            delimiter = '~~~~~' if text.startswith('~~~~~', pos) else text[pos]
            end = text.find(delimiter, pos + len(delimiter))
            if end < 0:
                raise ValueError(f'Unclosed string at line {line}')
            result.append(Token('string', text[pos + len(delimiter):end], line))
            pos = end + len(delimiter)
        else:
            match = TOKEN_PATTERN.match(text, pos)
            value = match[0]
            result.append(Token('ref' if re.fullmatch(r'@-?\d+', value) else 'word', value, line))
            pos += len(value)
        line += text[start:pos].count('\n')
    return result


def strings_after(tokens, index):
    values = []
    while index < len(tokens) and (tokens[index].kind == 'string' or
                                   re.search(r'[./\\]', tokens[index].value)):
        values.append(tokens[index].value)
        index += 1
    return values, index


def case_path(path):
    """Resolve existing paths without depending on filesystem case sensitivity."""
    path = Path(path).absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        if part == '..':
            current = current.parent
            continue
        if part == '.':
            continue
        exact = current / part
        if exact.exists():
            current = exact
            continue
        if not current.is_dir():
            return None
        matches = [p for p in current.iterdir() if p.name.casefold() == part.casefold()]
        if len(matches) > 1:
            raise ValueError(f'Ambiguous case-insensitive path: {path}')
        if not matches:
            return None
        current = matches[0]
    return current.resolve()


def case_glob(base, pattern):
    paths = [Path(base)]
    for part in Path(pattern).parts:
        if part == '.':
            continue
        if part == '..':
            paths = [path.parent for path in paths]
            continue
        next_paths = []
        for path in paths:
            if not path.is_dir():
                continue
            if not any(c in part for c in '*?['):
                exact = case_path(path / part)
                if exact:
                    next_paths.append(exact)
            else:
                next_paths.extend(child.resolve() for child in path.iterdir()
                                  if fnmatch.fnmatchcase(child.name.casefold(), part.casefold()))
        paths = next_paths
    return paths


class WeiduUsage:
    INSTALLER_COMMANDS = {
        'PRINT', 'PATCH_PRINT', 'FAIL', 'PATCH_FAIL', 'WARN', 'WARNING',
        'ACTION_WARN', 'BEGIN', 'SUBCOMPONENT', 'GROUP', 'DEPRECATED',
    }
    INCLUDE_COMMANDS = {'INCLUDE', 'REINCLUDE', 'PATCH_INCLUDE', 'PATCH_REINCLUDE', 'LOAD'}

    def __init__(self, tp2_file, source_language='english', tra_folder=None, source_root=None):
        self.tp2 = Path(tp2_file).resolve()
        self.tra_folder = Path(tra_folder).resolve() if tra_folder else None
        self.source_language = source_language
        self.source_root = Path(source_root) if source_root else Path(__file__).resolve().parents[2]
        self.variables = {}
        self.mod_prefixes = {self.tp2.parent.name.casefold(),
                             re.sub(r'^setup-', '', self.tp2.stem, flags=re.I).casefold()}
        self.ambiguous_variables = set()
        self.unknown_variables = set()
        self.variable_domains = defaultdict(set)
        self.tables = {}
        self.table_errors = {}
        self.usage = defaultdict(set)
        self.journal_entries = set()
        self.consumers = defaultdict(list)
        self.locations = defaultdict(list)
        self.warnings = []
        self.unresolved = []
        self.unresolved_occurrences = 0
        self._unresolved_keys = set()
        self.visited = set()
        self.include_results = {}
        self.sources = set()
        self.source_fallbacks = {}
        self.compilation_units = defaultdict(set)
        self.default_fallbacks = []
        self.complete = True
        self.ambiguous_files = set()
        self.uncertain_routing = False
        self.language = None
        self.language_declarations = []
        self.skip_reason = None
        self.source_data_issues = []
        self.auto_tra = []
        self.copy_aliases = []
        self._last_alias = {}
        self._alias_names = defaultdict(list)
        self.definitions = {}
        self.arrays = {}
        self.active_calls = set()
        self.source_contexts = defaultdict(list)
        self.optional_tables = set()
        self.notes = []
        self.deferred_numbers = set()
        self.opaque_external = False
        self.virtual_files = {}
        self.inline_templates = defaultdict(list)
        self.virtual_directories = set()
        self._virtual_index = {}
        self.using_references = {}
        self._tokens = {}
        self._paths = {}
        self._matching_tables = {}
        self._source_paths = {}
        self._dependency_roots = {}
        self._path_contexts = set()
        self._pending_contexts = []

    def warn(self, message):
        self.complete = False
        if message not in self.warnings:
            self.warnings.append(message)

    def tokens(self, path):
        if path not in self._tokens:
            text = self.virtual_files.get(path)
            if text is None:
                text = read_text(path)
            if path.suffix.casefold() not in {'.d', '.baf'}:
                inline = re.compile(r'^[ \t]*<<<<<<<<[ \t]*([^\r\n]+)[\r\n]+(.*?)>>>>>>>>',
                                    re.M | re.S)
                def save_inline(match):
                    raw_name = match[1].strip().strip('~"')
                    self.inline_templates[path].append((raw_name, match[2]))
                    name = self.expand(raw_name)
                    virtual = (self.tp2.parent / name).absolute()
                    self.put_virtual(virtual, match[2])
                    return '\n' * match[0].count('\n')
                text = inline.sub(save_inline, text)
            try:
                self._tokens[path] = tokenize(text)
            except ValueError as exc:
                raise ValueError(f'{path}: {exc}') from exc
        return self._tokens[path]

    def expand(self, value):
        value = re.sub(r'%s(?=[/\\]|$)', self.language or self.source_language, value)
        value = re.sub(r'%%([A-Za-z_][A-Za-z0-9_]*)%%',
                       lambda m: self.variables.get(self.variables.get(m[1].casefold(), '').casefold(), m[0]),
                       value)
        def replace(text, stack):
            def variable(match):
                name = match[1].casefold()
                if name in stack or name not in self.variables or len(stack) > 32:
                    return match[0]
                return replace(self.variables[name], stack | {name})
            return re.sub(r'%([^%]+)%', variable, text)
        return replace(value, set()).replace('\\', '/')

    @staticmethod
    def fallback_stack(paths):
        """Reloading the same source replaces it; it must not grow the stack."""
        return list(reversed(dict.fromkeys(reversed(paths))))

    def put_virtual(self, path, text):
        path = Path(path).resolve()
        self.virtual_files[path] = text
        self._virtual_index[str(path).casefold()] = path
        self._tokens.pop(path, None)
        self._paths.clear()
        self.virtual_directories.add(path.parent)

    def add_copy_alias(self, destination, original):
        key = destination.casefold()
        if self._last_alias.get(key) == original:
            return
        self._last_alias[key] = original
        self.copy_aliases.append((destination, original))
        self._alias_names[Path(destination).name.casefold()].append(original)
        self._paths.clear()

    def path(self, value, source):
        value = self.expand(value)
        if not value:
            return None
        if any(character in value for character in '%*?'):
            return None
        key = (value, source.parent)
        if key in self._paths:
            return self._paths[key]
        candidate = Path(value)
        if candidate.is_absolute():
            found = self._virtual_index.get(str(candidate).casefold())
            if not found and candidate in self.virtual_directories:
                found = candidate
            found = found or case_path(candidate)
            if found:
                self._paths[key] = found
                return found
        for base in (self.tp2.parent, self.tp2.parent.parent, source.parent):
            virtual = (base / candidate).absolute()
            existing = self._virtual_index.get(str(virtual).casefold())
            if existing or virtual in self.virtual_directories:
                self._paths[key] = existing or virtual
                return existing or virtual
            found = case_path(base / candidate)
            if found:
                self._paths[key] = found
                return found
        # Character-set helpers copy language folders into a generated workspace.
        # Resolve those read-only aliases back to their original source files.
        for destination, original in reversed(self.copy_aliases):
            if value.casefold() == destination.casefold():
                self._paths[key] = original
                return original
            if value.casefold().startswith(destination.casefold().rstrip('/') + '/'):
                rewritten = str(original).rstrip('/') + value[len(destination.rstrip('/')):]
                found = case_path(rewritten)
                if found:
                    self._paths[key] = found
                    return found
        # Other installed mods provide compatibility helpers (EET/BGT etc.).
        # Their checked-out sources may have an extra archive/repository folder.
        parts = candidate.parts
        if len(parts) > 1:
            local_roots = []
            if parts[0].casefold() in self.mod_prefixes:
                local_roots.append(self.tp2.parent)
            local_roots.extend(parent for parent in source.parents
                               if parent.name.casefold() == parts[0].casefold())
            for base in local_roots:
                found = case_path(base.joinpath(*parts[1:]))
                if found:
                    self._paths[key] = found
                    return found
            container = case_path(self.source_root / parts[0])
            if container and container.is_dir():
                for base in (container, container / container.name):
                    found = case_path(base.joinpath(*parts[1:]))
                    if found:
                        self._paths[key] = found
                        return found
            # A checkout wrapper need not have the same name as its mod folder:
            # e.g. SandrahEET/SandrahNPC, or IR_Revised overlaying ItemRevisions.
            component = parts[0].casefold()
            if component not in self._dependency_roots:
                roots = []
                if self.source_root.is_dir():
                    for checkout in self.source_root.iterdir():
                        if checkout.is_dir():
                            module = case_path(checkout / parts[0])
                            if module and module.is_dir() and module != self.tp2.parent:
                                roots.append(module)
                self._dependency_roots[component] = roots
            matches = [found for root in self._dependency_roots[component]
                       if (found := case_path(root.joinpath(*parts[1:])))]
            if len(matches) == 1:
                self._paths[key] = matches[0]
                self.notes.append(f'Resolved shared source {value!r} from {matches[0]}')
                return matches[0]
            if matches and all(p.is_file() for p in matches):
                first = matches[0].read_bytes()
                if all(p.read_bytes() == first for p in matches[1:]):
                    self._paths[key] = matches[0]
                    return matches[0]
        self._paths[key] = None
        return None

    def paths(self, value, source):
        # Inline names can contain variables read from a CRE or assigned after
        # the source was tokenized. Bind their names at the use site as WeiDU
        # does, rather than only when first reading the installer.
        expanded = self.expand(value)
        for templates in list(self.inline_templates.values()):
            for name, content in templates:
                if self.expand(name).casefold() == expanded.casefold():
                    virtual = (self.tp2.parent / expanded).absolute()
                    if self.virtual_files.get(virtual) != content:
                        self.put_virtual(virtual, content)
                    if '%' in expanded:
                        return [virtual]
        names = {name.casefold() for name in re.findall(r'%([^%]+)%', value)}
        alternatives = sorted(names.intersection(self.unknown_variables))
        choices = [sorted(self.variable_domains[name]) for name in alternatives]
        if alternatives and all(choices):
            count = 1
            for values in choices:
                count *= len(values)
            if count <= 256:
                found = set()
                for values in product(*choices):
                    mapping = dict(zip(alternatives, values))
                    variant = re.sub(r'%([^%]+)%', lambda m: mapping.get(m[1].casefold(), m[0]), value)
                    if variant == value:
                        continue
                    direct = self.path(variant, source)
                    if direct:
                        found.add(direct)
                if found:
                    return sorted(found)
        found = self.path(value, source)
        if found:
            return [found]
        expanded = self.expand(value)
        # Loops and function arguments often enumerate actual files. Index that
        # finite on-disk set without executing arbitrary WeiDU patch operations.
        if re.search(r'%[^%]+%', expanded):
            pattern = re.sub(r'%[^%]+%', '*', expanded)
            result = set()
            for destination, original in self.copy_aliases:
                if fnmatch.fnmatchcase(destination.casefold(), pattern.casefold()):
                    result.add(original)
            for base in (self.tp2.parent, self.tp2.parent.parent, source.parent):
                result.update(case_glob(base, pattern))
            for virtual in self.virtual_files:
                for base in (self.tp2.parent, self.tp2.parent.parent):
                    if fnmatch.fnmatchcase(str(virtual).casefold(), str(base / pattern).casefold()):
                        result.add(virtual)
            if result:
                self.notes.append(f'{source}: expanded file domain {value!r} to {len(result)} source paths')
            return sorted(result)
        return []

    def table(self, path):
        if path in self.table_errors:
            raise ValueError(self.table_errors[path])
        if path not in self.tables:
            try:
                content = self.virtual_files[path] if path in self.virtual_files else read_text(path)
                self.tables[path] = parse_tra(content, allow_references=True,
                                               duplicate_policy='last')
            except ValueError as exc:
                message = f'{path}: {exc}'
                self.table_errors[path] = message
                if message not in self.source_data_issues:
                    self.source_data_issues.append(message)
                raise ValueError(message) from exc
        return self.tables[path]

    def select_language(self):
        tokens = self.tokens(self.tp2)
        for i, token in enumerate(tokens[:-1]):
            if token.kind == 'word' and token.value.upper() == 'BACKUP':
                backup = tokens[i + 1].value.replace('\\', '/').split('/')
                if len(backup) > 1 and backup[0].casefold() != 'weidu_external':
                    self.mod_prefixes.add(backup[0].casefold())
        declarations = []
        for index, token in enumerate(tokens):
            if token.kind == 'word' and token.value.upper() == 'LANGUAGE':
                if index + 2 >= len(tokens):
                    continue
                name, directory = tokens[index + 1:index + 3]
                values, _ = strings_after(tokens, index + 3)
                if values:
                    declarations.append([name.value, directory.value] + values)
        self.language_declarations = declarations
        wanted = self.source_language.casefold()
        selected = [d for d in declarations if d[0].casefold() == wanted]
        if not selected:
            selected = [d for d in declarations if d[1].casefold() == wanted]
        if not selected:
            selected = [d for d in declarations if wanted == 'english' and
                        ('english' in d[0].casefold() or d[1].casefold() in {'en', 'en_us'})]
        if selected:
            # Explicit names win over a reused directory (Cernd), and separate
            # English revisions are selected in declaration order (TGC1E).
            selected = selected[:1]
            self.language = selected[0][1]
            # A missing LANGUAGE keyword is syntactically a list of extra file
            # names; do not silently load the next language into English.
            labels = {'russian', 'french', 'german', 'deutsch', 'polish', 'spanish',
                      'italian', 'chinese', 'portuguese', 'czech'}
            for i, value in enumerate(selected[0][2:-1], 2):
                if value.casefold() in labels and '/' not in value and '\\' not in value:
                    self.skip_reason = 'invalid_language_declaration'
                    self.source_data_issues.append(f'Missing LANGUAGE keyword before {value!r}: '
                                                   'another language is included in the selected fallback list')
        else:
            self.language = self.source_language
            self.skip_reason = 'no_language_declaration' if not declarations else 'no_selected_language'
        folder = self.tp2.parent.name
        # A root setup-foo.tp2 commonly refers to a sibling foo/ mod directory.
        guessed = re.sub(r'^setup-', '', self.tp2.stem, flags=re.I)
        sibling = case_path(self.tp2.parent / guessed)
        if sibling and sibling.is_dir():
            folder = sibling.name
        self.variables.update({'language': self.language, 'mod_folder': folder,
                               'mod_file': str(self.tp2), 'tp2_file_name': str(self.tp2)})
        if not declarations and not any(t.kind == 'string' and '.tra' in t.value.casefold()
                                       for t in tokens) and not any(
                                           t.value.upper() == 'AUTO_TRA' for t in tokens):
            self.skip_reason = 'not_a_localized_installer'
            return
        # Constant definitions before LANGUAGE can determine its paths.
        self.read_constants(tokens)
        if selected:
            self.default_fallbacks = self.resolve_paths(selected[0][2:], self.tp2, 'LANGUAGE')
            if not self.default_fallbacks:
                # Translation-only checkouts commonly retain an English LANGUAGE
                # declaration while shipping only Russian TRA files. Verify the
                # files rather than processing thousands of nonexistent IDs.
                english_files = [p for p in self.tp2.parent.rglob('*')
                                 if p.suffix.casefold() == '.tra' and any(
                                     part.casefold() in {self.language.casefold(), 'english', 'en_us'}
                                     for part in p.parts)]
                if not english_files:
                    self.skip_reason = 'selected_language_files_absent'
                    self.source_data_issues.append('Declared source language has no TRA files in this checkout')
        elif not declarations and not any(t.kind == 'string' and '.tra' in t.value.casefold()
                                           for t in tokens):
            self.skip_reason = 'not_a_localized_installer'
        for i, token in enumerate(tokens[:-1]):
            if token.kind == 'word' and token.value.upper() == 'AUTO_TRA':
                self.auto_tra.append(tokens[i + 1].value)

    def read_constants(self, tokens):
        ignored = {i for start, _, end in definition_ranges(tokens)
                   for i in range(start, end + 1)}
        for i, token in enumerate(tokens[:-2]):
            if i in ignored:
                continue
            if token.kind == 'word' and token.value.upper() in {'OUTER_SPRINT', 'OUTER_TEXT_SPRINT'}:
                name, value = tokens[i + 1:i + 3]
                if value.value.upper() in {'EVAL', 'EVALUATE_BUFFER'} and i + 3 < len(tokens):
                    value = tokens[i + 3]
                if value.kind == 'string' or (value.kind == 'word' and
                                             re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value.value)):
                    key = name.value.casefold()
                    expanded = self.expand(value.value)
                    old = self.variables.get(key)
                    if old is not None and old != expanded:
                        self.ambiguous_variables.add(key)
                    else:
                        self.variables[key] = expanded

    def resolve_paths(self, values, source, command):
        paths = []
        for value in values:
            found = [p for p in self.paths(value, source) if p.is_file() or p in self.virtual_files]
            if re.search(r'%[^%]+%', self.expand(value)) and command in self.INCLUDE_COMMANDS:
                found = [p for p in found if p.suffix.casefold() in {
                    '.tp2', '.tpa', '.tph', '.tpc', '.tpp', '.tpe', '.d', '.baf'} or p in self.virtual_files]
            if found:
                paths.extend(found)
                if len(found) > 1 and '%' in self.expand(value):
                    self.optional_tables.update(p for p in found if p.suffix.casefold() == '.tra')
            else:
                message = f'{source}: unresolved {command} path {value!r}'
                if command in {'LANGUAGE', 'LOAD_TRA', 'USING', 'WITH_TRA'}:
                    # WeiDU's handle_tra_filename explicitly skips absent TRA
                    # files. Only a reference missing from every loaded source
                    # is an error; an absent optional override is not one.
                    self.notes.append(message + ' (WeiDU skips absent TRA files)')
                else:
                    self.warn(message)
        return paths

    def matching_table(self, source):
        if source in self._matching_tables:
            return self._matching_tables[source]
        filename = source.stem + '.tra'
        if self.tra_folder:
            found = case_path(self.tra_folder / filename)
            self._matching_tables[source] = found
            return found
        # Prefer the selected language's directory over unrelated TRA folders.
        directories = list(dict.fromkeys(p.parent for p in self.default_fallbacks))
        for pattern in self.auto_tra:
            directory = self.path(pattern, self.tp2)
            if directory and directory.is_dir() and directory not in directories:
                directories.insert(0, directory)
        for directory in directories:
            found = case_path(directory / filename)
            if found is None:
                for original in reversed(self._alias_names.get(filename.casefold(), [])):
                    if original.parent == directory:
                        found = original
                        break
            if found:
                self._matching_tables[source] = found
                return found
        self._matching_tables[source] = None
        return None

    def resolve(self, source, number, fallbacks=None):
        if self.skip_reason == 'invalid_language_declaration':
            raise ValueError('; '.join(self.source_data_issues))
        candidates = self.resolve_candidates(source, number, fallbacks)
        leaves = []
        for path, entry in candidates:
            leaves.extend(self.follow_alias(path, entry, source, fallbacks))
        candidates = leaves
        first_path, first_entry = candidates[0]
        signature = lambda entry: (tuple(v.text for v in entry.variants), entry.reference)
        if any(signature(entry) != signature(first_entry) for _, entry in candidates[1:]):
            raise ValueError(f'{source}: @{number} has conflicting fallback definitions: '
                             + ', '.join(str(path) for path, _ in candidates))
        return first_path, first_entry

    def follow_alias(self, path, entry, source, fallbacks, seen=frozenset()):
        key = (path, entry.number)
        if key in seen:
            raise ValueError(f'TRA alias cycle: {path}:@{entry.number}')
        if entry.reference and re.fullmatch(r'@-?\d+', entry.reference):
            target = int(entry.reference[1:])
            if target in self.table(path):
                candidates = [(path, self.table(path)[target])]
            else:
                candidates = self.resolve_candidates(source, target, fallbacks)
            return [leaf for candidate, value in candidates
                    for leaf in self.follow_alias(candidate, value, source, fallbacks, seen | {key})]
        return [(path, entry)]

    def resolve_candidates(self, source, number, fallbacks=None):
        """Cover every feasible source binding; ordinary matching TRA wins first.

        A conditional LOAD_TRA does not invalidate unrelated matching-file IDs.
        For shared fallbacks, protect all possible bindings during usage analysis;
        actual dialogue extraction still requires one unambiguous source value.
        """
        source = Path(source)
        if source not in self._source_paths:
            self._source_paths[source] = source.resolve()
        source = self._source_paths[source]
        corresponding = self.matching_table(source) if source.suffix.lower() in {'.d', '.baf'} else None
        if corresponding and number in self.table(corresponding):
            return [(corresponding, self.table(corresponding)[number])]
        contexts = [fallbacks] if fallbacks is not None else self.source_contexts.get(source)
        if not contexts:
            contexts = [self.source_fallbacks.get(source, self.default_fallbacks)]
        result = {}
        for context in contexts:
            for path in reversed(context):
                table = self.table(path)
                if number in table:
                    result[path] = table[number]
                    if path not in self.optional_tables or path in self.default_fallbacks:
                        break
        if result:
            return list(result.items())
        raise ValueError(f'{source}: @{number} missing from corresponding TRA and declared fallbacks')

    def record(self, source, token, kind, fallbacks, journal=False, context=None):
        number = int(token.value[1:])
        try:
            candidates = self.resolve_candidates(source, number, fallbacks)
        except ValueError as exc:
            if kind == 'installer':
                self.notes.append(f'{source}:{token.line}: unresolved installer-only {token.value}; '
                                  'no game translation input depends on it')
                return
            self.unresolved_occurrences += 1
            key = ('tra_parse_error', str(exc)) if str(exc) in self.table_errors.values() else (source, number)
            if key not in self._unresolved_keys:
                self.unresolved.append(f'{source}:{token.line}: {exc}')
                self._unresolved_keys.add(key)
            self.complete = False
            return
        for path, _ in candidates:
            key = (path, number)
            self.usage[key].add(kind)
            if journal:
                self.journal_entries.add(key)
            self.locations[key].append(f'{source}:{token.line} ({kind})')
        for path, entry in candidates:
            for actual_path, actual_entry in self.follow_alias(path, entry, source, fallbacks):
                self.usage[(actual_path, actual_entry.number)].add(kind)
                if journal:
                    self.journal_entries.add((actual_path, actual_entry.number))
                detail = dict(context or {})
                detail.update(source=str(source), line=token.line, kind=kind)
                detail['resources'] = [self.expand(value) for value in detail.get('resources', [])]
                if detail not in self.consumers[(actual_path, actual_entry.number)]:
                    self.consumers[(actual_path, actual_entry.number)].append(detail)

    @staticmethod
    def reference_contexts(tokens, ignored=(), initial_resources=()):
        """Keep the explicit COPY/SAY relationship; unresolved helper inputs stay unclassified."""
        contexts = {}
        resources = list(initial_resources)
        for i, token in enumerate(tokens):
            if i in ignored or token.kind != 'word':
                continue
            command = token.value.upper()
            if command in FUNCTION_CALLS | MACRO_CALLS | {
                    'INCLUDE', 'REINCLUDE', 'PATCH_INCLUDE', 'PATCH_REINCLUDE', 'LOAD',
                    'WITH_TRA', 'ACTION_PHP_EACH', 'PHP_EACH', 'PATCH_PHP_EACH',
                    'OUTER_WHILE', 'ACTION_FOR_EACH', 'PATCH_FOR_EACH', 'ACTION_MATCH', 'PATCH_MATCH'}:
                contexts[i] = {'resources': list(resources)}
            if command in {'COPY', 'COPY_EXISTING', 'COPY_EXISTING_REGEXP', 'COPY_EXISTING_GLOB'}:
                start = i + 1
                while start < len(tokens) and tokens[start].value in {'+', '-', 'GLOB'}:
                    start += 1
                values = [t.value for t in tokens[start:start + 2]]
                extra, _ = strings_after(tokens, start + 2)
                resources = (values + extra)[::2]
            elif command in {'SAY', 'SAY_EVALUATED'} and i + 2 < len(tokens):
                if tokens[i + 2].kind == 'ref':
                    contexts[i + 2] = {'command': command, 'slot': tokens[i + 1].value,
                                       'resources': list(resources)}
            elif command in {'STRING_SET', 'STRING_SET_EVALUATE'}:
                for j in range(i + 1, min(i + 5, len(tokens))):
                    if tokens[j].kind == 'ref':
                        contexts[j] = {'command': command, 'slot': '', 'resources': []}
                        break
            elif command in {'FJ_INFO_POINT_STRREF', 'FJ_NAME_STRREF', 'FJ_TOOLTIP'}:
                for j in range(i + 1, min(i + 7, len(tokens))):
                    if tokens[j].kind == 'ref':
                        contexts[j] = {'command': 'RESOLVE_STR_REF', 'slot': command,
                                       'resources': list(resources)}
                        break
        return contexts

    def embedded_actions(self, source):
        """D DO strings contain BAF actions, not ordinary dialogue prose."""
        tokens = self.tokens(source)
        for i, token in enumerate(tokens[:-1]):
            if token.kind == 'word' and token.value.upper() == 'DO' and tokens[i + 1].kind == 'string':
                value = tokens[i + 1]
                actions = [Token(t.kind, t.value, t.line + value.line - 1) for t in tokenize(value.value)]
                yield value.line, actions

    @staticmethod
    def journal_refs(tokens):
        """Identify journal text by its consumer, without guessing from prose."""
        indices = set()
        for i, token in enumerate(tokens):
            if token.kind != 'word':
                continue
            command = token.value.upper()
            if command in {'ADDJOURNALENTRY', 'ERASEJOURNALENTRY'} and i + 1 < len(tokens):
                if tokens[i + 1].value != '(':
                    continue
                depth = 0
                for j in range(i + 1, len(tokens)):
                    if tokens[j].kind == 'word':
                        depth += (tokens[j].value == '(') - (tokens[j].value == ')')
                    if tokens[j].kind == 'ref':
                        indices.add(j)
                    if depth == 0:
                        break
            elif command in {'JOURNAL', 'SOLVED_JOURNAL', 'UNSOLVED_JOURNAL'}:
                if i + 1 < len(tokens) and tokens[i + 1].kind == 'ref':
                    indices.add(i + 1)
            elif command == 'ADD_JOURNAL':
                for j in range(i + 1, len(tokens)):
                    following = tokens[j]
                    if following.kind == 'ref':
                        indices.add(j)
                    elif following.kind == 'word' and following.value.upper() not in {'TITLE', '(', ')', ','}:
                        break
                    elif following.kind == 'string':
                        break
        return indices

    def installer_refs(self, tokens):
        indices = set()
        for i, token in enumerate(tokens[:-1]):
            if token.kind != 'word':
                continue
            command = token.value.upper()
            if command in self.INSTALLER_COMMANDS and tokens[i + 1].kind == 'ref':
                indices.add(i + 1)
            elif command in {'REQUIRE_PREDICATE', 'REQUIRE_COMPONENT', 'FORBID_COMPONENT'}:
                # A single @ID at the end of this physical statement is the
                # diagnostic. Multiline/compound expressions remain uncertain.
                tail = []
                j = i + 1
                while j < len(tokens) and tokens[j].line == token.line:
                    tail.append(j)
                    j += 1
                refs = [j for j in tail if tokens[j].kind == 'ref']
                if len(refs) == 1 and tail[-1] == refs[0]:
                    indices.add(refs[0])
        return indices

    def using_refs(self, tokens):
        """USING is statement-local for journals/TLK patches as well as COMPILE."""
        result = {}
        statements = {'ADD_JOURNAL', 'STRING_SET', 'STRING_SET_EVALUATE',
                      'SAY', 'SAY_EVALUATED', 'SPRINT', 'OUTER_SPRINT',
                      'REPLACE_TEXTUALLY', 'COMPILE', 'EXTEND_TOP', 'EXTEND_BOTTOM',
                      'PRINT', 'FAIL', 'END', 'BEGIN', 'COPY', 'COPY_EXISTING'}
        start = None
        for i, token in enumerate(tokens):
            if token.kind != 'word':
                continue
            command = token.value.upper()
            if command in statements:
                start = i
            elif command == 'USING' and start is not None:
                values, _ = strings_after(tokens, i + 1)
                for j in range(start, i):
                    if tokens[j].kind == 'ref':
                        result[j] = values
        return result

    def compile_sources(self, values, source, fallbacks, if_exists=False):
        fallbacks = self.fallback_stack(fallbacks)
        unit = (str(source), tuple(self.expand(value) for value in values), tuple(map(str, fallbacks)))
        for value in values:
            found_paths = self.paths(value, source)
            if not found_paths:
                message = f'{source}: unresolved compile input {value!r}'
                if if_exists:
                    self.notes.append(message + ' (IF_EXISTS)')
                else:
                    self.warn(message)
                continue
            files = []
            for found in found_paths:
                if found in self.virtual_directories:
                    files.extend(p for p in self.virtual_files if found in p.parents)
                files.extend(sorted(found.rglob('*')) if found.is_dir() else [found])
            for path in files:
                if path.suffix.casefold() not in {'.d', '.baf'}:
                    continue
                path = path.resolve()
                self.compilation_units[path].add(unit)
                if path.suffix.casefold() == '.baf':
                    # Later EXTEND_* can read a script compiled earlier in the
                    # same installer. Its @IDs have already become TLK refs;
                    # source text is accounted for below, not re-resolved there.
                    self.put_virtual(self.tp2.parent / 'override' / (path.stem + '.bcs'), '')
                old = self.source_fallbacks.get(path)
                if old is not None and old != fallbacks:
                    self.notes.append(f'{path}: compiled in multiple TRA contexts')
                self.source_fallbacks[path] = list(fallbacks)
                if tuple(fallbacks) not in self.source_contexts[path]:
                    self.source_contexts[path].append(tuple(fallbacks))
                if self.uncertain_routing:
                    self.ambiguous_files.add(path)

    def condition(self, tokens, source):
        """Evaluate only known string/parameter tests, never game patch code."""
        tokens = list(tokens)
        while tokens and tokens[0].value == '(' and tokens[-1].value == ')':
            depth = 0
            for j, token in enumerate(tokens):
                depth += (token.value == '(') - (token.value == ')')
                if depth == 0:
                    break
            if j != len(tokens) - 1:
                break
            tokens = tokens[1:-1]
        for operators in ({'OR', '||'}, {'AND', '&&'}):
            depth = 0
            for j, token in enumerate(tokens):
                depth += (token.value == '(') - (token.value == ')')
                if depth == 0 and token.kind == 'word' and token.value.upper() in operators:
                    left = self.condition(tokens[:j], source)
                    right = self.condition(tokens[j + 1:], source)
                    if 'OR' in operators:
                        return True if True in (left, right) else (False if left is right is False else None)
                    return False if False in (left, right) else (True if left is right is True else None)
        values = [token for token in tokens if token.value.upper() not in {'(', ')', 'THEN'}]
        negate = False
        while values and values[0].value.upper() in {'!', 'NOT'}:
            negate = not negate
            values = values[1:]
        decision = None
        dependencies = {name.casefold() for token in values
                        for name in re.findall(r'%([^%]+)%', token.value)}
        dependencies.update(token.value.casefold() for token in values if token.kind == 'word')
        filesystem_test = len(values) == 2 and values[0].value.upper() in {'FILE_EXISTS', 'DIRECTORY_EXISTS'}
        if dependencies.intersection(self.unknown_variables) and not filesystem_test:
            return None
        if len(values) == 2 and values[0].value.upper() == 'VARIABLE_IS_SET':
            decision = values[1].value.casefold() in self.variables
        elif len(values) == 2 and values[0].value.upper() == 'IS_AN_INT':
            name = self.expand(values[1].value)
            candidate = self.variables.get(name.casefold(), name)
            if '%' not in candidate:
                decision = bool(re.fullmatch(r'-?(?:\d+|0[xX][0-9a-fA-F]+)', candidate))
        elif len(values) == 5 and values[0].value.upper() in {'INDEX', 'RINDEX'}:
            pattern, text = self.expand(values[1].value), self.expand(values[2].value)
            if '%' not in pattern + text:
                try:
                    matches = list(re.finditer(pattern, text))
                    offset = matches[-1 if values[0].value.upper() == 'RINDEX' else 0].start() if matches else -1
                    decision = self.condition([Token('word', str(offset), values[0].line)] + values[3:], source)
                except re.error:
                    pass
        elif len(values) == 2 and values[0].value.upper() in {'FILE_EXISTS', 'DIRECTORY_EXISTS'}:
            name = self.expand(values[1].value)
            first = name.replace('\\', '/').split('/')[0].casefold()
            # Source/dependency files can be tested. Game resources outside this
            # checkout (override/data/chitin.key) cannot be assumed absent.
            if first in self.mod_prefixes or first in {'bgt', 'eet'} or name.startswith('.../'):
                found = self.paths(name, source)
                decision = bool(found)
                if decision and values[0].value.upper() == 'DIRECTORY_EXISTS':
                    decision = any(p.is_dir() for p in found)
        elif len(values) == 1 and values[0].value.casefold() in self.variables:
            value = self.variables[values[0].value.casefold()]
            if value.isdigit():
                decision = bool(int(value))
        elif len(values) == 3:
            left, operator, right = values
            first, second = self.expand(left.value), self.expand(right.value)
            if '%' not in first + second:
                op = operator.value.upper()
                if op.endswith('_CASE'):
                    first, second = first.casefold(), second.casefold()
                if op in {'STRING_EQUAL', 'STRING_EQUAL_CASE', 'STR_EQ', 'STR_EQ_CASE'}:
                    decision = first == second
                elif op in {'STRING_COMPARE', 'STRING_COMPARE_CASE', 'STR_CMP', 'STR_CMP_CASE'}:
                    decision = first != second
                elif op in {'=', '==', '!=', '>', '<', '>=', '<='}:
                    first = self.variables.get(first.casefold(), first)
                    second = self.variables.get(second.casefold(), second)
                    if re.fullmatch(r'-?\d+', first) and re.fullmatch(r'-?\d+', second):
                        a, b = int(first), int(second)
                        decision = {'=': a == b, '==': a == b, '!=': a != b,
                                    '>': a > b, '<': a < b, '>=': a >= b, '<=': a <= b}[op]
        if decision is not None and negate:
            decision = not decision
        return decision

    def scan_script(self, path, fallbacks, stack=(), conditional=False, fragment=None, resource_context=()):
        path = path.resolve()
        fallbacks = self.fallback_stack(fallbacks)
        if fragment is None and path.suffix.casefold() in {'.d', '.baf'}:
            self.compile_sources([str(path)], path, fallbacks)
            return fallbacks
        if fragment is not None:
            for name, text in self.inline_templates[path]:
                self.put_virtual(self.tp2.parent / self.expand(name), text)
        if fragment is None and path in stack:
            context = (path, tuple(fallbacks))
            if context not in self._path_contexts:
                self._pending_contexts.append((path, list(fallbacks), self.variables.copy()))
            self.notes.append(f'Closed include graph revisit: {path}')
            return fallbacks
        if fragment is None:
            self._path_contexts.add((path, tuple(fallbacks)))
        # REINCLUDE may execute again with a different translation environment.
        fragment_key = None
        if fragment is not None:
            names = {name.casefold() for token in fragment
                     for name in re.findall(r'%([^%]+)%', token.value)}
            names.update(token.value.casefold() for token in fragment
                         if token.kind == 'word' and token.value.casefold() in self.variables)
            fragment_key = (fragment[0].line if fragment else 0,
                            fragment[-1].line if fragment else 0, len(fragment),
                            tuple((name, self.variables.get(name)) for name in sorted(names)))
        identity = (path, tuple(fallbacks), conditional, fragment_key,
                    hash(self.virtual_files[path]) if path in self.virtual_files else None, tuple(resource_context))
        if identity in self.visited:
            return self.include_results.get(identity, fallbacks)
        self.visited.add(identity)
        self.sources.add(path)
        tokens = self.tokens(path) if fragment is None else fragment
        ignored = set()
        try:
            ranges = definition_ranges(tokens)
        except ValueError as exc:
            raise ValueError(f'{path}: {exc}') from exc
        for start, opening, closing in ranges:
            name = tokens[start + 1].value.casefold()
            kinds = ('action', 'patch') if tokens[start].value.upper() == 'DEFINE_DIMORPHIC_FUNCTION' else (
                'patch' if '_PATCH_' in tokens[start].value.upper() else 'action',)
            for kind in kinds:
                self.definitions[(name, kind)] = (path, tokens[start + 2:opening], tokens[opening + 1:closing])
            ignored.update(range(start, closing + 1))
        installer = self.installer_refs(tokens)
        journals = self.journal_refs(tokens)
        reference_contexts = self.reference_contexts(tokens, ignored, resource_context)
        using = self.using_refs(tokens)
        active = list(fallbacks)
        block_depth = 0
        unknown_ranges = set()
        for i, token in enumerate(tokens):
            if i in ignored:
                continue
            if token.kind == 'ref':
                local = self.resolve_paths(using[i], path, 'USING') if i in using else []
                self.record(path, token, 'installer' if i in installer else 'unknown', active + local,
                            journal=i in journals, context=reference_contexts.get(i))
            elif token.kind == 'string':
                # Code strings are not resolved at their declaration site.
                # Their actual compiler may select a different TRA via USING.
                for match in re.finditer(r'@-?\d+', token.value):
                    self.deferred_numbers.add(int(match[0][1:]))
            elif token.kind == 'word':
                command = token.value.upper()
                caller_resources = [self.expand(value) for value in reference_contexts.get(i, {}).get('resources', resource_context)]
                if command == 'WITH_TRA':
                    names, opening = strings_after(tokens, i + 1)
                    if opening < len(tokens) and tokens[opening].value.upper() == 'BEGIN':
                        closing = block_end(tokens, opening)
                        extra = self.resolve_paths(names, path, 'WITH_TRA')
                        self.scan_script(path, active + extra, stack, conditional,
                                         tokens[opening + 1:closing], caller_resources)
                        ignored.update(range(opening, closing + 1))
                elif command in {'ACTION_DEFINE_ARRAY', 'DEFINE_ARRAY'} and i + 2 < len(tokens):
                    opening = i + 2
                    if tokens[opening].value.upper() == 'BEGIN':
                        closing = block_end(tokens, opening)
                        self.arrays[tokens[i + 1].value.casefold()] = [
                            t.value for t in tokens[opening + 1:closing]]
                        ignored.update(range(i + 1, closing + 1))
                elif command in {'ACTION_DEFINE_ASSOCIATIVE_ARRAY', 'DEFINE_ASSOCIATIVE_ARRAY'} and i + 2 < len(tokens):
                    opening = i + 2
                    if tokens[opening].value.upper() == 'BEGIN':
                        closing = block_end(tokens, opening)
                        values = tokens[opening + 1:closing]
                        if len(values) % 3 == 0 and all(values[j + 1].value == '=>'
                                                       for j in range(0, len(values), 3)):
                            self.arrays[tokens[i + 1].value.casefold()] = {
                                self.expand(values[j].value): self.expand(values[j + 2].value)
                                for j in range(0, len(values), 3)}
                        ignored.update(range(i + 1, closing + 1))
                elif command in {'ACTION_PHP_EACH', 'PHP_EACH', 'PATCH_PHP_EACH'} and i + 6 < len(tokens):
                    if tokens[i + 2].value.upper() == 'AS' and tokens[i + 4].value == '=>':
                        keys = [tokens[i + 3].value.casefold(), tokens[i + 5].value.casefold()]
                        entries = self.arrays.get(tokens[i + 1].value.casefold())
                        opening = i + 6
                        if isinstance(entries, dict) and tokens[opening].value.upper() == 'BEGIN':
                            closing = block_end(tokens, opening)
                            for key, value in entries.items():
                                self.variables.update(zip(keys, (key, value)))
                                active = self.scan_script(path, active, stack, conditional,
                                                          tokens[opening + 1:closing], caller_resources)
                            ignored.update(range(i + 1, closing + 1))
                        else:
                            for key in keys:
                                self.variables[key] = '%' + key + '%'
                                self.unknown_variables.add(key)
                elif command == 'OUTER_WHILE':
                    opening = next((j for j in range(i + 1, len(tokens))
                                    if tokens[j].kind == 'word' and tokens[j].value.upper() == 'BEGIN'), None)
                    if opening is not None:
                        expression = tokens[i + 1:opening]
                        # Only drain known string lists; arbitrary patch loops
                        # remain an overapproximation of one possible body.
                        if any(t.value.upper() in {'STR_CMP', 'STRING_COMPARE', 'STRING_COMPARE_CASE'}
                               for t in expression) and self.condition(expression, path) is not None:
                            closing = block_end(tokens, opening)
                            seen = set()
                            while self.condition(expression, path) is True:
                                state = tuple(self.expand(self.variables.get(t.value.casefold(), t.value))
                                              for t in expression)
                                if state in seen or len(seen) >= 256:
                                    self.warn(f'{path}:{token.line}: string-list loop did not converge')
                                    break
                                seen.add(state)
                                active = self.scan_script(path, active, stack, conditional,
                                                          tokens[opening + 1:closing], caller_resources)
                            ignored.update(range(opening, closing + 1))
                elif command in {'ACTION_FOR_EACH', 'PATCH_FOR_EACH'} and i + 3 < len(tokens):
                    if tokens[i + 2].value.upper() == 'IN':
                        opening = next((j for j in range(i + 3, len(tokens))
                                        if tokens[j].kind == 'word' and tokens[j].value.upper() == 'BEGIN'), None)
                        if opening is not None:
                            values = [self.expand(t.value) for t in tokens[i + 3:opening]]
                            if all('%' not in value for value in values) and len(values) <= 256:
                                closing = block_end(tokens, opening)
                                name = tokens[i + 1].value.casefold()
                                for value in values:
                                    self.variables[name] = value
                                    active = self.scan_script(path, active, stack, conditional,
                                                              tokens[opening + 1:closing], caller_resources)
                                ignored.update(range(i + 1, closing + 1))
                elif command in {'ACTION_MATCH', 'PATCH_MATCH'} and i + 2 < len(tokens):
                    value = self.expand(tokens[i + 1].value)
                    if '%' not in value and tokens[i + 2].value.upper() == 'WITH':
                        closing = block_end(tokens, i + 2)
                        cursor = i + 3
                        branches = []
                        supported = True
                        default = []
                        while cursor < closing:
                            if tokens[cursor].value.upper() == 'DEFAULT':
                                default = tokens[cursor + 1:closing]
                                break
                            opening = next((j for j in range(cursor, closing)
                                            if tokens[j].kind == 'word' and tokens[j].value.upper() == 'BEGIN'), None)
                            if opening is None:
                                supported = False
                                break
                            labels = [self.expand(t.value) for t in tokens[cursor:opening]]
                            if any(not re.fullmatch(r'[\w.-]*', label) for label in labels):
                                supported = False
                                break
                            end = block_end(tokens, opening)
                            branches.append((labels, tokens[opening + 1:end]))
                            cursor = end + 1
                        if supported:
                            body = next((body for labels, body in branches if value in labels), default)
                            active = self.scan_script(path, active, stack, conditional, body, caller_resources)
                            ignored.update(range(i + 1, closing + 1))
                elif command in {'ACTION_IF', 'PATCH_IF'}:
                    opening = next((j for j in range(i + 1, len(tokens))
                                    if tokens[j].kind == 'word' and tokens[j].value.upper() == 'BEGIN'), None)
                    if opening is not None and opening + 1 < len(tokens) and tokens[opening + 1].kind in {'ref', 'string'}:
                        # A single-statement IF need not have BEGIN/END. Do not
                        # mistake a later component's BEGIN @label for its body.
                        opening = None
                    if opening is not None:
                        decision = self.condition(tokens[i + 1:opening], path)
                        closing = block_end(tokens, opening)
                        if decision is False:
                            ignored.update(range(opening, closing + 1))
                        elif decision is True:
                            after = closing + 1
                            while after < len(tokens) and tokens[after].value.upper() == 'ELSE':
                                other = next((j for j in range(after + 1, len(tokens))
                                              if tokens[j].kind == 'word' and tokens[j].value.upper() == 'BEGIN'), None)
                                if (other is None or (other + 1 < len(tokens) and
                                                      tokens[other + 1].kind in {'ref', 'string'})):
                                    break
                                end = block_end(tokens, other)
                                ignored.update(range(after, end + 1))
                                after = end + 1
                        else:
                            unknown_ranges.update(range(opening, closing + 1))
                            after = closing + 1
                            if after < len(tokens) and tokens[after].value.upper() == 'ELSE':
                                other = next((j for j in range(after + 1, len(tokens))
                                              if tokens[j].kind == 'word' and tokens[j].value.upper() == 'BEGIN'), None)
                                if (other is not None and (other + 1 == len(tokens) or
                                                          tokens[other + 1].kind not in {'ref', 'string'})):
                                    unknown_ranges.update(range(after, block_end(tokens, other) + 1))
                elif command == 'REQUIRE_PREDICATE' and i + 1 < len(tokens) and tokens[i + 1].value == '(':
                    depth = 0
                    closing = None
                    for j in range(i + 1, len(tokens)):
                        depth += (tokens[j].value == '(') - (tokens[j].value == ')')
                        if depth == 0:
                            closing = j
                            break
                    if closing is not None and self.condition(tokens[i + 1:closing + 1], path) is False:
                        following = next((j for j in range(closing + 1, len(tokens) - 1)
                                          if tokens[j].kind == 'word' and tokens[j].value.upper() == 'BEGIN'
                                          and tokens[j + 1].kind in {'ref', 'string'}), len(tokens))
                        ignored.update(range(closing + 1, following))
                        self.notes.append(f'{path}:{token.line}: component skipped: source-file prerequisite is false')
                elif command in {'OUTER_SPRINT', 'OUTER_TEXT_SPRINT', 'SPRINT', 'TEXT_SPRINT', 'LOCAL_SPRINT'}:
                    if i + 2 < len(tokens):
                        ignored.add(i + 1)
                        name, value = tokens[i + 1:i + 3]
                        if value.value.upper() in {'EVAL', 'EVALUATE_BUFFER'} and i + 3 < len(tokens):
                            value = tokens[i + 3]
                        if value.kind == 'string' or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value.value):
                            previous_value = self.variables.get(name.value.casefold())
                            self.variables[name.value.casefold()] = self.expand(value.value)
                            if i in unknown_ranges:
                                self.unknown_variables.add(name.value.casefold())
                                if previous_value is not None:
                                    self.variable_domains[name.value.casefold()].add(previous_value)
                                self.variable_domains[name.value.casefold()].add(self.variables[name.value.casefold()])
                            self._paths.clear()
                elif command == 'OUTER_SET' and i + 3 < len(tokens):
                    ignored.add(i + 1)
                    name, equals, value = tokens[i + 1:i + 4]
                    if equals.value == '=' and value.value.isdigit():
                        previous_value = self.variables.get(name.value.casefold())
                        self.variables[name.value.casefold()] = value.value
                        if i in unknown_ranges:
                            self.unknown_variables.add(name.value.casefold())
                            if previous_value is not None:
                                self.variable_domains[name.value.casefold()].add(previous_value)
                            self.variable_domains[name.value.casefold()].add(value.value)
                    elif equals.value == '=':
                        expression = []
                        j = i + 3
                        while j < len(tokens) and tokens[j].line == token.line:
                            expression.append(tokens[j])
                            j += 1
                        evaluated = self.condition(expression, path)
                        if evaluated is not None:
                            self.variables[name.value.casefold()] = str(int(evaluated))
                elif command == 'AT' and i + 1 < len(tokens):
                    value = self.variables.get(tokens[i + 1].value.casefold())
                    if value is not None and re.fullmatch(r'-?\d+', value):
                        self.record(path, Token('ref', '@' + value, token.line), 'unknown', active)
                elif command in FUNCTION_CALLS | MACRO_CALLS:
                    if i + 1 < len(tokens):
                        end = block_end(tokens, i) if command in FUNCTION_CALLS else i + 2
                        # A helper named "include" or "compile" is not a
                        # second native command. Its argument names are not
                        # commands either; preserve their literal references.
                        for argument_index, argument in enumerate(tokens[i + 2:end], i + 2):
                            if argument.kind == 'ref':
                                self.record(path, argument, 'unknown', active,
                                            context=reference_contexts.get(argument_index))
                            elif argument.kind == 'string':
                                self.deferred_numbers.update(int(m[0][1:]) for m in
                                                             re.finditer(r'@-?\d+', argument.value))
                        ignored.update(range(i + 1, end + (command in FUNCTION_CALLS)))
                        name = self.expand(tokens[i + 1].value).casefold()
                        call_key = (name, 'patch' if command in {'LPF', 'LPM', 'LAUNCH_PATCH_FUNCTION',
                                                               'LAUNCH_PATCH_MACRO'} else 'action')
                        if '%' in name:
                            # A runtime-selected helper may call any definition.
                            # Protect its possible text without pretending the
                            # helper's runtime control flow has been evaluated.
                            for _, _, body in self.definitions.values():
                                self.deferred_numbers.update(int(t.value[1:]) for t in body
                                                             if t.kind == 'ref')
                            self.notes.append(f'{path}:{token.line}: runtime helper {name!r}; '
                                              'definition references retained conservatively')
                        builtin_charset = name in {'handle_charsets', 'handle_charsets_immutably', 'charset_wrapper'}
                        if builtin_charset:
                            end = block_end(tokens, i)
                            arguments = tokens[i + 2:end]
                            params = {}
                            for j in range(len(arguments) - 2):
                                if arguments[j + 1].value == '=':
                                    value = arguments[j + 2]
                                    if value.value.upper() == 'EVAL' and j + 3 < len(arguments):
                                        value = arguments[j + 3]
                                    params[arguments[j].value.casefold()] = self.expand(value.value)
                            original = self.path(params.get('tra_path', ''), path)
                            for filename in self.arrays.get(params.get('reload_array', '').casefold(), []):
                                if not filename.casefold().endswith('.tra'):
                                    filename += '.tra'
                                table = self.path(params.get('tra_path', '').rstrip('/') + '/' +
                                                  self.language + '/' + filename, path)
                                if table:
                                    active = self.fallback_stack(active + [table])
                            if name == 'charset_wrapper':
                                raw = params.get('tra_path', '')
                                original = self.path(raw, path) if raw else None
                                if not raw:
                                    original = (self.path(self.expand('%MOD_FOLDER%/lang'), path) or
                                                self.path(self.expand('%MOD_FOLDER%/tra'), path))
                                elif original is None:
                                    original = self.path(self.expand('%MOD_FOLDER%/') + raw, path)
                                if original:
                                    generated = self.expand('weidu_external/lang/%MOD_FOLDER%')
                                    self.add_copy_alias(generated, original)
                                    self.variables['out_path'] = str(original)
                                    for j in range(len(arguments) - 2):
                                        if arguments[j + 1].value == '=' and arguments[j + 2].value.casefold() == 'out_path':
                                            self.variables[arguments[j].value.casefold()] = str(original)
                                    setup = params.get('setup', '') or params.get('setup_tra', 'setup')
                                    extra = params.get('load', '').split()
                                    for filename in [setup] + extra:
                                        if not filename.casefold().endswith('.tra'):
                                            filename += '.tra'
                                        table = case_path(original / self.language / filename)
                                        if table:
                                            active.append(table)
                                    self._paths.clear()
                            if name == 'handle_charsets_immutably':
                                original = self.path(self.expand('%MOD_FOLDER%/') +
                                                     params.get('tra_base', 'lang'), path)
                                if original:
                                    self.variables['scs_tra_loc'] = str(original)
                                    for j in range(len(arguments) - 2):
                                        if arguments[j + 1].value == '=' and arguments[j + 2].value.casefold() == 'scs_tra_loc':
                                            self.variables[arguments[j].value.casefold()] = str(original)
                            if original and params.get('out_path'):
                                self.add_copy_alias(params['out_path'], original)
                                self._paths.clear()
                        if not builtin_charset and call_key in self.definitions and call_key not in self.active_calls:
                            end = block_end(tokens, i) if command in FUNCTION_CALLS else i + 2
                            function_path, signature, body = self.definitions[call_key]
                            previous = self.variables.copy()
                            previous_unknown = self.unknown_variables.copy()
                            previous_domains = {key: set(values) for key, values in self.variable_domains.items()}
                            previous_arrays = self.arrays.copy()
                            parameters = set()
                            call_args = tokens[i + 2:end]
                            mode = None
                            for j, argument in enumerate(call_args):
                                if argument.value.upper() in {'STR_VAR', 'INT_VAR', 'RET', 'RET_ARRAY'}:
                                    mode = argument.value.upper()
                                    continue
                                before = call_args[j - 1].value if j else None
                                after = call_args[j + 1].value if j + 1 < len(call_args) else None
                                if (mode in {'STR_VAR', 'INT_VAR'} and before != '=' and after != '='
                                        and argument.value.casefold() in previous):
                                    parameters.add(argument.value.casefold())
                            # Static string arguments/defaults supply include,
                            # compile and TRA paths used inside helper functions.
                            for is_default, arguments in ((False, call_args), (True, signature)):
                                mode = None
                                for j in range(len(arguments) - 2):
                                    if arguments[j].value.upper() in {'STR_VAR', 'INT_VAR', 'RET', 'RET_ARRAY'}:
                                        mode = arguments[j].value.upper()
                                    if mode in {'RET', 'RET_ARRAY'}:
                                        continue
                                    if arguments[j + 1].value == '=':
                                        if is_default and arguments[j].value.casefold() in parameters:
                                            continue
                                        value = arguments[j + 2]
                                        if value.value.upper() == 'EVAL' and j + 3 < len(arguments):
                                            value = arguments[j + 3]
                                        raw = (self.variables.get(value.value.casefold(), value.value)
                                               if mode == 'INT_VAR' else value.value)
                                        self.variables[arguments[j].value.casefold()] = self.expand(raw)
                                        parameters.add(arguments[j].value.casefold())
                                        self.unknown_variables.discard(arguments[j].value.casefold())
                            # STR_VAR input is shorthand for passing the caller's
                            # existing input variable, not the callee default.
                            call_args = tokens[i + 2:end]
                            mode = None
                            for j, argument in enumerate(call_args):
                                keyword = argument.value.upper()
                                if keyword in {'STR_VAR', 'INT_VAR', 'RET', 'RET_ARRAY'}:
                                    mode = keyword
                                    continue
                                key = argument.value.casefold()
                                if mode in {'STR_VAR', 'INT_VAR'} and key in previous:
                                    before = call_args[j - 1].value if j else None
                                    after = call_args[j + 1].value if j + 1 < len(call_args) else None
                                    if before != '=' and after != '=':
                                        self.variables[key] = previous[key]
                                        parameters.add(key)
                            self.active_calls.add(call_key)
                            # Standard SFO pure list helper. Model its string
                            # result directly; no installer or patch is run.
                            if name == 'return_first_entry' and any(t.value.casefold() == 'separator' for t in signature):
                                remaining = self.variables.get('list', '').strip()
                                separator = self.variables.get('separator', ' ')
                                if remaining[:1] in {'"', '~'}:
                                    boundary = remaining.find(remaining[0], 1)
                                    entry, rest = ((remaining[1:boundary], remaining[boundary + 1:])
                                                   if boundary >= 0 else (remaining, ''))
                                else:
                                    entry, _, rest = remaining.partition(separator or ' ')
                                self.variables.update(entry=entry.strip(), list=rest.strip())
                            else:
                                active = self.scan_script(function_path, active, stack, conditional, body, caller_resources)
                            self.active_calls.remove(call_key)
                            returned = {}
                            for j, argument in enumerate(call_args):
                                if argument.value.upper() != 'RET':
                                    continue
                                k = j + 1
                                while k < len(call_args):
                                    key = call_args[k].value.casefold()
                                    origin = key
                                    if k + 2 < len(call_args) and call_args[k + 1].value == '=':
                                        origin = call_args[k + 2].value.casefold()
                                        k += 2
                                    if origin in self.variables:
                                        returned[key] = self.variables[origin]
                                    k += 1
                            # Native WeiDU var_push/var_pop scopes every function
                            # variable, not only declared parameters. Macros use
                            # the caller's scope. Only RET escapes a function.
                            if command in FUNCTION_CALLS:
                                self.variables = previous
                                self.unknown_variables = previous_unknown
                                self.variable_domains = defaultdict(set, previous_domains)
                                self.arrays = previous_arrays
                            self.variables.update(returned)
                            self._paths.clear()
                elif command == 'MKDIR' and i + 1 < len(tokens):
                    name = self.expand(tokens[i + 1].value)
                    self.virtual_directories.add((self.tp2.parent / name).resolve())
                elif command == 'COPY':
                    start = i + 1
                    while start < len(tokens) and tokens[start].value in {'-', '+'}:
                        start += 1
                    values = [t.value for t in tokens[start:start + 2]]
                    extra, after = strings_after(tokens, start + 2)
                    values.extend(extra)
                    for pair in range(0, len(values) - 1, 2):
                        originals = self.paths(values[pair], path)
                        for original in originals:
                            target = self.expand(values[pair + 1])
                            logical = (self.tp2.parent / target).resolve()
                            if not original.is_dir() and (logical in self.virtual_directories or target.casefold() == 'override'):
                                target = target.rstrip('/') + '/' + original.name
                            self.add_copy_alias(target, original)
                            if original in self.virtual_files:
                                destination = (self.tp2.parent / target).absolute()
                                text = self.virtual_files[original]
                                if after < len(tokens) and tokens[after].value.upper() == 'EVALUATE_BUFFER':
                                    text = self.expand(text)
                                self.put_virtual(destination, text)
                            self._paths.clear()
                elif command in {'COPY_EXISTING', 'COPY_EXISTING_REGEXP', 'COPY_EXISTING_GLOB'}:
                    start = i + 1
                    while start < len(tokens) and tokens[start].value in {'-', '+'}:
                        start += 1
                    values = [t.value for t in tokens[start:start + 2]]
                    extra, _ = strings_after(tokens, start + 2)
                    values.extend(extra)
                    for pair in range(0, len(values) - 1, 2):
                        original, destination = map(self.expand, values[pair:pair + 2])
                        if Path(original).suffix.casefold() in {'.dlg', '.bcs'}:
                            if Path(destination).suffix.casefold() not in {'.d', '.baf', '.bcs', '.dlg'}:
                                destination = destination.rstrip('/') + '/' + Path(original).name
                            self.put_virtual(self.tp2.parent / destination, '')
                            self.notes.append(f'{path}:{token.line}: game resource {original} is '
                                              'an opaque source with no mod TRA IDs; patch strings are scanned separately')
                elif command == 'BEGIN' and (i + 1 == len(tokens) or
                                           tokens[i + 1].kind not in {'ref', 'string'}):
                    block_depth += 1
                elif command == 'END':
                    block_depth = max(0, block_depth - 1)
                elif command in self.INCLUDE_COMMANDS:
                    if command == 'LOAD' and (i + 1 == len(tokens) or tokens[i + 1].kind != 'string'):
                        continue  # a parameter/2DA variable named load
                    values, _ = strings_after(tokens, i + 1)
                    if not values:
                        self.warn(f'{path}:{token.line}: dynamic {command}')
                    for include in self.resolve_paths(values, path, command):
                        active = self.scan_script(include, active, stack + (path,),
                                                  conditional or bool(block_depth), resource_context=caller_resources)
                elif command == 'LOAD_TRA':
                    values, _ = strings_after(tokens, i + 1)
                    if not values:
                        self.warn(f'{path}:{token.line}: dynamic LOAD_TRA')
                    loaded = self.resolve_paths(values, path, command)
                    if block_depth or conditional:
                        self.optional_tables.update(loaded)
                    active = self.fallback_stack(active + loaded)
                elif command == 'COMPILE':
                    j = i + 1
                    if_exists = False
                    while j < len(tokens) and tokens[j].value.upper() in {'EVALUATE_BUFFER', 'EVAL', 'IF_EXISTS'}:
                        if_exists |= tokens[j].value.upper() == 'IF_EXISTS'
                        j += 1
                    values, end = strings_after(tokens, j)
                    extra = []
                    while end < len(tokens) and tokens[end].value.upper() in {'EVALUATE_BUFFER', 'EVAL', 'IF_EXISTS'}:
                        if_exists |= tokens[end].value.upper() == 'IF_EXISTS'
                        end += 1
                    if end < len(tokens) and tokens[end].value.upper() == 'USING':
                        using_files, _ = strings_after(tokens, end + 1)
                        extra = self.resolve_paths(using_files, path, 'USING')
                    if not values:
                        self.warn(f'{path}:{token.line}: dynamic COMPILE')
                    self.compile_sources(values, path, active + extra, if_exists)
                elif command in {'EXTEND_TOP', 'EXTEND_BOTTOM', 'EXTEND_TOP_REGEXP', 'EXTEND_BOTTOM_REGEXP'}:
                    values = [t.value for t in tokens[i + 1:i + 3]]
                    # First argument is the game BCS destination, second is BAF.
                    if len(values) >= 2:
                        end = i + 3
                        while end < len(tokens) and tokens[end].value.upper() in {'EVALUATE_BUFFER', 'EVAL', 'IF_EXISTS'}:
                            end += 1
                        extra = []
                        if end < len(tokens) and tokens[end].value.upper() == 'USING':
                            using_files, _ = strings_after(tokens, end + 1)
                            extra = self.resolve_paths(using_files, path, 'USING')
                        self.compile_sources(values[1:2], path, active + extra)
                    else:
                        self.warn(f'{path}:{token.line}: dynamic {command}')
                elif command in {'AT_NOW', 'AT_INTERACTIVE_NOW', 'AT_EXIT'}:
                    literal = next((t.value for t in tokens[i + 1:i + 4] if t.kind == 'string'), '')
                    action = self.expand(literal).strip()
                    safe = (re.match(r'^(?:chmod|echo|rm|rmdir|del|oggdec|sox|wavc)(?:\s|$)', action, re.I)
                            or '--biff-get' in action.casefold() or '--uninstall' in action.casefold()
                            or re.match(r'^wine\s+--help', action, re.I))
                    if safe:
                        self.notes.append(f'{path}:{token.line}: installer/asset hook {action!r}')
                    else:
                        # Native executables are outside the WeiDU source graph.
                        # Preserve every entry if their TRA usage is opaque;
                        # this is a conservative result, not a parsing failure.
                        self.opaque_external = True
                        self.notes.append(f'{path}:{token.line}: external hook {action!r}; '
                                          'all TRA entries retained conservatively')
        active = self.fallback_stack(active)
        self.include_results[identity] = list(active)
        return active

    def analyze(self):
        self.select_language()
        if self.skip_reason in {'no_selected_language', 'not_a_localized_installer',
                                'selected_language_files_absent', 'invalid_language_declaration'}:
            self.complete = False
            return self
        self.scan_script(self.tp2, self.default_fallbacks)
        while self._pending_contexts:
            path, context, variables = self._pending_contexts.pop()
            if (path, tuple(context)) in self._path_contexts:
                continue
            previous = self.variables
            self.variables = variables
            self.scan_script(path, context)
            self.variables = previous
        for source, fallbacks in sorted(self.source_fallbacks.items()):
            tokens = self.tokens(source)
            journals = self.journal_refs(tokens)
            for i, token in enumerate(tokens):
                if token.kind == 'ref':
                    self.record(source, token, 'game', None, journal=i in journals)
                elif token.kind == 'string':
                    for match in re.finditer(r'@-?\d+', token.value):
                        self.deferred_numbers.add(int(match[0][1:]))
            if source.suffix.casefold() == '.d':
                for _, actions in self.embedded_actions(source):
                    journals = self.journal_refs(actions)
                    for i, token in enumerate(actions):
                        if token.kind == 'ref':
                            self.record(source, token, 'game', None, journal=i in journals)
        for key in self.usage:
            if key[1] in self.deferred_numbers:
                self.usage[key].add('unknown')
        return self

    @property
    def excluded(self):
        # Incomplete include/routing coverage cannot prove installer-only usage.
        if not self.complete or self.opaque_external:
            return set()
        return {key for key, uses in self.usage.items()
                if uses == {'installer'} and key[1] not in self.deferred_numbers}

    def report(self):
        return {
            'tp2': str(self.tp2), 'language': self.language,
            'language_declarations': self.language_declarations,
            'skip_reason': self.skip_reason,
            'source_data_issues': self.source_data_issues,
            'opaque_external_hook': self.opaque_external,
            'notes': list(dict.fromkeys(self.notes)),
            'fallbacks': [str(p) for p in self.default_fallbacks],
            'weidu_files': len(self.sources), 'compiled_sources': len(self.source_fallbacks),
            'complete': self.complete, 'warnings': self.warnings,
            'unresolved': self.unresolved,
            'unresolved_reference_occurrences': self.unresolved_occurrences,
            'journal_entries': [{'file': str(p), 'id': n} for p, n in sorted(self.journal_entries)],
            'excluded': [{'file': str(p), 'id': n, 'locations': self.locations[(p, n)]}
                         for p, n in sorted(self.excluded)],
        }


def audit(root, output, source_language='english'):
    reports = []
    paths = sorted(path for path in Path(root).rglob('*')
                   if path.suffix.casefold() == '.tp2' and '.git' not in path.parts
                   and 'venv' not in path.parts)
    for path in paths:
        try:
            reports.append(WeiduUsage(path, source_language, source_root=root).analyze().report())
        except (OSError, ValueError, UnicodeError) as exc:
            reports.append({'tp2': str(path), 'complete': False, 'error': str(exc)})
        # Keep completed cases inspectable during long source-tree audits.
        Path(output).write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n')
        if len(reports) % 25 == 0:
            print(f'Audited {len(reports)} TP2 files...', flush=True)
    Path(output).write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n')
    complete = sum(r['complete'] for r in reports)
    helpers = sum(r.get('skip_reason') == 'not_a_localized_installer' for r in reports)
    unavailable = sum(r.get('skip_reason') in {'no_selected_language', 'selected_language_files_absent'}
                      for r in reports)
    unresolved = len(reports) - complete - helpers - unavailable
    print(f'Audited {len(reports)} TP2 files: {complete} complete, {helpers} nonlocalized helpers, '
          f'{unavailable} without selected-language inputs, {unresolved} source/runtime cases. '
          f'Report: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-root', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--source-language', default='english')
    args = parser.parse_args()
    audit(args.audit_root, args.report, args.source_language)
