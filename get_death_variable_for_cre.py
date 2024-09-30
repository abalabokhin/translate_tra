#!/usr/bin/env python3

import argparse

def print_death_variable(infile):
    cre_in = open(infile, mode="rb")
    cre_data = cre_in.read()

    dv_bytes = cre_data[0x280:0x280 + 32]
    print(infile, dv_bytes.decode('latin-1'))


__desc__ = '''
This program print the death variable for CRE file
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='Input CRE filename')
    args = parser.parse_args()
    print_death_variable(args.infile)
