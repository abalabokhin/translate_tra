#!/usr/bin/env python3

import argparse
import os
import pathlib
import re
import sys

def find_global_vars_in_one_txt(filename):
    f = open(filename, "r", encoding='cp1251')
    _, ext = os.path.splitext(filename)
    s = f.read()
    s_orig = s
    f.close()
    result = set()
    for el in re.findall(r'"[^"]*"\s*,\s*"GLOBAL"', s, flags=re.IGNORECASE):
        m1 = re.search('"([^"]*)"', str(el))
        if m1:
            result.add(m1.group(1))

    return result


def find_all_global_vars(in_folder, folders_to_skip, prefix):
    ex_txt = ['d', 'baf']
    extensions_txt = ["." + x.upper() for x in ex_txt]

    global_result = set()
    for dir_, _, files in os.walk(in_folder):
        rel_dir = os.path.relpath(dir_, in_folder)
        folders = pathlib.PurePath(rel_dir).parts
        if not any([i in folders for i in folders_to_skip]):
            for file in files:
                split_filename = os.path.splitext(file)
                if split_filename[1].upper() in extensions_txt:
                    result = find_global_vars_in_one_txt(os.path.join(dir_, file))
                    if result:
                        global_result.update(result)

    table = {}
    for r in global_result:
        if not r.startswith(prefix) and not r.startswith('SPRITE_IS_DEAD'):
            table[r] = prefix + r

    return table


__desc__ = '''
This program add prefix NW to all references to all global variables in D and BAF files.
Example of parameters for NWN: 
/home/paladin/source/translations/NWNForBG/NWNForBG/ --skip-folders legacy_dlg --prefix NW
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('in_folder', help='Folder recursively rename files and references to them in.')
    parser.add_argument('out_table_file', help='File to print renaming table.')
    parser.add_argument('prefix', help='Prefix to add.')
    parser.add_argument('--skip-folders', help='Case sensitive folder names to skip.', nargs='+', default=[])
    args = parser.parse_args()

    table = find_all_global_vars(args.in_folder, args.skip_folders, args.prefix)
    f1 = open(args.out_table_file, "w")
    for k in table:
        f1.write("{}, {}\n".format(k, table[k]))
    f1.close()
