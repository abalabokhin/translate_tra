#!/usr/bin/env python3

import argparse
import os
import pathlib
import re


def collect_uniq_filenames(in_folder, folders_to_skip):
    es = ['ogg', 'wav', 'bam', 'bmp', 'cre', 'd', 'eff', 'itm', 'mus', 'acm', 'pro', 'baf', 'spl', 'sto', 'tra', 'vvc']
    all_ids = set()
    extensions = ["." + x.upper() for x in es]
    for dir_, _, files in os.walk(in_folder):
        rel_dir = os.path.relpath(dir_, in_folder)
        folders = pathlib.PurePath(rel_dir).parts
        if not any([i in folders for i in folders_to_skip]):
            for f in files:
                file_upper = f.upper()
                split_filename = os.path.splitext(file_upper)
                if split_filename[1] in extensions and not re.match("SP(PR|WI|IN|CL[0-9]{3})", split_filename[0]):
                    all_ids.add(split_filename[0])
    print(all_ids)


__desc__ = '''
This program collect all unique filenames that prefix should be added to 
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('in_folder', help='Folder recursively search filename in.')
    parser.add_argument('out_file', help='Folder recursively search filename in.')
    parser.add_argument('prefix', help='Prefix to add')
    parser.add_argument('--skip', help='Folder names to skip', nargs='+', default=[])
    args = parser.parse_args()

    collect_uniq_filenames(args.in_folder, args.skip)
