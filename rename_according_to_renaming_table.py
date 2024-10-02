#!/usr/bin/env python3

import argparse
import os
import pathlib
import re
import sys
import magic


def read_table(filename):
    table_file = open(filename, "r")
    table = []
    for line in table_file.readlines():
        tokens = line.split(',')
        table.append((tokens[0].strip(), tokens[1].strip()))
    return table


def replace_refs_in_bin(filename, table_bin):
    f = open(filename, "rb")
    s = f.read()
    s_orig = s
    f.close()
    pos_i = 0
    while pos_i < len(s_orig) - 8:
        id_candidate = s[pos_i:pos_i+8].upper()
        if id_candidate[0:2] == b'NW':
            pos_i += 8
            continue
        if id_candidate in table_bin:
            s = s[:pos_i] + table_bin[id_candidate] + s[pos_i+8:]
            pos_i += 8
        else:
            pos_i += 1

    if s != s_orig:
        print("bin file {} changed and saved".format(filename))
        f = open(filename, "wb")
        f.write(s)
        f.close()


def replace_refs_in_txt(filename, table):
    # TODO: make dedicated processing for SPRITE_IS_DEAD variable
    with open(filename, 'rb') as file_blob:
        blob = file_blob.read()
        m = magic.open(magic.MAGIC_MIME_ENCODING)
        m.load()
        encoding = m.buffer(blob)
    if encoding == 'unknown-8bit' or encoding == 'us-ascii':
        encoding = 'cp1251'
    print("processing {} with encoding {}".format(filename, encoding))
    f = open(filename, "r", encoding=encoding)
    _, ext = os.path.splitext(filename)
    s = f.read()
    s_orig = s
    f.close()
    if ext.upper() == '.TRA':
        for key in table:
            s = re.sub('\\[ *' + key + ' *\\]', '[' + table[key] + ']', s, flags=re.IGNORECASE)
    else:
        for key in table:
            s = re.sub('\\b' + key + '\\b', table[key], s, flags=re.IGNORECASE)

    if s != s_orig:
        print("txt file {} changed and saved".format(filename))
        f = open(filename, "w", encoding='cp1251')
        f.write(s)
        f.close()


def rename_files_according_to_table(file_table, renaming_table):
    for k, orig_filepath in file_table:
        if k not in renaming_table:
            continue
        new_basename = renaming_table[k]
        path, filename = os.path.split(orig_filepath)
        _, ext = os.path.splitext(filename)
        new_full_filename = os.path.join(path, new_basename + ext)
        print("renaming {} into {}".format(orig_filepath, new_full_filename))
        os.rename(orig_filepath, new_full_filename)


def change_refs(in_folder, renaming_table_txt, folders_to_skip):
    print(renaming_table)
    es_bin = ['are', 'cre', 'eff', 'itm', 'pro', 'spl', 'sto', 'vvc']
    ex_txt = ['d', 'tph', 'baf', 'tra', 'tp2']
    extensions_bin = ["." + x.upper() for x in es_bin]
    extensions_txt = ["." + x.upper() for x in ex_txt]

    renaming_table_bin = {}
    for key in renaming_table_txt:
        if len(key) > 8 or len(renaming_table_txt[key]) > 8:
            continue
        key_b = bytes(key, 'ascii')
        key_b = key_b + bytearray(8 - len(key_b))
        value_b = bytes(renaming_table_txt[key], 'ascii')
        value_b = value_b + bytearray(8 - len(value_b))
        renaming_table_bin[key_b.upper()] = value_b.upper()

    print(in_folder)
    for dir_, _, files in os.walk(in_folder):
        rel_dir = os.path.relpath(dir_, in_folder)
        folders = pathlib.PurePath(rel_dir).parts
        if not any([i in folders for i in folders_to_skip]):
            for file in files:
                split_filename = os.path.splitext(file)
                if split_filename[1].upper() in extensions_bin:
                    replace_refs_in_bin(os.path.join(dir_, file), renaming_table_bin)
                if split_filename[1].upper() in extensions_txt:
                    replace_refs_in_txt(os.path.join(dir_, file), renaming_table_txt)


__desc__ = '''
This program change all references to all resources according to the provided table and rename files itself.
Example of parameters for NWN: 
/home/paladin/source/translations/NWNForBG/NWNForBG/ 1.txt --in_filenames_file 2.txt --skip-folders legacy_dlg reference
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('in_folder', help='Folder recursively rename files and references to them in.')
    parser.add_argument('in_table_file', help='File to read renaming table.')
    parser.add_argument('--in_filenames_file', help='File with original files and paths to them.', required=False)
    parser.add_argument('--skip-folders', help='Case sensitive folder names to skip', nargs='+', default=[])
    args = parser.parse_args()

    renaming_table = dict(read_table(args.in_table_file))
    change_refs(args.in_folder, renaming_table, args.skip_folders)
    if args.in_filenames_file:
        file_table = read_table(args.in_filenames_file)
        rename_files_according_to_table(file_table, renaming_table)
