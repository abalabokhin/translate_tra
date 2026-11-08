#!/usr/bin/env python3

import argparse
import os
import chardet
import struct
from collections import defaultdict

from antlr4 import *
from DLexer import DLexer
from DParser import DParser


def detect_encoding(filepath):
    """Detect file encoding using chardet."""
    with open(filepath, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding']


def is_valid_actor_name(actor_name):
    """Check if the actor name is valid (all of them are considered valid for now)."""
    if not actor_name:
        return False
    return True


def extract_death_variable_from_cre(cre_filepath):
    """Extract death variable from CRE file binary data."""
    try:
        with open(cre_filepath, 'rb') as f:
            # Seek to the death variable field offset (0x0280 = 640)
            f.seek(0x0280)

            # Read 32 bytes for the death variable
            death_var_bytes = f.read(32)

            if len(death_var_bytes) < 32:
                return None

            # Convert to string, null-terminated
            death_variable = death_var_bytes.split(b'\x00')[0].decode('ascii', errors='ignore').strip()

            if death_variable:
                return death_variable.upper()
            return None

    except Exception as e:
        print(f"Error reading CRE file {cre_filepath}: {e}")
        return None


def extract_gender_from_cre(cre_filepath):
    """Extract gender from CRE file binary data."""
    try:
        with open(cre_filepath, 'rb') as f:
            # Seek to the gender field offset (0x0275 = 629)
            f.seek(0x0275)

            # Read 1 byte for the gender
            gender_byte = f.read(1)

            if len(gender_byte) < 1:
                return None

            gender_value = gender_byte[0]

            # Map gender values according to GENDER.IDS
            gender_map = {
                1: 'MALE',
                2: 'FEMALE',
                3: 'OTHER',
                4: 'NEITHER'
            }

            return gender_map.get(gender_value, 'UNKNOWN')

    except Exception as e:
        print(f"Error reading CRE file {cre_filepath}: {e}")
        return None


def extract_dialog_file_from_cre(cre_filepath):
    """Extract dialog file name from CRE file binary data."""
    try:
        with open(cre_filepath, 'rb') as f:
            # Seek to the dialog file field offset (0x02cc = 716)
            f.seek(0x02cc)

            # Read 8 bytes for the dialog file name
            dialog_bytes = f.read(8)

            if len(dialog_bytes) < 8:
                return None

            # Convert to string, null-terminated
            dialog_name = dialog_bytes.split(b'\x00')[0].decode('ascii', errors='ignore').strip()

            if dialog_name:
                return dialog_name.upper()
            return None

    except Exception as e:
        print(f"Error reading CRE file {cre_filepath}: {e}")
        return None


def scan_cre_files_in_folder(folder_path, actors=None, death_variables=None):
    """Compatibility wrapper for a single CRE source."""
    return scan_cre_files_in_folders([folder_path], actors, death_variables)


def scan_cre_files_in_folders(folder_paths, actors=None, death_variables=None):
    """Index CRE identities; retain gender data only for relevant resources.

    Folders are searched in order. The first resource with a given basename wins,
    case-insensitively, allowing mod resources to override base-game resources.
    Only V1.0 CRE files are supported; identities are read from their headers.
    """
    cre_to_dialog = {}
    dialog_to_cre = defaultdict(set)
    cre_to_death_var = {}
    death_var_to_cre = defaultdict(set)
    cre_to_gender = {}
    actors = None if actors is None else {a.upper() for a in actors}
    death_variables = {a.upper() for a in (death_variables or ())}
    seen = set()
    scanned = 0
    for folder_path in folder_paths:
        if not os.path.isdir(folder_path):
            raise ValueError(f'CRE folder does not exist: {folder_path}')
        for root, dirs, files in os.walk(folder_path):
            dirs.sort()
            for filename in sorted(files):
                if not filename.lower().endswith('.cre'):
                    continue
                resource = filename.upper()
                if resource in seen:
                    continue
                seen.add(resource)
                filepath = os.path.join(root, filename)
                with open(filepath, 'rb') as handle:
                    header = handle.read(0x2d4)
                scanned += 1
                if len(header) < 0x2d4 or header[:8] != b'CRE V1.0':
                    raise ValueError(f'Unsupported or truncated CRE header: {filepath}')
                def identifier(start, end):
                    return header[start:end].split(b'\0')[0].decode('ascii').strip().upper()
                dialog = identifier(0x2cc, 0x2d4)
                death_var = identifier(0x280, 0x2a0)
                if actors is not None and dialog not in actors and death_var not in death_variables:
                    continue
                cre_to_dialog[filename] = dialog or None
                cre_to_death_var[filename] = death_var or None
                cre_to_gender[filename] = {1: 'MALE', 2: 'FEMALE', 3: 'OTHER',
                                           4: 'NEITHER'}.get(header[0x275], 'UNKNOWN')
                if dialog:
                    dialog_to_cre[dialog].add(filename)
                if death_var:
                    death_var_to_cre[death_var].add(filename)
    print(f'Inspected {scanned} CRE headers; retained {len(cre_to_gender)} matching resources')
    return cre_to_dialog, dialog_to_cre, cre_to_death_var, death_var_to_cre, cre_to_gender


def read_dialogue_table(filepath, table_type):
    """Read actual game 2DA aliases, excluding dream/override script columns."""
    with open(filepath, encoding=detect_encoding(filepath)) as handle:
        lines = [line.split('//', 1)[0].strip() for line in handle]
    lines = [line for line in lines if line]
    if len(lines) < 3 or lines[0].upper().split() != ['2DA', 'V1.0']:
        raise ValueError(f'Invalid 2DA table: {filepath}')
    default = lines[1].upper()
    headers = [h.upper() for h in lines[2].split()]
    if table_type == 'PDIALOG':
        indices = [i for i, h in enumerate(headers) if h.endswith('DIALOG_FILE')]
    else:
        indices = [i for i, h in enumerate(headers) if h in ('FILE', '25FILE')]
    if not indices:
        raise ValueError(f'No dialogue columns in {filepath}')
    entries = {}
    for line in lines[3:]:
        cells = line.upper().split()
        dialogs = [cells[i + 1] for i in indices if i + 1 < len(cells)
                   and cells[i + 1] not in {default, '***', '*', 'NONE', '0'}]
        if dialogs:
            entries[cells[0]] = {'all_dialogs': list(dict.fromkeys(dialogs))}
    return entries


def parse_tp2_table_modifications(tp2_filepath):
    """Parse TP2 file and extract PDIALOG.2DA and INTERDIA.2DA modifications."""
    import re

    pdialog_entries = {}
    interdia_entries = {}

    if not os.path.exists(tp2_filepath):
        print(f"Warning: TP2 file {tp2_filepath} does not exist")
        return pdialog_entries, interdia_entries

    try:
        encoding = detect_encoding(tp2_filepath)
        with open(tp2_filepath, 'r', encoding=encoding) as file:
            content = file.read()
    except Exception as e:
        print(f"Error reading TP2 file {tp2_filepath}: {e}")
        return pdialog_entries, interdia_entries

    print(f"Parsing TP2 file: {tp2_filepath}")

    # Parse PDIALOG.2DA APPEND statements
    # Format: APPEND ~PDIALOG.2DA~ ~CHARACTER_NAME POST_DIALOG JOINED_DIALOG DREAM_DIALOG ***...~
    pdialog_pattern = r'APPEND\s+~PDIALOG\.2DA~\s+~([A-Za-z_#][A-Za-z0-9_#]*)\s+([A-Za-z_#][A-Za-z0-9_#]*)\s+([A-Za-z_#][A-Za-z0-9_#]*)\s+([A-Za-z_*#][A-Za-z0-9_*#]*)'

    for match in re.finditer(pdialog_pattern, content, re.IGNORECASE):
        character = match.group(1).upper()
        post_dialog = match.group(2).upper()
        joined_dialog = match.group(3).upper()

        dream_dialog = match.group(4).upper() if match.group(4) != '***' else None

        # Only include valid actor names
        valid_dialogs = []
        for dialog in [post_dialog, joined_dialog, dream_dialog]:
            if dialog and is_valid_actor_name(dialog):
                valid_dialogs.append(dialog)

        if valid_dialogs:
            pdialog_entries[character] = {
                'post_dialog': post_dialog if is_valid_actor_name(post_dialog) else None,
                'joined_dialog': joined_dialog if is_valid_actor_name(joined_dialog) else None,
                'dream_dialog': dream_dialog if dream_dialog and is_valid_actor_name(dream_dialog) else None,
                'all_dialogs': valid_dialogs
            }

    # Parse INTERDIA.2DA APPEND statements
    # Format: APPEND ~INTERDIA.2DA~ ~CHARACTER_NAME PARTY_DIALOG INTERRUPT_DIALOG~
    interdia_pattern = r'APPEND\s+~INTERDIA\.2DA~\s+~([A-Za-z_#][A-Za-z0-9_#]*)\s+([A-Za-z_#][A-Za-z0-9_#]*)\s+([A-Za-z_#][A-Za-z0-9_#]*)\s*~'

    for match in re.finditer(interdia_pattern, content, re.IGNORECASE):
        character = match.group(1).upper()
        party_dialog = match.group(2).upper()
        interrupt_dialog = match.group(3).upper() if match.group(3).upper() != 'NONE' else None

        # Only include valid actor names
        valid_dialogs = []
        for dialog in [party_dialog, interrupt_dialog]:
            if dialog and is_valid_actor_name(dialog):
                valid_dialogs.append(dialog)

        if valid_dialogs:
            interdia_entries[character] = {
                'party_dialog': party_dialog if is_valid_actor_name(party_dialog) else None,
                'interrupt_dialog': interrupt_dialog if interrupt_dialog and is_valid_actor_name(interrupt_dialog) else None,
                'all_dialogs': valid_dialogs
            }

    print(f"Found {len(pdialog_entries)} PDIALOG.2DA entries")
    print(f"Found {len(interdia_entries)} INTERDIA.2DA entries")

    return pdialog_entries, interdia_entries


class ActorExtractionListener(ParseTreeListener):
    """Track speaking actors separately from dialogue declarations/references."""

    def __init__(self, d_filename):
        self.d_filename = d_filename
        self.actors = set()
        self.referenced_actors = set()

    def get_speaker_from_file_rule(self, file_rule):
        """Extract speaker name from fileRule."""
        if file_rule and file_rule.stringRule():
            speaker = file_rule.stringRule().getText()
            # Clean speaker name
            if (speaker.startswith('~') and speaker.endswith('~')) or \
               (speaker.startswith('"') and speaker.endswith('"')):
                speaker = speaker[1:-1]
            return speaker.upper()
        return None

    def add_actor_if_valid(self, actor):
        """Record a dialogue identifier without assuming it has speech."""
        if actor and is_valid_actor_name(actor):
            self.referenced_actors.add(actor)

    def enterSayTextRule(self, ctx):
        """Attribute NPC text to its enclosing speaker, excluding player replies.

        The nearest dialogue owner handles SAY, REPLACE_SAY, CHAIN/CHAIN2,
        APPENDI and interjection speaker blocks. Interjection targets and EXTERN
        destinations alone do not establish that an actor has text to translate.
        """
        owner = ctx.parentCtx
        while owner is not None:
            if isinstance(owner, DParser.ReplyTransitionContext):
                return
            if getattr(owner, 'dlg', None) is not None:
                actor = self.get_speaker_from_file_rule(owner.dlg)
                self.add_actor_if_valid(actor)
                if actor and is_valid_actor_name(actor):
                    self.actors.add(actor)
                return
            owner = owner.parentCtx

    def enterBeginDAction(self, ctx: DParser.BeginDActionContext):
        """Handle BEGIN dialogueName action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterAppendDAction(self, ctx: DParser.AppendDActionContext):
        """Handle APPEND dialogueName action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterAppendEarlyDAction(self, ctx: DParser.AppendEarlyDActionContext):
        """Handle APPEND_EARLY dialogueName action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterChainDAction(self, ctx: DParser.ChainDActionContext):
        """Handle CHAIN dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterInterjectDAction(self, ctx: DParser.InterjectDActionContext):
        """Handle INTERJECT dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterInterjectCopyTransDAction(self, ctx: DParser.InterjectCopyTransDActionContext):
        """Handle INTERJECT_COPY_TRANS dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterExtendTopBottomDAction(self, ctx: DParser.ExtendTopBottomDActionContext):
        """Handle EXTEND_TOP/EXTEND_BOTTOM dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterReplaceDAction(self, ctx: DParser.ReplaceDActionContext):
        """Handle REPLACE dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterAddStateTriggerDAction(self, ctx: DParser.AddStateTriggerDActionContext):
        """Handle ADD_STATE_TRIGGER dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterAddTransTriggerDAction(self, ctx: DParser.AddTransTriggerDActionContext):
        """Handle ADD_TRANS_TRIGGER dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterAddTransActionDAction(self, ctx: DParser.AddTransActionDActionContext):
        """Handle ADD_TRANS_ACTION dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterReplaceTransActionDAction(self, ctx: DParser.ReplaceTransActionDActionContext):
        """Handle REPLACE_TRANS_ACTION dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterReplaceTransTriggerDAction(self, ctx: DParser.ReplaceTransTriggerDActionContext):
        """Handle REPLACE_TRANS_TRIGGER dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterAlterTransDAction(self, ctx: DParser.AlterTransDActionContext):
        """Handle ALTER_TRANS dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterSetWeightDAction(self, ctx: DParser.SetWeightDActionContext):
        """Handle SET_WEIGHT dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterReplaceSayDAction(self, ctx: DParser.ReplaceSayDActionContext):
        """Handle REPLACE_SAY dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterReplaceStateTriggerDAction(self, ctx: DParser.ReplaceStateTriggerDActionContext):
        """Handle REPLACE_STATE_TRIGGER dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterReplaceTriggerTextDAction(self, ctx: DParser.ReplaceTriggerTextDActionContext):
        """Handle REPLACE_TRIGGER_TEXT dialogue action."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterReplaceActionTextDAction(self, ctx: DParser.ReplaceActionTextDActionContext):
        """Handle REPLACE_ACTION_TEXT dialogue action."""
        if hasattr(ctx, 'dlgs') and ctx.dlgs:
            for dlg in ctx.dlgs:
                speaker = self.get_speaker_from_file_rule(dlg)
                self.add_actor_if_valid(speaker)

    def enterExternTransitionTarget(self, ctx: DParser.ExternTransitionTargetContext):
        """Handle EXTERN transitions."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterCopyTransTransition(self, ctx: DParser.CopyTransTransitionContext):
        """Handle COPY_TRANS transitions."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterCopyTransLateTransition(self, ctx: DParser.CopyTransLateTransitionContext):
        """Handle COPY_TRANS_LATE transitions."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterMonologChainBlock(self, ctx: DParser.MonologChainBlockContext):
        """Handle monolog chain blocks (== SPEAKER format)."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)

    def enterChain2State(self, ctx: DParser.Chain2StateContext):
        """Handle CHAIN2 statements."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)
        if ctx.exitDlg:
            speaker = self.get_speaker_from_file_rule(ctx.exitDlg)
            self.add_actor_if_valid(speaker)

    def enterAppendiState(self, ctx: DParser.AppendiStateContext):
        """Handle APPENDI statements."""
        if ctx.dlg:
            speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.add_actor_if_valid(speaker)


def extract_actors_from_d_file(d_filepath):
    """Extract actors with NPC text; ignore declarations and references alone."""
    try:
        encoding = detect_encoding(d_filepath)
        with open(d_filepath, 'r', encoding=encoding) as file:
            content = file.read()
    except Exception as e:
        print(f"Error reading {d_filepath}: {e}")
        return set()

    d_filename = os.path.basename(d_filepath)

    try:
        # Create ANTLR4 input stream
        input_stream = InputStream(content)

        # Create lexer
        lexer = DLexer(input_stream)

        # Create token stream
        stream = CommonTokenStream(lexer)

        # Create parser
        parser = DParser(stream)

        # Parse the file
        tree = parser.dFileRule()

        # Create actor extraction listener
        listener = ActorExtractionListener(d_filename)

        # Walk the parse tree
        walker = ParseTreeWalker()
        walker.walk(listener, tree)

        return listener.actors

    except Exception as e:
        print(f"Error parsing {d_filepath}: {e}")
        return set()


def process_d_files_in_folder(folder_path):
    """Process all D files in a folder and extract unique actors."""
    if not os.path.exists(folder_path):
        print(f"Error: Folder {folder_path} does not exist")
        return {}, {}

    d_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.d')]

    if not d_files:
        print(f"No D files found in {folder_path}")
        return {}, {}

    print(f"Found {len(d_files)} D files to process")

    all_actors = set()
    file_actors = defaultdict(set)

    for d_filename in sorted(d_files):
        d_filepath = os.path.join(folder_path, d_filename)
        print(f"Processing {d_filename}...")

        try:
            actors = extract_actors_from_d_file(d_filepath)
            if actors:
                file_actors[d_filename] = actors
                all_actors.update(actors)
                print(f"  Found {len(actors)} actors: {', '.join(sorted(actors))}")
            else:
                print(f"  No speaking actors found (declarations/references only)")
        except Exception as e:
            print(f"  Error processing {d_filename}: {e}")

    return all_actors, file_actors


def resolve_actor_gender(actor, all_cre_files, cre_to_gender):
    """Resolve gender for an actor based on associated CRE files."""
    if not all_cre_files:
        return "", ""  # Empty gender and no detail

    # Collect genders from all CRE files
    genders = []
    cre_gender_details = []

    for cre_file in sorted(all_cre_files):
        gender = cre_to_gender.get(cre_file)
        if gender:
            genders.append(gender)
            cre_gender_details.append(f"{cre_file}:{gender}")

    if not genders:
        return "", ""  # No gender information available

    # Check if all genders are the same
    unique_genders = set(genders)
    if len(unique_genders) == 1:
        return genders[0], ""  # Single consistent gender
    else:
        # Mixed genders - return MIXED and details
        detail = " (" + " ".join(cre_gender_details) + ")"
        return "MIXED", detail


def main():
    parser = argparse.ArgumentParser(description='''
Extract speaking actors from D files using ANTLR grammar and map them to CRE files via death variables.

This script uses the proper ANTLR4 grammar to parse D files and extract
actors with NPC text from SAY states, CHAIN/CHAIN2, interjection speaker blocks,
APPEND/APPEND_EARLY/APPENDI, REPLACE and REPLACE_SAY.
Empty declarations, reference-only targets, player replies and changes to triggers
or actions alone do not establish a speaking actor. Explicit empty SAY text still
counts as a text entry. Game 2DA and TP2 mappings resolve only these speaking actors.

It also scans CRE files to extract both dialog file references and death variables,
then parses TP2 files to map death variables to dialog files. This creates a complete
mapping between actors found in D files and their corresponding CRE files through
the TP2 table modifications (PDIALOG.2DA and INTERDIA.2DA).

The key insight is that TP2 table entries use death variables (not CRE filenames)
as the first column, so we extract death variables from CRE files and match them
to the TP2 entries to complete the actor-to-CRE mapping.
''')

    parser.add_argument('d_folder', help='Folder containing D files')
    parser.add_argument('--cre-folder', '-c', action='append', default=[],
                        help='CRE folder; repeat for additional sources. First folder wins resource conflicts.')
    parser.add_argument('--pdialog-file', action='append', default=[],
                        help='Game PDIALOG.2DA; repeat for additional tables')
    parser.add_argument('--interdia-file', action='append', default=[],
                        help='Game INTERDIA.2DA; repeat for additional tables')
    parser.add_argument('--tp2-file', '-t', help='TP2 file to parse for table modifications (optional)')
    parser.add_argument('--output', '-o', help='Output file to save enhanced actor mapping')
    parser.add_argument('--csv-output', help='CSV output file for actor-gender mapping')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed per-file actor lists')

    args = parser.parse_args()

    # Process all D files
    print("=== PROCESSING D FILES ===")
    all_actors, file_actors = process_d_files_in_folder(args.d_folder)

    if not all_actors:
        print("No valid actors found in any D files")
        return 1

    # Process TP2 file if specified
    pdialog_entries = {}
    interdia_entries = {}
    tp2_actors = set()
    for filepath in args.pdialog_file:
        pdialog_entries.update(read_dialogue_table(filepath, 'PDIALOG'))
    for filepath in args.interdia_file:
        interdia_entries.update(read_dialogue_table(filepath, 'INTERDIA'))
    if args.tp2_file:
        print(f"\n=== PROCESSING TP2 FILE ===")
        if os.path.exists(args.tp2_file):
            mod_pdialog, mod_interdia = parse_tp2_table_modifications(args.tp2_file)
            pdialog_entries.update(mod_pdialog)
            interdia_entries.update(mod_interdia)

            # Only mod-added aliases for speakers in the selected D files.
            for character, data in mod_pdialog.items():
                tp2_actors.update(data['all_dialogs'])
            for character, data in mod_interdia.items():
                tp2_actors.update(data['all_dialogs'])
            tp2_actors.intersection_update(all_actors)

            print(f"Total TP2 dynamic actors found: {len(tp2_actors)}")
        else:
            print(f"Warning: TP2 file {args.tp2_file} does not exist")

    # Tables resolve aliases; they must not introduce unrelated game actors.
    all_combined_actors = all_actors
    relevant_death_vars = {
        character
        for table in (pdialog_entries, interdia_entries)
        for character, data in table.items()
        if all_actors.intersection(data['all_dialogs'])
    }
    dialog_to_cre = defaultdict(set)
    death_var_to_cre = defaultdict(set)
    cre_to_death_var = {}
    cre_to_gender = {}
    if args.cre_folder:
        print("\n=== PROCESSING CRE FILES ===")
        (cre_to_dialog, dialog_to_cre, cre_to_death_var,
         death_var_to_cre, cre_to_gender) = scan_cre_files_in_folders(
             args.cre_folder, all_actors, relevant_death_vars)

    # Create enhanced actor mapping
    print(f"\n{'='*80}")
    print(f"ENHANCED ACTOR MAPPING (D FILES + CRE FILES + TP2 DYNAMIC)")
    print(f"{'='*80}")

    sorted_actors = sorted(all_combined_actors)
    actor_info_mapping = {}

    for actor in sorted_actors:
        # Get CRE files by dialog name (for actors found in D files)
        cre_files_by_dialog = list(dialog_to_cre.get(actor, []))

        # Find TP2 dynamic mapping info and get CRE files by death variable
        character_info = None
        dynamic_type = None
        cre_files_by_death_var = []

        matches = []
        for table_type, table in [('PDIALOG', pdialog_entries), ('INTERDIA', interdia_entries)]:
            for char, data in table.items():
                if actor in data['all_dialogs']:
                    matches.append((table_type, char))
                    cre_files_by_death_var.extend(death_var_to_cre.get(char, ()))
        if matches:
            character_info = ','.join(sorted({char for _, char in matches}))
            dynamic_type = '+'.join(sorted({kind for kind, _ in matches}))

        # Combine CRE files from both sources (remove duplicates)
        all_cre_files = list(set(cre_files_by_dialog + cre_files_by_death_var))

        actor_info_mapping[actor] = {
            'cre_files': all_cre_files,
            'cre_files_by_dialog': cre_files_by_dialog,
            'cre_files_by_death_var': cre_files_by_death_var,
            'character': character_info,
            'dynamic_type': dynamic_type,
            'source': 'D_FILE' if actor in all_actors else 'TP2_ONLY'
        }

        # Display mapping
        cre_info = f"{', '.join(sorted(all_cre_files))}" if all_cre_files else "(no CRE)"
        dialog_info = f"D:{', '.join(sorted(cre_files_by_dialog))}" if cre_files_by_dialog else ""
        death_var_info = f"DV:{', '.join(sorted(cre_files_by_death_var))}" if cre_files_by_death_var else ""
        mapping_detail = f"({dialog_info} {death_var_info})".strip()
        dynamic_info = f"[{dynamic_type}:{character_info}]" if character_info else ""
        source_info = f"({actor_info_mapping[actor]['source']})"

        print(f"{actor:<12} -> {cre_info:<25} {mapping_detail:<30} {dynamic_info:<20} {source_info}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"ENHANCED SUMMARY")
    print(f"{'='*60}")
    print(f"Total unique actors from D files: {len(all_actors)}")
    print(f"Total unique actors from TP2 dynamic: {len(tp2_actors)}")
    print(f"Total combined unique actors: {len(all_combined_actors)}")

    actors_with_cre = len([a for a in actor_info_mapping if actor_info_mapping[a]['cre_files']])
    actors_without_cre = len(all_combined_actors) - actors_with_cre
    actors_with_dynamic = len([a for a in actor_info_mapping if actor_info_mapping[a]['character']])
    actors_d_only = len([a for a in actor_info_mapping if actor_info_mapping[a]['source'] == 'D_FILE'])
    actors_tp2_only = len([a for a in actor_info_mapping if actor_info_mapping[a]['source'] == 'TP2_ONLY'])

    print(f"Actors with CRE files: {actors_with_cre}")
    print(f"Actors without CRE files: {actors_without_cre}")
    print(f"Actors with dialogue-table mapping: {actors_with_dynamic}")
    print(f"Actors from D files only: {actors_d_only}")
    print(f"Actors from TP2 only: {actors_tp2_only}")

    if args.cre_folder:
        total_cre_dialogs = len([d for d in dialog_to_cre.keys() if d])
        print(f"Total CRE files with dialog references: {total_cre_dialogs}")

    if args.tp2_file:
        print(f"PDIALOG.2DA characters: {len(pdialog_entries)}")
        print(f"INTERDIA.2DA characters: {len(interdia_entries)}")

    if args.verbose:
        print(f"\n{'='*60}")
        print("DETAILED BREAKDOWN BY D FILE")
        print(f"{'='*60}")
        for filename, actors in sorted(file_actors.items()):
            print(f"\n{filename}:")
            for actor in sorted(actors):
                info = actor_info_mapping.get(actor, {})
                cre_files = info.get('cre_files', [])
                cre_files_by_dialog = info.get('cre_files_by_dialog', [])
                cre_files_by_death_var = info.get('cre_files_by_death_var', [])
                character = info.get('character')
                dynamic_type = info.get('dynamic_type')

                cre_info = f" -> {', '.join(sorted(cre_files))}" if cre_files else " -> (no CRE)"
                dialog_detail = f" D:{', '.join(sorted(cre_files_by_dialog))}" if cre_files_by_dialog else ""
                death_var_detail = f" DV:{', '.join(sorted(cre_files_by_death_var))}" if cre_files_by_death_var else ""
                dynamic_info = f" [{dynamic_type}:{character}]" if character else ""
                print(f"  - {actor}{cre_info}{dialog_detail}{death_var_detail}{dynamic_info}")

    # Save CSV output if specified
    if args.csv_output:
        try:
            import csv

            # Read existing CSV entries if file exists
            existing_actors = set()
            if os.path.exists(args.csv_output):
                with open(args.csv_output, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0]:  # Skip empty rows
                            existing_actors.add(row[0])

            # Prepare new entries
            new_entries = []
            for actor in sorted_actors:
                if actor not in existing_actors:
                    info = actor_info_mapping[actor]
                    all_cre_files = info['cre_files']

                    # Resolve gender for this actor
                    gender, gender_detail = resolve_actor_gender(actor, all_cre_files, cre_to_gender)

                    # Format the gender column
                    gender_column = gender + gender_detail if gender_detail else gender

                    new_entries.append([actor, gender_column])

            # Write new entries to CSV file
            if new_entries:
                # Use write mode if file doesn't exist, append mode if it does
                file_mode = 'w' if not os.path.exists(args.csv_output) or not existing_actors else 'a'
                with open(args.csv_output, file_mode, encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(new_entries)
                print(f"\nAdded {len(new_entries)} new actor-gender mappings to: {args.csv_output}")
            else:
                print(f"\nNo new actors to add to CSV file: {args.csv_output}")

        except Exception as e:
            print(f"Error saving CSV to {args.csv_output}: {e}")

    # Save to output file if specified
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write("# Enhanced Actor Mapping (D Files + CRE Files + TP2 Death Variables)\n")
                f.write("# Generated from D file grammar parsing, CRE file scanning with death variables, and TP2 table modifications\n")
                f.write(f"# D files source: {args.d_folder}\n")
                if args.cre_folder:
                    f.write(f"# CRE files source: {args.cre_folder}\n")
                if args.tp2_file:
                    f.write(f"# TP2 file source: {args.tp2_file}\n")
                f.write(f"# Total D file actors: {len(all_actors)}\n")
                f.write(f"# Total TP2 dynamic actors: {len(tp2_actors)}\n")
                f.write(f"# Total combined actors: {len(all_combined_actors)}\n")
                f.write(f"# Actors with CRE files: {actors_with_cre}\n")
                f.write(f"# Actors with TP2 dynamic mapping: {actors_with_dynamic}\n")
                f.write("\n# Format: ACTOR_NAME -> CRE_FILES (D:dialog_mapping DV:death_var_mapping) [DYNAMIC_TYPE:CHARACTER] (SOURCE)\n")
                f.write("#         where D: shows CRE files found by dialog reference\n")
                f.write("#               DV: shows CRE files found by death variable from TP2\n")
                f.write("#               DYNAMIC_TYPE is PDIALOG or INTERDIA\n")
                f.write("#               SOURCE is D_FILE or TP2_ONLY\n\n")

                for actor in sorted_actors:
                    info = actor_info_mapping[actor]
                    cre_files = info['cre_files']
                    cre_files_by_dialog = info['cre_files_by_dialog']
                    cre_files_by_death_var = info['cre_files_by_death_var']
                    character = info['character']
                    dynamic_type = info['dynamic_type']
                    source = info['source']

                    cre_info = ', '.join(sorted(cre_files)) if cre_files else "(no CRE file found)"
                    dialog_detail = f"D:{', '.join(sorted(cre_files_by_dialog))}" if cre_files_by_dialog else ""
                    death_var_detail = f"DV:{', '.join(sorted(cre_files_by_death_var))}" if cre_files_by_death_var else ""
                    mapping_detail = f" ({dialog_detail} {death_var_detail})".strip() if (dialog_detail or death_var_detail) else ""
                    dynamic_info = f" [{dynamic_type}:{character}]" if character else ""
                    source_info = f" ({source})"

                    f.write(f"{actor} -> {cre_info}{mapping_detail}{dynamic_info}{source_info}\n")

            print(f"\nActor-to-CRE mapping saved to: {args.output}")
        except Exception as e:
            print(f"Error saving to {args.output}: {e}")

    return 0


if __name__ == '__main__':
    exit(main())
