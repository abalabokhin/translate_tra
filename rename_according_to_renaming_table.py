#!/usr/bin/env python3

import argparse
import os
import pathlib
import re
import sys


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
        f = open(filename, "w", encoding='cp1251')
        f.write(s)
        f.close()

def change_refs(in_folder, renaming_table_filename, folders_to_skip):
    table_file = open(renaming_table_filename, "r")
    table = {}
    for l in table_file.readlines():
        tokens = l.split(',')
        table[tokens[0].strip()] = tokens[1].strip()

    print(table)
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
                    print("processing binary file {}".format(file))
                    replace_refs_in_bin(os.path.join(dir_, file), table)
                if split_filename[1].upper() in extensions_txt:
                    print("processing txt file {}".format(file))
                    replace_refs_in_txt(os.path.join(dir_, file), table)

def clean_id(id_to_clean):
    result = id_to_clean
    for c in ["_", "-", "#"]:
        i = result.find(c)
        if 0 <= i <= 2:
            result = result[i + 1:]
        result = result.replace(c, '')
    return result


def build_table(ids, prefix):
    table = {}
    for id in ids:
        id_cleaned = clean_id(id)
        if id.startswith(prefix):
            continue
        i = id.find(prefix)
        if i >= 0:
            value = prefix + id[:i] + id[i+len(prefix):]
        elif len(id) <= 8 - len(prefix):
            value = prefix + id
        elif len(id_cleaned) <= 8 - len(prefix):
            value = prefix + id_cleaned
        else:
            n_to_eat = len(prefix) + len(id_cleaned) - 8
            n_keep_at_end = 1
            result = re.search("[0-9]+$", id_cleaned)
            if result:
                n_keep_at_end = len(result.group())
            else:
                result = re.search("[0-9]+.$", id_cleaned)
                if result:
                    n_keep_at_end = len(result.group())
            if n_to_eat + n_keep_at_end > 8:
                n_keep_at_end = n_to_eat + n_keep_at_end - 8
            value = prefix + id_cleaned[0: len(id_cleaned) - n_to_eat - n_keep_at_end]
            if n_keep_at_end > 0:
                value += id_cleaned[-n_keep_at_end:]
        table[id] = value

    values = set(table.values())
    v2k = {}
    for k in table:
        v = table[k]
        if v in v2k:
            # try to solve the collisions
            new_v = v
            for j in range(100):
                suffix = str(j)
                if len(suffix) + len(v) <= 8:
                    v_candidate = v + suffix
                else:
                    n_to_eat = len(v) + len(suffix) - 8
                    v_candidate = v[0:-n_to_eat] + suffix
                if v_candidate not in values:
                    new_v = v_candidate
                    break

            if new_v == v:
                print("UNSOLVED COLLISION {}->{}, {}->{}".format(v2k[v], v, k, v))
            v = new_v
        if len(v) > 8:
            print("Error in defining new id name: ", k, v)
        values.add(v)
        v2k[v] = k
        table[k] = v

    return table


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

    ids_with_filenames = change_refs(args.in_folder, args.in_table_file, args.skip_folders)
    # print(ids_with_filenames)

