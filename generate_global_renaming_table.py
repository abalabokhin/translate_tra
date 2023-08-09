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
    return all_ids


def clean_id(id):
    result = id
    for c in ["_", "-", "#"]:
        i = result.find(c)
        if 0 <= i <= 2:
            result = result[i + 1:]
        result = result.replace(c, '')
    return result

def build_table(ids, prefix):
    table = {}
    for id in ids:
        value = id
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
            if n_to_eat + n_keep_at_end >= 8:
                n_keep_at_end = 0
            value = prefix + id_cleaned[0: len(id_cleaned) - n_to_eat - n_keep_at_end]
            if n_keep_at_end > 0:
                value += id_cleaned[-n_keep_at_end:]

        if len(value) > 8:
            print("Error in defining value for id: id, value", id, value)
        table[id] = value
    v2i = {}
    for i in table:
        v = table[i]
        if v in v2i:
            print("COLLISION {}->{}, {}->{}".format(v2i[v], v, i, v))
        v2i[v] = i








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

    ids = collect_uniq_filenames(args.in_folder, args.skip)
    build_table(ids, args.prefix)