#!/usr/bin/env python3

import argparse
import re

def split_and_replace(original_string, i, init_offset, factor, final_offset):
    rx = re.finditer(r'(\S+)', original_string)
    m_i = 0
    for match in rx:
        if m_i == i:
            try:
                start_i = match.start()
                old_x = int(original_string[match.start():match.end()])
                t = str(int((old_x + init_offset) * factor + final_offset))
                return original_string[0:start_i] + re.sub(r'(\S+)', t, original_string[start_i:], 1)
            except ValueError:
                pass
        m_i += 1
    return original_string


__desc__ = '''
This program modify coordinates in tlb file: new_x = (old_x + init_offset_x) * factor_x + final_offset_x
and the same with "y". It saves coordinates in a new_file (can be the same).   
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('in_file', help='tlb file with coordinates.')
    parser.add_argument('out_file', help='tlb file to save tlb file with modified coordinates.')
    parser.add_argument('--init_offset_x', help='', type=int, default=0)
    parser.add_argument('--init_offset_y', help='', type=int, default=0)
    parser.add_argument('--final_offset_x', help='', type=int, default=0)
    parser.add_argument('--final_offset_y', help='', type=int, default=0)
    parser.add_argument('--factor_x', help='', type=float, default=1)
    parser.add_argument('--factor_y', help='', type=float, default=1)
    args = parser.parse_args()

    outlines = []
    f_in = open(args.in_file, "r")
    lines = f_in.readlines()
    f_in.close()
    for line in lines:
        line = split_and_replace(line, 5, args.init_offset_x, args.factor_x, args.final_offset_x)
        line = split_and_replace(line, 6, args.init_offset_y, args.factor_y, args.final_offset_y)
        outlines.append(line)

    f_out = open(args.out_file, "w")
    f_out.writelines(outlines)
    f_out.close()
