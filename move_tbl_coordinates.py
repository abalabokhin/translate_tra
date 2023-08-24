#!/usr/bin/env python3

import argparse

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
        tokens = line.split(" ")
        out_tokens = []
        non_empty_tokens = 0
        for t in tokens:
            if t:
                non_empty_tokens += 1
                if non_empty_tokens == 6:
                    try:
                        old_x = int(t)
                        t = str(int((old_x + args.init_offset_x) * args.factor_x + args.final_offset_x))
                    except ValueError:
                        pass
                if non_empty_tokens == 7:
                    try:
                        old_y = int(t)
                        t = str(int((old_y + args.init_offset_y) * args.factor_y + args.final_offset_y))
                    except ValueError:
                        pass
            out_tokens.append(t)
        line = " ".join(out_tokens)
        outlines.append(line)

    f_out = open(args.out_file, "w")
    f_out.writelines(outlines)
    f_out.close()
