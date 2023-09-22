#!/usr/bin/env python3

import argparse
import os
import pathlib
import re
import sys


def read_table(filename):
    table_file = open(filename, "r")
    table = {}
    for line in table_file.readlines():
        tokens = line.split(',')
        table[tokens[0].strip()] = tokens[1].strip()
    return table


def replace_refs_in_bin(filename, table):
    f = open(filename, "rb")
    s = f.read()
    s_orig = s
    f.close()
    for key in table:
        key_b = bytes(key, 'ascii')
        key_b = key_b + bytearray(8 - len(key_b))
        value_b = bytes(table[key], 'ascii')
        value_b = value_b + bytearray(8 - len(value_b))
        s = re.sub(key_b, value_b, s, flags=re.IGNORECASE)

    if s != s_orig:
        print("bin file {} changed and saved".format(filename))
        f = open(filename, "wb")
        f.write(s)
        f.close()


def replace_refs_in_txt(filename, table):
    f = open(filename, "r", encoding='cp1251')
    s = f.read()
    s_orig = s
    f.close()
    for key in table:
        s = re.sub('\\b'+key+'\\b', table[key], s, flags=re.IGNORECASE)

    if s != s_orig:
        print("txt file {} changed and saved".format(filename))
        f = open(filename, "w", encoding='cp1251')
        f.write(s)
        f.close()


def rename_files_according_to_table(file_table, renaming_table):
    print(renaming_table)
    for k in file_table:
        if k not in renaming_table:
            continue
        new_basename = renaming_table[k]
        path, filename = os.path.split(file_table[k])
        _, ext = os.path.splitext(filename)
        new_full_filename = os.path.join(path, new_basename + ext)
        print("renaming {} into {}".format(file_table[k], new_full_filename))
        os.rename(file_table[k], new_full_filename)


def change_refs(in_folder, renaming_table, folders_to_skip):
    print(renaming_table)
    # check, do we need eff?
    es_bin = ['are', 'cre', 'eff', 'itm', 'pro', 'spl', 'sto', 'vvs']
    ex_txt = ['d', 'tph', 'baf', 'tra', 'tp2']
    extensions_bin = ["." + x.upper() for x in es_bin]
    extensions_txt = ["." + x.upper() for x in ex_txt]

    for dir_, _, files in os.walk(in_folder):
        rel_dir = os.path.relpath(dir_, in_folder)
        folders = pathlib.PurePath(rel_dir).parts
        if not any([i in folders for i in folders_to_skip]):
            for file in files:
                split_filename = os.path.splitext(file)
                if split_filename[1].upper() in extensions_bin:
                    replace_refs_in_bin(os.path.join(dir_, file), renaming_table)
                if split_filename[1].upper() in extensions_txt:
                    replace_refs_in_txt(os.path.join(dir_, file), renaming_table)


__desc__ = '''
This program change all references to all resources according to the provided table and rename files itself.
Example of parameters for NWN: 
/home/paladin/source/translations/NWNForBG/NWNForBG/ 1.txt 2.txt --skip-folders legacy_dlg
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('in_folder', help='Folder recursively rename files and references to them in.')
    parser.add_argument('in_table_file', help='File to read renaming table.')
    parser.add_argument('in_filenames_file', help='File with original files and paths to them.')
    parser.add_argument('--skip-folders', help='Case sensitive folder names to skip', nargs='+', default=[])
    args = parser.parse_args()

    file_table = read_table(args.in_filenames_file)
    renaming_table = read_table(args.in_table_file)
    change_refs(args.in_folder, renaming_table, args.skip_folders)
    rename_files_according_to_table(file_table, renaming_table)
