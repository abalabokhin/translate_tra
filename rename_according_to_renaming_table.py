#!/usr/bin/env python3

import argparse
import os
import pathlib
import re


def change_refs(in_folder, renaming_table_filename):
    table_file = open(renaming_table_filename, "r")
    table = {}
    for l in f.readlines():
        tokens = l.split(',')
        table[tokens[0]] = tokens[1]

    # check, do we need eff?
    es_bin = ['are', 'cre', 'eff', 'itm', 'pro', 'spl', 'sto', 'vvs']
    ex_text = ['d', 'tph', 'baf', 'tra', 'tp2']
    es = ['ogg', 'wav', 'bam', 'bmp', 'cre', 'd', 'eff', 'itm', 'pro', 'baf', 'spl', 'sto', 'tra', 'vvc']
    all_ids_with_files = []
    extensions = ["." + x.upper() for x in es]

    for dir_, _, files in os.walk(in_folder):
        rel_dir = os.path.relpath(dir_, in_folder)
        folders = pathlib.PurePath(rel_dir).parts
        if not any([i in folders for i in folders_to_skip]):
            for file in files:
                split_filename = os.path.splitext(file)
                if (split_filename[1].upper() in extensions and split_filename[0] not in filenames_to_skip and
                        not re.match("SP(PR|WI|IN|CL[0-9]{3})", split_filename[0].upper())):
                    all_ids_with_files.append((split_filename[0].upper(), os.path.join(dir_, file)))
    return all_ids_with_files


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
    ids = set()
    for e in ids_with_filenames:
        ids.add(e[0])
    table = build_table(ids, args.prefix)

    f = open(args.out_filenames_file, "w")
    for e in ids_with_filenames:
        f.write("{}, {}\n".format(e[0], e[1]))
    f.close()

    f1 = open(args.out_table_file, "w")
    for k in table:
        f1.write("{}, {}\n".format(k, table[k]))
    f1.close()
