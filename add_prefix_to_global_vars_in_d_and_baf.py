#!/usr/bin/env python3

import argparse
import os
import pathlib
import re
import sys

def add_prefix_in_txt(filename):
    f = open(filename, "r", encoding='cp1251')
    _, ext = os.path.splitext(filename)
    s = f.read()
    s_orig = s
    f.close()
    for el in set(re.findall(r'[^"]*"\s*,\s*"GLOBAL"', s, flags=re.IGNORECASE)):
        if not el.upper().startswith('SPRITE') and not el.upper().startswith('NW'):
            s = s.replace(el, 'NW'+el)

    if s != s_orig:
        print("txt file {} changed and saved".format(filename))
        f = open(filename, "w", encoding='cp1251')
        f.write(s)
        f.close()


def change_refs(in_folder, folders_to_skip):
    ex_txt = ['d', 'baf']
    extensions_txt = ["." + x.upper() for x in ex_txt]

    for dir_, _, files in os.walk(in_folder):
        rel_dir = os.path.relpath(dir_, in_folder)
        folders = pathlib.PurePath(rel_dir).parts
        if not any([i in folders for i in folders_to_skip]):
            for file in files:
                split_filename = os.path.splitext(file)
                if split_filename[1].upper() in extensions_txt:
                    add_prefix_in_txt(os.path.join(dir_, file))


__desc__ = '''
This program add prefix NW to all references to all global variables in D and BAF files.
Example of parameters for NWN: 
/home/paladin/source/translations/NWNForBG/NWNForBG/ --skip-folders legacy_dlg
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('in_folder', help='Folder recursively rename files and references to them in.')
    parser.add_argument('--skip-folders', help='Case sensitive folder names to skip', nargs='+', default=[])
    args = parser.parse_args()

    change_refs(args.in_folder, args.skip_folders)
