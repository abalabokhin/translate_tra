#!/usr/bin/env python3

import argparse
import os
import chardet
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
    """Check if the actor name is valid (starts with TC or BTC)."""
    if not actor_name:
        return False
    # Valid actor names should start with TC or BTC
    return actor_name.startswith(('TC', 'BTC'))


class ActorExtractionListener(ParseTreeListener):
    """ANTLR4 listener to extract only actor names from D files."""

    def __init__(self, d_filename):
        self.d_filename = d_filename
        self.actors = set()

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
        """Add actor to set if it's a valid actor name."""
        if actor and is_valid_actor_name(actor):
            self.actors.add(actor)

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
    """Extract all unique actors from a D file using ANTLR grammar."""
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
                print(f"  No actors found")
        except Exception as e:
            print(f"  Error processing {d_filename}: {e}")

    return all_actors, file_actors


def main():
    parser = argparse.ArgumentParser(description='''
Extract unique actors from D files using ANTLR grammar.

This script uses the proper ANTLR4 grammar to parse D files and extract
all unique actor names from various dialogue constructs:
- APPEND/APPEND_EARLY statements
- BEGIN statements
- CHAIN statements
- INTERJECT statements
- EXTERN references
- Action statements (EXTEND, REPLACE, etc.)
- Chain speaker lines (== ACTOR)

Only actors starting with TC or BTC are considered valid.
Output shows actors found per file and a summary of all unique actors.
''')

    parser.add_argument('d_folder', help='Folder containing D files')
    parser.add_argument('--output', '-o', help='Output file to save unique actors list')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed per-file actor lists')

    args = parser.parse_args()

    # Process all D files
    all_actors, file_actors = process_d_files_in_folder(args.d_folder)

    if not all_actors:
        print("No valid actors found in any D files")
        return 1

    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: Found {len(all_actors)} unique valid actors total")
    print(f"{'='*60}")

    # Sort actors for consistent output
    sorted_actors = sorted(all_actors)

    if args.verbose:
        print("\nDetailed breakdown by file:")
        for filename, actors in sorted(file_actors.items()):
            print(f"\n{filename}:")
            for actor in sorted(actors):
                print(f"  - {actor}")

    print(f"\nAll unique valid actors ({len(sorted_actors)}):")
    for i, actor in enumerate(sorted_actors, 1):
        print(f"{i:3d}. {actor}")

    # Save to output file if specified
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write("# Unique actors extracted from D files using ANTLR grammar\n")
                f.write(f"# Total: {len(sorted_actors)} valid actors (starting with TC or BTC)\n")
                f.write(f"# Source folder: {args.d_folder}\n\n")

                for actor in sorted_actors:
                    f.write(f"{actor}\n")

            print(f"\nUnique actors list saved to: {args.output}")
        except Exception as e:
            print(f"Error saving to {args.output}: {e}")

    return 0


if __name__ == '__main__':
    exit(main())