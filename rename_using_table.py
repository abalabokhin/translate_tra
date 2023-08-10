#!/usr/bin/env python3

import argparse
import os
import pathlib
import re


def change_inside_files(in_folder, folders_to_skip, rename_table):
    es = ['ogg', 'wav', 'bam', 'bmp', 'cre', 'd', 'eff', 'itm', 'mus', 'acm', 'pro', 'baf', 'spl', 'sto', 'tra', 'vvc']
    all_ids_with_files = []

    extensions = ["." + x.upper() for x in es]
    for dir_, _, files in os.walk(in_folder):
        rel_dir = os.path.relpath(dir_, in_folder)
        folders = pathlib.PurePath(rel_dir).parts
        if not any([i in folders for i in folders_to_skip]):
            for f in files:
                file_upper = f.upper()
                split_filename = os.path.splitext(file_upper)
                if split_filename[1] in extensions and not re.match("SP(PR|WI|IN|CL[0-9]{3})", split_filename[0]):
                    all_ids_with_files.append((split_filename[0], os.path.join(dir_, f)))
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
This program collect all unique filenames that prefix should be added to 
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('in_folder', help='Folder recursively search filename in.')
    parser.add_argument('in_table_file', help='File to read renaming table.')
    parser.add_argument('in_filenames_file', help='File to read files to rename.')
    parser.add_argument('--skip', help='Folder names to skip', nargs='+', default=[])
    args = parser.parse_args()

    table = {}
    f = open(args.in_table_file, "r")
    lines = f.readlines()
    for line in lines:
        line.split(',')
        table[line[0].strip()] = line[1].strip()

    print(table)

    change_inside_files(args.in_folder, args.skip, args.in_table_file)
    rename_files(args.in_filenames_file, args.in_table_file)

