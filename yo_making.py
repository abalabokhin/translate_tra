#!/usr/bin/env python3

import argparse
import re

__desc__ = '''
This program automatically change all russian letters "е" to be "ё" in words in a file, if such words exists
in dictionary. If there is an unclear case, eg: "все"-"всё" - it will ask from user.
The dioctionary file is in russian_yo_words.txt files.'''

def update_file(infile, outfile):
    dictionary = {}
    with open("russian_yo_words_short.txt", mode='r') as file:
        text = file.read()
        for a in text.split():
            if a == 'всё':
                print(a, a.replace('ё', 'e'))
            dictionary[a.replace('ё', 'e')] = a
    print(dictionary)
    print(dictionary['вселен'])
    with open(infile, mode='r') as file:
   #     text = file.read()
        text = "Щелкнут, Привет, меня зовут андр'ей и все-все все как щас щeлкнут!"
        regex = r'\w+'
        words = re.findall(regex, text)
        for w in words:
            if w in dictionary:
                print(w)




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='Input filename.')
    parser.add_argument('--out', help='Output filename.', required=True)
    args = parser.parse_args()

    out = args.out
    if not out:
        out = args.infile

    update_file(args.infile, out)
