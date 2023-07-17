#!/usr/bin/env python3

import argparse
import re


def clear_content(content):
    pos1 = content.find('"')
    pos2 = content.rfind('"')
    result = content[pos1+1:pos2]
    result1 = re.sub("<StartCheck>.*</Start>", '', result)
    return result1.strip()


def nwn_file_to_tra(infile, outfile):
    f = open(infile, "r")
    f1 = open(outfile, "w")
    lines = f.readlines()
    number = -1
    content = ""
    inside_content = False
    for line in lines:
        m = re.search("Element #([0-9]*)", line)
        if m:
            content = clear_content(content)
            if number >= 0 and len(content) > 0:
                f1.write("@{} = ~{}~\n".format(number, content))
            number = int(m.group(1))
            inside_content = False
        m = re.search('.*Content: (.*)', line)

        if m:
            inside_content = True
            content = m.group(1)
        elif inside_content:
            content += line



__desc__ = '''
This program automatically translates (using google translate) one *.tra file.
The file should have even number of '~' and every pair of '~' should have a text to translate.
E.g:
 @1    = ~This needs to be translated~
 @4    = ~This also needs to be translated~
It is supposed that after automatic translation manual correction should be done, so to every translated 
string, prefix 'НП: ' can be added added to mark that this string needs correction.
By default the language to translate is Russian (ru). Also by default the output file is the same as input file, 
so the original file is exchanged with the translated one.
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='Input filename.')
    parser.add_argument('--out', help='Output filename.', required=False)
    args = parser.parse_args()

    out = args.out
    if not out:
        out = args.infile + ".tra"

    nwn_file_to_tra(args.infile, out)
