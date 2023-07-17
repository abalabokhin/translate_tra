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


def read_file1(infile, enc=None, remove_whitespaces=False):
    print("\n\nStarted processing file {}".format(infile))
    if enc is None:
        with open(infile, mode='rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            enc = result['encoding']

    print("\n\nStarted processing file {} with encoding {}\n\n".format(infile, enc))
    try:
        with open(infile, mode='r', encoding=enc, newline='\r\n') as file:
            text = file.read()
    except UnicodeDecodeError:
        with open(infile, mode='r', newline='\r\n') as file:
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
        for r in replicas:
            r.replace("\n\n", "\n")
        if remove_whitespaces:
            fixed_replicas = []
            for r in replicas:
                fixed_replicas.append(remove_extra_spaces(r))
        else:
            fixed_replicas = replicas
        result[int(numbers[0])] = fixed_replicas
    return result


def remove_unused(filename_in, filename_used):
    file_used = open(filename_used, "r")
    lines = file_used.readlines()
    used_numbers = set()
    for line in lines:
        line = line.removeprefix("@")
        number = int(line)
        used_numbers.add(number)

    with open(filename_in, mode='rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)

    print("\n\nStarted processing file {} with encoding {}\n\n".format(filename_in, result['encoding']))
    with open(filename_in, mode='r', encoding=result['encoding']) as file:
        text = file.read()
    out_text = ""

    find_delimiter_re = re.compile('@[0-9]+[\\s]*=[\\s]*(.)')
    find_string_re = re.compile('@[0-9]+[^@]*')
    find_replica_re0 = re.compile('~([^~]*)~')
    find_replica_re1 = re.compile('"([^"]*)"')

    lines = find_string_re.findall(text)
    # indexes = [i for i, ltr in enumerate(text) if ltr == '~']
    # pairs = list(zip(indexes[::2], indexes[1::2]))
    n_processed = 0
    out_text_offset = 0

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
        line = text[start_i:end_i]
        m = re.search("@([0-9]+)", line)
        if int(m.group(1)) in used_numbers:
            out_text += (line + "\n")

        #
        # translated_line = line
        # delimiters = find_delimiter_re.findall(line)
        # if len(delimiters) != 1 or (delimiters[0] != '~' and delimiters[0] != '"'):
        #     print("Cannot process line: \"{}\", skipping".format(line))
        #     continue
        # if delimiters[0] == "~":
        #     find_replica_re = find_replica_re0
        # else:
        #     find_replica_re = find_replica_re1
        #
        # strings = find_replica_re.findall(line)
        # for string in strings:
        #     translated_string = ""
        #     if string:
        #         translated_string = string
        #
        #     if string != translated_string:
        #         translated_line = translated_line.replace(string, translated_string)
        #
        # if line != translated_line:
        #     print('"{}" translated into "{}"'.format(line, translated_line))
        #     out_text = out_text[:(start_i + out_text_offset)] + translated_line + out_text[(end_i + out_text_offset):]
        #     out_text_offset += (len(translated_line) - len(line))

    with open(filename_in, mode='w', encoding="cp1251") as outfile:
        outfile.write(out_text)


    # new_dict = {}
    # for number in used_numbers:
    #     new_dict[number] = src_dict[number]
    #
    # file_out = open(filename_in, "w", encoding="cp1251")
    # for i in range(max_number + 1):
    #     if i in new_dict:
    #         if len(new_dict[i]) == 1:
    #             file_out.write("@{} = ~{}~\n".format(i, new_dict[i][0]))
    #         elif len(new_dict[i]) == 2:
    #             file_out.write("@{} = ~{}~ ~{}~\n".format(i, new_dict[i][0], new_dict[i][1]))




__desc__ = '''
This program take one tra file and remove all unused numbers with the list of used numbers. 
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('src', help='File or folder to check all tra lines from.')
    parser.add_argument('used_numbers', help='File to find closest line for every line in infile1.')
    args = parser.parse_args()

    if os.path.isfile(args.src):
        remove_unused(args.src, args.used_numbers)
