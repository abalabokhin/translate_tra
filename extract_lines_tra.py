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


def read_file1(infile, enc=None):
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

    lines_n = len(lines)
    result = dict()
    for line in lines:
        numbers = find_number_re.findall(line)
        if len(numbers) != 1:
            sys.exit('Bad line in file {}: \n {}'.format(infile, line))

        result[numbers[0]] = line
    return result


def extract_lines(src_file, number_file, tr_enc=''):
    with open(number_file, mode='r') as file:
        text = file.read()
    numbers = list(set(text.split()))
    numbers = list(map(int, numbers))
    numbers.sort()
    numbers = list(map(str, numbers))

    src_dict = read_file1(src_file)

    for n in numbers:
        if n not in src_dict:
            sys.exit(f"Line #{n} not in tra file.")
        rr = src_dict[n]
        print(rr.strip())


__desc__ = '''
This program find all the items in tra file and return their numbers.
'''

# TODO: 1) add support for male/female translation
# 2) smarter search (if there is a translation from several sources - it should be taken from the same file"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile1', help='Tra file to find items in.')
    parser.add_argument('infile2', help='File with lines to extract. Numbers can be duplicated. Every nymber must be on the next string')
    # parser.add_argument('--source-dir', help='Dir with original tra files (should be the same lang as for infile).', required=True)
    args = parser.parse_args()

    extract_lines(args.infile1, args.infile2)
