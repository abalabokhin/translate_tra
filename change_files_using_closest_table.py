#!/usr/bin/env python3

import argparse
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
    find_replica_re2 = re.compile('%([^%]*)%')
    find_sound = re.compile('\\[[^\\]]*\\]')

    result = dict()
    sound_result = dict()
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
        result[int(numbers[0])] = fixed_replicas

        for r in replicas:
            line.replace(r, '')
        sounds = find_sound.findall(line)
        if len(sounds) > 0:
            sound_result[numbers[0]] = sounds

    return result, sound_result


def upper_case_map(strings):
    result = dict()
    for s in strings:
        result[s.upper()] = s
    return result


def read_map_file(map_filename):
    #filename to line number to replicas, len and distance
    result = {}
    parse_line_re = re.compile('([^ ]+) ([0-9]+) \[([^\]]*)\] ([0-9]+) ([0-9]+)')
    with open(map_filename, mode='r') as file:
        lines = file.readlines()

    for l in lines:
        sr = parse_line_re.search(l)
        if not sr:
            print("bad line in map file", l)
            sys.exit()
        filename = sr.group(1)
        replica_n = int(sr.group(2))
        close_replicas = sr.group(3)
        distance = int(sr.group(4))
        orig_len = int(sr.group(5))
        tt = close_replicas.split(",")
        if not tt:
            print("bad line in map file", l)
            sys.exit()
        close_replicas_numbers = []
        for t in tt:
            t = t.strip()
            close_replicas_numbers.append(int(t[1:-1]))
        if filename not in result:
            result[filename] = {}
        result[filename][replica_n] = (close_replicas_numbers, distance, orig_len)
    return result


# l1 - english
def replace_closest_lines(src_files, dict_l1_file, map_file):
    map_info = read_map_file(map_file)
    dict_l1, _ = read_file1(dict_l1_file)

    for src_file in src_files:
        print("processing {}".format(src_file))
        src_l2, _ = read_file1(src_file)
        basename = os.path.basename(src_file)

        with open(src_file, mode='r') as file:
            text = file.read()
        out_text = text

        find_number_re = re.compile('@([0-9]+)')
        find_delimiter_re = re.compile('@[0-9]+[\\s]*=[\\s]*(.)')
        find_string_re = re.compile('@[0-9]+[^@]*')
        find_replica_re0 = re.compile('~([^~]*)~')
        find_replica_re1 = re.compile('"([^"]*)"')
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
            line = text[start_i:end_i]
            numbers = find_number_re.findall(line)
            number = int(numbers[0])
            delimiters = find_delimiter_re.findall(line)
            if len(delimiters) != 1 or (delimiters[0] != '~' and delimiters[0] != '"'):
                print("Cannot process line: \"{}\", skipping".format(line))
                continue
            if delimiters[0] == "~":
                find_replica_re = find_replica_re0
            else:
                find_replica_re = find_replica_re1

            strings = find_replica_re.findall(line)
            if not strings:
                continue
            string = strings[0]
            if basename not in map_info or number not in map_info[basename]:
                print('file and/or number not in mapping table', basename, number)
                sys.exit()
            info = map_info[basename][number]
            close_replicas = info[0]
            distance = info[1]
            orig_len = info[2]

            good_line = (distance <= orig_len / 20)
            best_comb_l1 = []
            for n in close_replicas:
                if n in dict_l1:
                    best_comb_l1.append(dict_l1[n][0])
            l1_new_line = " ".join(best_comb_l1)
            if good_line:
                changed_line = line.replace(string, l1_new_line)
            else:
                changed_line = line + '/*' + l1_new_line + '*/'

            if line != changed_line:
                out_text = out_text[:(start_i + out_text_offset)] + changed_line + out_text[
                                                                                      (end_i + out_text_offset):]
                out_text_offset += (len(changed_line) - len(line))

        with open(src_file, mode='w') as outfile:
            outfile.write(out_text)


__desc__ = '''
This program take one tra file and find all the closest lines (based on Levenshtein distance) in another tra file. 
It is not general, but it should start with almost translated files and search only replicas starting with NP:
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('src_l1', help='File or folder to check tra lines from.')
    parser.add_argument('--dict_l1', help='File to take replicas for translation if the distance is small enough', required=True)
    parser.add_argument('--map_file', help='file to get mapping lines and distance', required=True)
    args = parser.parse_args()

    if os.path.isfile(args.src_l1):
        replace_closest_lines({args.src_l1}, args.dict_l1, args.map_file)
    if os.path.isdir(args.src_l1):
        filenames = []
        for path in os.listdir(args.src_l1):
            full_path = os.path.join(args.src_l1, path)
            if os.path.isfile(full_path):
                filenames.append(full_path)
        replace_closest_lines(filenames, args.dict_l1, args.map_file)


