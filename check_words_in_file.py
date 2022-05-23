#!/usr/bin/env python3

import argparse
import re
import csv

def search_file(infile, csvfile):
    with open(infile, 'r') as file:
        text = file.read().lower()
        with open(csvfile, newline = '') as csvfile:
            csvreader = csv.reader(csvfile)
            for row in csvreader:
                a = row[0].lower()
                if a:
                    pos = text.find(a)
                    if pos >= 0:
                        pos0 = text.rfind('@', 0, pos)
                        pos1 = text.find('=', pos0)
                        print(row[0], text[pos0:pos1].strip())


__desc__ = '''
This program search for the first occurence of expressions from a first column of CSV file in bigger file
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='Input filename.')
    parser.add_argument('--csv', help='SCV file', required=True)
    args = parser.parse_args()

    search_file(args.infile, args.csv)
