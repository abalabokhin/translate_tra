#!/usr/bin/env python3

import argparse
import urllib.error
import os
import sys
import chardet
import re

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

    lines_n = len(lines)
    result = dict()
    for num, line in enumerate(lines):
        numbers = find_number_re.findall(line)
        replicas = find_replica_re.findall(line)
        if len(replicas) == 0:
            replicas = find_replica_re1.findall(line)

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


def update_file(infile, outfile, orig_dir, tr_dir, tr_enc=''):
    tr_map = build_dict_dir(orig_dir, tr_dir, tr_enc)
    if len(tr_map) == 0:
        sys.exit("Cannot build translation dict from '{}' and '{}' dirs".format(orig_dir, tr_dir))

    with open(infile, mode='r') as file:
        text = file.read()
    out_text = text

    indexes = [i for i, ltr in enumerate(text) if ltr == '~']
    pairs = list(zip(indexes[::2], indexes[1::2]))
    n_translated = 0
    n_processed = 0
    out_text_offset = 0
    for p in pairs:
        n_processed += 1
        string = text[p[0] + 1: p[1]]
        print('processing string "{}", {} out of {}'.format(string, n_processed, len(pairs)))
        translated_string = string
        fixed_string = remove_extra_spaces(string)
        check_me = True
        if fixed_string in tr_map:
            translated_string = tr_map[fixed_string][0][0]
            check_me = False

        n_translated +=1
        if check_me:
            translated_string = translated_string
        out_text = out_text[:(p[0] + 1 + out_text_offset)] + translated_string + out_text[(p[1] + out_text_offset):]
        out_text_offset += (len(translated_string) - len(string))

    with open(outfile, mode='w') as outf:
        outf.write(out_text)


__desc__ = '''
This program automatically update one *.tra file translation from other source.
The idea that sometimes already translated lines are located in defferent files.
So, if we have the source file with the original language (e.g en), and lots of other files
with original texts (on e.g. english) and already translated texts, we can search already
translated files for some replicas.
'''

# TODO: 1) add support for male/female translation
# 2) smarter search (if there is a translation from several sources - it should be taken from the same file"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='Input filename.')
    parser.add_argument('--out', help='Output filename.', required=True)
    parser.add_argument('--source-dir', help='Dir with original tra files (should be the same lang as for infile).', required=True)
    parser.add_argument('--translated-dir', help='Dir with translated tra files (should be the same lang as for output file).', required=True)
    parser.add_argument('--translated-encoding', help='You can specify the translated encoding here, otherwise it is defined automatically.', required=False)
    args = parser.parse_args()

    out = args.out
    if not out:
        out = args.infile

    update_file(args.infile, out, args.source_dir, args.translated_dir, args.translated_encoding)
