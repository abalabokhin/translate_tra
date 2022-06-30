#!/usr/bin/env python3

import argparse
import urllib.error
import os
import sys
import chardet
import re
from Levenshtein import distance as levenshtein_distance

def remove_extra_spaces(string):
    result = "".join(string.split())
    return result

def read_file1(infile, enc=None, remove_whitespaces = False):
    print("\n\nStarted processing file {}".format(infile))
    if enc is None:
        with open(infile, mode='rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            enc = result['encoding']

    print("\n\nStarted processing file {} with encoding {}\n\n".format(infile, enc))
    try:
        with open(infile, mode='r', encoding=enc) as file:
            text = file.read()
    except UnicodeDecodeError:
        with open(infile, mode='r') as file:
            text = file.read()

    lines = re.findall('@[0-9]+[^@]*', text)
    find_number_re = re.compile('@([0-9]+)')
    find_replica_re = re.compile('~([^~]*)~')
    find_replica_re1 = re.compile('"([^"]*)"')
    find_replica_re2 = re.compile('%([^%]*)%')

    lines_n = len(lines)
    result = dict()
    for num, line in enumerate(lines):
        numbers = find_number_re.findall(line)
        replicas = find_replica_re.findall(line)
        if len(replicas) == 0 or len(replicas) > 2:
            replicas = find_replica_re1.findall(line)
            if len(replicas) == 0 or len(replicas) > 2:
                replicas = find_replica_re2.findall(line)

        if len(numbers) != 1 or len(replicas) == 0 or len(replicas) > 2:
            sys.exit('Bad line in file {}: \n {}'.format(infile, line))
        if remove_whitespaces:
            fixed_replicas = []
            for r in replicas:
                fixed_replicas.append(remove_extra_spaces(r))
        else:
            fixed_replicas = replicas
        result[numbers[0]] = fixed_replicas
    return result


def build_dict_file(result, orig_file, tr_file, tr_enc):
    print(orig_file, tr_file)
    dfo = read_file1(orig_file, None, True)
    dft = read_file1(tr_file, tr_enc)
    common_keys = list(set(dfo.keys()) & set(dft.keys()))
    for k in common_keys:
        if dfo[k][0] not in result:
            result[dfo[k][0]] = [dft[k]]
        else:
            result[dfo[k][0]].append(dft[k])


def upper_case_map(strings):
    result = dict()
    for s in strings:
        result[s.upper()] = s
    return result


def build_dict_dir(orig_dir, tr_dir, tr_enc):
    result = dict()
    orig_files = os.listdir(orig_dir)
    tr_files = os.listdir(tr_dir)
    orig_files_map = upper_case_map(orig_files)
    tr_files_map = upper_case_map(tr_files)
    common_files = list(orig_files_map.keys() & tr_files_map.keys())
    for cf in common_files:
        build_dict_file(result, os.path.join(orig_dir, orig_files_map[cf]), os.path.join(tr_dir, tr_files_map[cf]), tr_enc)
    return result


def find_closest_lines(src_file, dst_file, tr_enc=''):
    src_dict = read_file1(src_file)
    dst_dict = read_file1(dst_file)
    for n in src_dict.keys():
        # print(n)
        src_string = src_dict[n][0]
        if n in dst_dict:
            dst_string = dst_dict[n][0]
            if src_string == dst_string:
                # don't print the same lines
                # print(n, src_dict[n], dst_dict[n])
                continue

        # processing empty string
        if not src_string:
            if n in dst_dict:
                print(n, src_dict[n], dst_dict[n], "!!! Empy string in src but in dst not empty!!!")
                pass
            else:
                print(n, src_dict[n], "!!! Empy string only in src !!!")
            continue

        min_d = 1000000
        dst_n = -1
        for n1 in dst_dict.keys():
            dst_string = dst_dict[n1][0]
            d = levenshtein_distance(src_string, dst_string)
            if d < min_d or (d == min_d and n1 == n):
                min_d = d
                dst_n = n1
            if min_d == 0:
                break

        if dst_n == n:
            # don't print the same lines
            continue

        print(n, dst_n, src_dict[n], dst_dict[dst_n])








    # tr_map = build_dict_file(srcfile,  tr_dir, tr_enc)
    # if len(tr_map) == 0:
    #     sys.exit("Cannot build translation dict from '{}' and '{}' dirs".format(orig_dir, tr_dir))
    #
    # with open(infile, mode='r') as file:
    #     text = file.read()
    # out_text = text
    #
    # indexes = [i for i, ltr in enumerate(text) if ltr == '~']
    # pairs = list(zip(indexes[::2], indexes[1::2]))
    # n_translated = 0
    # n_processed = 0
    # out_text_offset = 0
    # for p in pairs:
    #     n_processed += 1
    #     string = text[p[0] + 1: p[1]]
    #     print('processing string "{}", {} out of {}'.format(string, n_processed, len(pairs)))
    #     translated_string = string
    #     fixed_string = remove_extra_spaces(string)
    #     check_me = True
    #     if fixed_string in tr_map:
    #         translated_string = tr_map[fixed_string][0][0]
    #         check_me = False
    #
    #     n_translated +=1
    #     if check_me:
    #         translated_string = translated_string
    #     out_text = out_text[:(p[0] + 1 + out_text_offset)] + translated_string + out_text[(p[1] + out_text_offset):]
    #     out_text_offset += (len(translated_string) - len(string))
    #
    # with open(outfile, mode='w') as outf:
    #     outf.write(out_text)


__desc__ = '''
This program take one tra file and find all the closest lines (based on Levenshtein distance) in another tra file. 
'''

# TODO: 1) add support for male/female translation
# 2) smarter search (if there is a translation from several sources - it should be taken from the same file"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile1', help='File to check all tra lines from.')
    parser.add_argument('infile2', help='File to find closest line for every line in infile1.')
    # parser.add_argument('--source-dir', help='Dir with original tra files (should be the same lang as for infile).', required=True)
    args = parser.parse_args()

    find_closest_lines(args.infile1, args.infile2)
