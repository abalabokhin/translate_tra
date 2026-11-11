"""Link D files after parsing, preserving source identity and physical TRA provenance."""
from collections import defaultdict
from dataclasses import replace
import hashlib
from pathlib import Path
import re


class ModDialogueGraph:
    def __init__(self, listeners, root, compilation_units=None):
        self.listeners = {listener.source_path: listener for listener in listeners}
        self.root = Path(root).resolve()
        self.units = compilation_units or {}
        self.states = {}
        self.definitions = defaultdict(list)
        self.aliases = {}
        self.frontiers = []
        self._frontier_keys = set()
        self.cross_file_edges = set()
        self.prefixes = {}
        self.numeric_states = {}
        for path, listener in self.listeners.items():
            try:
                label = str(path.relative_to(self.root))
            except ValueError:
                label = str(path)
            suffix = hashlib.sha256(label.encode()).hexdigest()[:8]
            self.prefixes[path] = f'{path.stem}_{suffix}'
            for state_id, state in listener.all_states_by_id.items():
                self.states[(path, state_id)] = state
            for symbol, state_id in listener.public_states.items():
                self.definitions[symbol].append((path, state_id))
        # A complete BEGIN resource has known state indices. APPEND-only game
        # resources have an unknown base-state count and cannot be numbered here.
        creators = defaultdict(list)
        for path, listener in self.listeners.items():
            for actor in listener.created_dialogues:
                creators[actor].append(path)
        for actor, paths in creators.items():
            if len(paths) != 1:
                continue
            path = paths[0]
            listener = self.listeners[path]
            if actor in listener.unknown_numeric_layout or any(
                    other != path and state.speaker.casefold() == actor
                    and any(line.line_type == 'SAY' for line in state.lines)
                    for (other, _), state in self.states.items()):
                continue
            source_states = [state for state in listener.all_states
                             if state.speaker.casefold() == actor and any(line.line_type == 'SAY' for line in state.lines)]
            for index, state in enumerate(source_states):
                self.numeric_states[(actor, index)] = (path, state.state_id)
        # EXTEND placeholders refer to the original state's entry, not a new
        # file-local dialogue state. Join them only to an unambiguous definition.
        for (path, state_id), state in self.states.items():
            if state_id in self.listeners[path].public_states.values():
                continue
            if any(line.line_type == 'SAY' for line in state.lines):
                continue
            actor, label = state_id.split(':', 1)
            target = self.choose(path, actor, label)
            if target:
                self.aliases[(path, state_id)] = target

    def qualified(self, node):
        path, state_id = node
        return self.prefixes[path] + '::' + state_id

    def choose(self, source, actor, label):
        candidates = list(dict.fromkeys(self.definitions.get((actor.casefold(), label), [])))
        local = [node for node in candidates if node[0] == source]
        if local:
            return local[0]
        same_unit = [node for node in candidates if self.units.get(source, set()) & self.units.get(node[0], set())]
        if same_unit:
            candidates = same_unit
        elif re.fullmatch(r'-?\d+', label) and self.units.get(source):
            # Numeric references into an already-compiled DLG are state indices.
            # A numeric label in another compilation action need not have that
            # index (APPEND can start after hundreds of base-game states).
            known_index = self.numeric_states.get((actor.casefold(), int(label)))
            if known_index:
                return known_index
            candidates = [node for node in candidates if not self.units.get(node[0])]
        if len(candidates) > 1:
            files = ', '.join(str(path) for path, _ in candidates)
            raise ValueError(f'{source}: ambiguous dialogue target {actor}:{label}; definitions in {files}')
        if candidates:
            return candidates[0]
        return self.numeric_states.get((actor.casefold(), int(label))) if re.fullmatch(r'-?\d+', label) else None

    def target(self, path, state, raw):
        if raw == 'EXIT':
            return None
        listener = self.listeners[path]
        if raw in listener.all_states_by_id:
            node = path, raw
            return self.aliases.get(node, node)
        if ':' in raw:
            actor, label = raw.split(':', 1)
        else:
            actor, label = state.speaker, raw
        node = self.choose(path, actor, label)
        if node:
            return node
        key = (path, state.state_id, raw)
        if key not in self._frontier_keys:
            self._frontier_keys.add(key)
            self.frontiers.append({'source': str(path), 'state': state.state_id, 'target': raw,
                                   'reason': 'Target is not defined in the available D compilation sources'})
        return None

    def build(self):
        lines, states, by_state, origins, replies = [], {}, defaultdict(list), {}, {}
        for path, listener in self.listeners.items():
            for state_id, state in listener.all_states_by_id.items():
                node = self.aliases.get((path, state_id), (path, state_id))
                qualified = self.qualified(node)
                if qualified not in states:
                    original = self.states[node]
                    states[qualified] = replace(original, state_id=qualified, lines=[], transitions=[])
            for line in listener.all_lines:
                node = self.aliases.get((path, line.state_id), (path, line.state_id))
                copy = replace(line, line_id=self.prefixes[path] + '::' + line.line_id,
                               state_id=self.qualified(node), predecessors=[], targets=[])
                if copy.line_id in origins:
                    raise ValueError(f'{path}: duplicate dialogue line ID {line.line_id}')
                origins[copy.line_id] = path
                lines.append(copy)
                by_state[copy.state_id].append(copy)
                states[copy.state_id].lines.append(copy)
                if line.line_type == 'REPLY':
                    replies[copy.line_id] = {self.target(path, listener.all_states_by_id[line.state_id], raw)
                                            for raw in line.targets if raw != 'EXIT'}
        def connect(source, target):
            if target.line_id not in source.targets:
                source.targets.append(target.line_id)
            if source.line_id not in target.predecessors:
                target.predecessors.append(source.line_id)
            if origins[source.line_id] != origins[target.line_id]:
                self.cross_file_edges.add((source.line_id, target.line_id))

        adjacency = defaultdict(set)
        for state_id, state_lines in by_state.items():
            for reply in (line for line in state_lines if line.line_type == 'REPLY'):
                for say in (line for line in state_lines if line.line_type == 'SAY'):
                    connect(say, reply)
        for path, listener in self.listeners.items():
            for original_id, transitions in listener.state_transitions.items():
                original = listener.all_states_by_id[original_id]
                source_node = self.aliases.get((path, original_id), (path, original_id))
                source_id = self.qualified(source_node)
                automatic = {self.target(path, original, raw)
                             for raw in listener.automatic_transitions.get(original_id, []) if raw != 'EXIT'}
                for raw in transitions:
                    node = self.target(path, original, raw)
                    if node is None:
                        continue
                    target_id = self.qualified(node)
                    adjacency[source_id].add(target_id)
                    adjacency[target_id].add(source_id)
                    if target_id not in states[source_id].transitions:
                        states[source_id].transitions.append(target_id)
                    target_lines = [line for line in by_state[target_id] if line.line_type == 'SAY']
                    if not target_lines:
                        target_lines = [line for line in by_state[target_id] if line.line_type == 'REPLY']
                    for source_line in by_state[source_id]:
                        follows = (node in replies.get(source_line.line_id, set()) if source_line.line_type == 'REPLY'
                                   else node in automatic)
                        if follows:
                            for target_line in target_lines:
                                connect(source_line, target_line)
        groups, visited = [], set()
        for state_id in states:
            if state_id in visited:
                continue
            component, pending = set(), [state_id]
            while pending:
                current = pending.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                pending.extend(sorted(adjacency[current], reverse=True))
            group = [line for line in lines if line.state_id in component]
            if group:
                groups.append(group)
        report = {'source_files': len(self.listeners), 'states': len(states), 'lines': len(lines),
                  'groups': len(groups), 'cross_file_line_edges': len(self.cross_file_edges),
                  'external_targets': self.frontiers}
        return list(states.values()), lines, groups, report
