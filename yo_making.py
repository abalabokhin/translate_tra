#!/usr/bin/env python3

import argparse
import re
import click

def read_dict(dict_file):
    dictionary = {}
    with open(dict_file, mode='r') as file:
        text = file.read()
        for a in text.split():
            b = a.replace('ё', 'е')
            dictionary[b] = a
    return dictionary

def update_file(infile, outfile):
    with open(infile, mode='r') as file:
        main_dict = read_dict("russian_yo_words.txt")
        both_dict = read_dict("russian_yo_words_both.txt")

        with open(infile, mode='r') as file:
            text = file.read()
            regex = re.compile(r'\w+')
            match = regex.search(text)
            while match:
                start_p = match.start(0)
                end_p = match.end(0)
                w = match.group(0)
                w_lower = w.lower()
                upper_case = True
                if w == w_lower:
                    upper_case = False
                if w_lower in main_dict:
                    new_w = main_dict[w_lower]
                    if upper_case:
                        new_w = new_w[0].upper() + new_w[1:]
                    if w_lower not in both_dict:
                        text = text[:start_p] + new_w + text[end_p:]
                    else:
                        print('replace "{0}" with "{1}" in "{2}": (y/n)?"'.format(w, new_w, text[start_p-10 : end_p+20]))
                        c = click.getchar()
                        print(c)
                        if c == 'y':
                            text = text[:start_p] + new_w + text[end_p:]

                match = regex.search(text, end_p)
            with open(outfile, mode='w') as outf:
                outf.write(text)

__desc__ = '''
This program automatically change all russian letters "е" to be "ё" in words in a file, if such words exists
in dictionary. If there is an unclear case, eg: "все"-"всё" - it will ask from user.
The dictionary file is in russian_yo_words.txt file.
The dictionary file for word that can be read both ways is in russian_yo_words_both.txt file.
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='Input filename.')
    parser.add_argument('--out', help='Output filename.', required=False)
    args = parser.parse_args()

    out = args.out
    if not out:
        out = args.infile

    update_file(args.infile, out)
