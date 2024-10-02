#!/usr/bin/env python3

import argparse
import os
import pathlib
import re


def collect_uniq_filenames(in_folder, folders_to_skip, filenames_to_skip):
    es = ['ogg', 'wav', 'bam', 'bmp', 'cre', 'd', 'eff', 'itm', 'pro', 'baf', 'spl', 'sto', 'tra', 'vvc']
    all_ids_with_files = []
    extensions = ["." + x.upper() for x in es]

    for dir_, _, files in os.walk(in_folder):
        rel_dir = os.path.relpath(dir_, in_folder)
        folders = pathlib.PurePath(rel_dir).parts
        if not any([i in folders for i in folders_to_skip]):
            for file in files:
                split_filename = os.path.splitext(file)
                # TODO: add not renaming RNDTRE08.ITM and similar items
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


def build_table(ids, prefix, file_for_names):
    names_to_rename = set()
    if file_for_names:
        with open(file_for_names, "rt") as f:
            lines = [line.rstrip('\n').upper() for line in f]
            names_to_rename = set(lines)

    table = {}
    for id in ids:
        id_cleaned = clean_id(id)
        if id.startswith(prefix):
            continue
        if len(names_to_rename) > 0 and id not in names_to_rename:
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
        if v in v2k or v in ids:
            # try to solve the collisions
            new_v = v
            for j in range(100):
                suffix = str(j)
                if len(suffix) + len(v) <= 8:
                    v_candidate = v + suffix
                else:
                    n_to_eat = len(v) + len(suffix) - 8
                    v_candidate = v[0:-n_to_eat] + suffix
                if v_candidate not in values and v_candidate not in ids:
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
And generate global renaming table with this prefix
All area files (are, mos, wed, tis) and music files (acm, mus) are considered to have proper names
example of parameters for NWN: /home/paladin/source/NWNForBG/NWNForBG/ 1.txt 2.txt NW --skip-folders 2da Worldmap are ia_cre ia_ini legacy_dlg lib missing_anim_ee movies to_extend tis tis_ee iconv setup setup-ee --skip-files setup setup-ee worldmap
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('in_folder', help='Folder recursively search filename in.')
    parser.add_argument('out_table_file', help='File to print renaming table.')
    parser.add_argument('out_filenames_file', help='File to print original files to rename.')
    parser.add_argument('prefix', help='Prefix to add')
    parser.add_argument('--skip-folders', help='Case sensitive folder names to skip', nargs='+', default=[])
    parser.add_argument('--skip-files', help='Case sensitive file names to skip', nargs='+',
                        default=[])
    parser.add_argument('--names-from-file-only', help='To rename only some particular names, the file with names can be provided here', default="")
    args = parser.parse_args()

    ids_with_filenames = collect_uniq_filenames(args.in_folder, args.skip_folders, args.skip_files)
    # print(ids_with_filenames)
    ids = set()
    for e in ids_with_filenames:
        ids.add(e[0])
    table = build_table(ids, args.prefix, args.names_from_file_only)

    f = open(args.out_filenames_file, "w")
    for e in ids_with_filenames:
        f.write("{}, {}\n".format(e[0], e[1]))
    f.close()

    f1 = open(args.out_table_file, "w")
    for k in table:
        f1.write("{}, {}\n".format(k, table[k]))
    f1.close()
