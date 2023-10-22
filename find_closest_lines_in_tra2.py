#!/usr/bin/env python3

import argparse
import os
import sys
import chardet
import re
from Levenshtein import distance as levenshtein_distance
from nltk import tokenize


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
        result[numbers[0]] = fixed_replicas

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


def all_split_on_sentences_combinations(line):
    result = [[line]]
    parts = tokenize.sent_tokenize(line)
    for i in range(1, len(parts)):
        for j in range(i, len(parts)):
            combination = [parts[:i], parts[i:j], parts[j:]]
            combination[:] = [x for x in combination if x]
            res1 = []
            for c in list(combination):
                res1.append(" ".join(c))
            result.append(res1)
    return result


def find_closest_in_dict(src_string, dst_dict):
    min_d = 1000000
    dst_n = -1
    for n1 in dst_dict.keys():
        dst_string = dst_dict[n1][0]
        d = levenshtein_distance(src_string, dst_string)
        if d < min_d:
            min_d = d
            dst_n = n1
        if min_d == 0:
            break
    return dst_n, min_d


# l1 - english
def find_closest_lines(src_files, src_files_l2, dict_l1_file, dict_l2_file, map_file):
    dict_l1, _ = read_file1(dict_l1_file)
    dict_l2, _ = read_file1(dict_l2_file)
    if map_file:
        map_out_file = open(map_file, "a")

    for src_file, src_file_l2 in zip(src_files, src_files_l2):
        print("processing {}".format(src_file))
        src_l2, _ = read_file1(src_file_l2)
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
            number = numbers[0]
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
            if not string.startswith('NP:'):
                continue
            all_combinations = all_split_on_sentences_combinations(src_l2[number][0])
            best_comb_ns = []
            min_d = 100000
            for combination in all_combinations:
                closest_parts = []
                comb_ns = []
                for part in combination:
                    n, _ = find_closest_in_dict(part, dict_l2)
                    closest_parts.append(dict_l2[n][0])
                    comb_ns.append(n)
                comb = " ".join(closest_parts)
                d = levenshtein_distance(comb, src_l2[number][0])
                if d < min_d:
                    min_d = d
                    best_comb_ns = comb_ns

            good_line = (min_d <= len(src_l2[number][0]) / 10)
            if not good_line:
                continue

            if map_out_file:
                map_out_file.write("{} {} {} {} {}\n".format(basename, number, best_comb_ns, min_d, good_line))
            best_comb_l1 = []
            for n in best_comb_ns:
                best_comb_l1.append(dict_l1[n][0])
            l1_new_line = " ".join(best_comb_l1)
            changed_line = line.replace(string, l1_new_line)

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
    parser.add_argument('src_l1', help='File or folder to check tra lines from with NP: prefix.')
    parser.add_argument('src_l2', help='File or folder of the same but with other language, good one, '
                                               'all the replicas from here are search')
    parser.add_argument('--dict_l1', help='File to take replicas for translation if the distance is small enough', required=True)
    parser.add_argument('--dict_l2', help='File to take replicas for translation if the distance is small enough',
                        required=True)
    parser.add_argument('--map_file', help='file to show mapping lines and distance', required=False)
    args = parser.parse_args()

    if os.path.isfile(args.src_l1):
        find_closest_lines({args.src_l1}, {args.src_l2}, args.dict_l1, args.dict_l2, args.map_file)
    if os.path.isdir(args.src_l1):
        filenames = []
        filenames_l2 = []
        for path in os.listdir(args.src_l1):
            if 'setup' in path:
                continue
            full_path = os.path.join(args.src_l1, path)
            full_path_l2 = os.path.join(args.src_l2, path)
            if os.path.isfile(full_path):
                filenames.append(full_path)
                filenames_l2.append(full_path_l2)
        find_closest_lines(filenames, filenames_l2, args.dict_l1, args.dict_l2, args.map_file)


