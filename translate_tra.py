#!/usr/bin/env python3

import argparse
import time
import urllib.error

from textblob import TextBlob

__desc__ = '''
This program automatically translates (using google translate) one *.tra file.
The file should have even number of '~' and every pair of '~' should have a text to translate.
E.g:
 @1    = ~This needs to be translated~
 @4    = ~This also needs to be translated~
It is supposed that after automatic translation manual correction should be done, so to every translated 
string, prefix 'NC: ' is added to mark that this string needs correction.
By default the language to translate is Russian (ru). Also by default the output file is the same as input file, 
so the original file is exchanged with the translated one.
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='Input filename.')
    parser.add_argument('--out', help='Output filename.', required=False)
    parser.add_argument('--lang', help='Language to translate to.', required=False, default='ru')
    args = parser.parse_args()

    outfile = args.out
    infile = args.infile
    if not outfile:
        outfile = infile

    with open(infile, mode='r') as file:
        text = file.read()
    out_text = text

    indexes = [i for i, ltr in enumerate(text) if ltr == '~']
    pairs = list(zip(indexes[::2], indexes[1::2]))
    n_translated = 0
    n_processed = 0
    try:
        for p in pairs:
            n_processed += 1
            print('processing {} out of {}'.format(n_processed, len(pairs)))
            time.sleep(1)
            string = text[p[0] + 1: p[1]]
            blob = TextBlob(string)
            if blob.detect_language() == 'en':
                time.sleep(1)
                n_translated += 1
                translated_string = blob.translate(from_lang='en', to=args.lang)
                print('"{}" translated into "{}"'.format(string, str(translated_string)))
                out_text.replace(string, "NC: " + translated_string, 1)
    except urllib.error.HTTPError:
        print('"Too Many Requests" exception, try again tomorrow. Saving what was translated...')

    with open(outfile, mode='w') as outfile:
        outfile.write(out_text)
