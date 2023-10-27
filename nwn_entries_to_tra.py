#!/usr/bin/env python3

import argparse
import re


def clear_content(content):
    pos1 = content.find('"')
    pos2 = content.rfind('"')
    result = content[pos1+1:pos2]
    result = re.sub("<CUSTOM[^<]*>", '', result)
    result = re.sub("<Delete>", '', result)
    result = re.sub("<StartCheck>.*</Start>", '', result)
    result = re.sub("StartCheck>.*</Start", '', result)
    result = re.sub("<StartAction>([^<]*)</Start>", '\\1', result)
    result = re.sub("<StartAction>([^<]*)<StartAction>", '\\1', result)
    result = re.sub("<StartHighlight>([^<]*)</Start>", '\\1', result)

    result = re.sub("<[Bb]itch/[Bb]astard>", 'GIRLBOY>', result)
    result = re.sub("<[Bb]oy/[Gg]irl>", '<GIRLBOY>', result)
    result = re.sub("<[Ll]ad/[Ll]ass>", '<GIRLBOY>', result)

    result = re.sub("<[Bb]rother/[Ss]ister>", '<BROTHERSISTER>', result)

    result = re.sub("<[Rr]ace>", '<RACE>', result)
    result = re.sub("<class>", '<RACE>', result)

    result = re.sub("<day/night>", '<DAYNIGHT>', result)
    result = re.sub("<quarterday>", '<DAYNIGHTALL>', result)
    result = re.sub("<FirstName>", '<CHARNAME>', result)
    result = re.sub("<FullName>", '<CHARNAME>', result)
    result = re.sub("<LastName>", '<CHARNAME>', result)
    result = re.sub("<[Hh]e/[Ss]he>", '<HESHE>', result)
    result = re.sub("<[Hh]im/[Hh]er>", '<HIMHER>', result)
    result = re.sub("<[Hh]is/[Hh]er(s|)>", '<HISHER>', result)

    result = re.sub("<[Ll]ady/[Ll]ord>", '<LADYLORD>', result)
    result = re.sub("<[Ll]ord/[Ll]ady>", '<LADYLORD>', result)
    result = re.sub("<[Mm]aster/[Mm]istress>", '<LADYLORD>', result)

    result = re.sub("<[Mm]ale/[Ff]emale>", '<MALEFEMALE>', result)
    result = re.sub("<[Mm]an/[Ww]oman>", '<MANWOMAN>', result)

    result = re.sub("<[Ss]ir/[Mm]adam>", '<SIRMAAM>', result)
    result = re.sub("<[Mm]ister/[Mm]iss(s|)us>", '<SIRMAAM>', result)

    result = result.strip()
    return result


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
