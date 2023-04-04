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
            result.append(n)
    return result


def update_file(infile, infile2):
    all_items_number = find_items(infile, "Вес: ")
    print(all_items_number)
    dict_with_proper_desc = read_file1(infile2)

    with open(infile, mode='r') as file:
        text = file.read()
    out_text = text

    indexes = [i for i, ltr in enumerate(text) if ltr == '~']
    pairs = list(zip(indexes[::2], indexes[1::2]))
    n_translated = 0
    n_processed = 0
    out_text_offset = 0

    find_number_re = re.compile('@(\\d+)')
    find_delimiter_re = re.compile('@[0-9]+[\\s]*=[\\s]*(.)')
    find_string_re = re.compile('@[0-9]+[^@]*')
    find_replica_re0 = re.compile('~([^~]*)~')
    find_replica_re1 = re.compile('"([^"]*)"')
    lines = find_string_re.findall(text)

    r = True
    start_i = -1
    while True:
        r = find_string_re.search(text, start_i + 1)
        if not r:
            break
        start_i = r.start()
        end_i = r.end() - 1
        if end_i == len(text) - 1:
            end_i += 1
        n_processed += 1
        print('processing {} out of {}'.format(n_processed, len(lines)))
        line = text[start_i:end_i]
        numbers = find_number_re.findall(line)
        if len(numbers) == 0:
            continue
        number = numbers[0]
        if number not in all_items_number:
            continue
        if number not in dict_with_proper_desc:
            continue
        translated_line = line
        delimiters = find_delimiter_re.findall(line)
        if len(delimiters) != 1 or (delimiters[0] != '~' and delimiters[0] != '"'):
            print("Cannot process line: \"{}\", skipping".format(line))
            continue
        if delimiters[0] == "~":
            find_replica_re = find_replica_re0
        else:
            find_replica_re = find_replica_re1

        strings = find_replica_re.findall(line)
        for string in strings:
            translated_string = ""
            if string:
                new_desc = dict_with_proper_desc[number][0].split("ХАРАКТ")[0]
                translated_string = string
                tokens = translated_string.split("ПАРАМЕТРЫ:")
                if len(tokens) > 1:
                    tokens[0] = new_desc
                    translated_string = "ПАРАМЕТРЫ:".join(tokens)
                else:
                    new_desc = dict_with_proper_desc[number][0].split("Вес")[0]
                    translated_string = string
                    tokens = translated_string.split("Вес:")
                    if len(tokens) > 1:
                        tokens[0] = new_desc
                        translated_string = "Вес:".join(tokens)

            if string != translated_string:
                translated_line = translated_line.replace(string, translated_string)

        if line != translated_line:
            print('"{}" translated into "{}"'.format(line, translated_line))
            out_text = out_text[:(start_i + out_text_offset)] + translated_line + out_text[(end_i + out_text_offset):]
            out_text_offset += (len(translated_line) - len(line))

    with open(infile, mode='w') as outfile:
        outfile.write(out_text)



__desc__ = '''
This program find all the items in tra file and replace their description from another file
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='File to find items in.')
    parser.add_argument('infile1', help='File to have description from.')
    # parser.add_argument('--source-dir', help='Dir with original tra files (should be the same lang as for infile).', required=True)
    args = parser.parse_args()
    update_file(args.infile, args.infile1)
    

