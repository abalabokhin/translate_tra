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

    lines = re.findall('@\\d+[^@]*', text)
    find_number_re = re.compile('@(\\d+)')
    find_replica_re = re.compile('~~~~~(.*)~~~~~')
    find_replica_re0 = re.compile('~([^~]*)~')
    find_replica_re1 = re.compile('"([^"]*)"')
    find_replica_re2 = re.compile('%([^%]*)%')

    lines_n = len(lines)
    result = dict()
    for line in lines:
        numbers = find_number_re.findall(line)
        if len(numbers) != 1:
            sys.exit('Bad line in file {}: \n {}'.format(infile, line))
        replicas = find_replica_re.findall(line)
        if len(replicas) == 0 or len(replicas) > 2:
            replicas = find_replica_re0.findall(line)
            if len(replicas) == 0 or len(replicas) > 2:
                replicas = find_replica_re1.findall(line)
                if len(replicas) == 0 or len(replicas) > 2:
                    replicas = find_replica_re2.findall(line)

        if len(replicas) == 0 or len(replicas) > 2:
            sys.exit('Bad line in file {}: \n {}'.format(infile, line))
        if remove_whitespaces:
            fixed_replicas = []
            for r in replicas:
                fixed_replicas.append(remove_extra_spaces(r))
        else:
            fixed_replicas = replicas
        result[numbers[0]] = fixed_replicas
    return result


def find_items(src_file, search_string, tr_enc=''):
    src_dict = read_file1(src_file)
    result = []
    for n in src_dict.keys():
        # print(n)
        src_string = src_dict[n][0]
        if src_string.find(search_string) >= 0:
            print(n)


__desc__ = '''
This program find all the items in tra file and return their numbers.
'''

# TODO: 1) add support for male/female translation
# 2) smarter search (if there is a translation from several sources - it should be taken from the same file"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='File to find items in.')
    # parser.add_argument('--source-dir', help='Dir with original tra files (should be the same lang as for infile).', required=True)
    args = parser.parse_args()

    find_items(args.infile, "Вес: ")
