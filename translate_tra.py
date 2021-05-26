#!/usr/bin/env python3

import argparse
import urllib.error

from textblob import TextBlob
from googletrans import Translator
import pycld2 as cld2
from google.cloud import translate_v2 as translate


def translate_file(infile, outfile, lang, engine):
    with open(infile, mode='r') as file:
        text = file.read()
    out_text = text

    indexes = [i for i, ltr in enumerate(text) if ltr == '~']
    pairs = list(zip(indexes[::2], indexes[1::2]))
    n_translated = 0
    n_processed = 0
    translator = Translator()
    out_text_offset = 0

    if engine == 'googlecloud':
        translate_client = translate.Client()

    try:
        for p in pairs:
            n_processed += 1
            print('processing {} out of {}'.format(n_processed, len(pairs)))
            string = text[p[0] + 1: p[1]]
            translated_string = string
            reliable, _, details = cld2.detect(string)
            if reliable and details[0][1] == 'en':
                if engine == 'googletrans':
                    translated_string = translator.translate(string, dest=lang).text
                elif engine == 'googlecloud':
                    result = translate_client.translate(string, target_language='ru')
                    translated_string = result['translatedText']
                else:
                    blob = TextBlob(string)
                    translated_string = str(blob.translate(from_lang='en', to=lang))

            if string != translated_string:
                n_translated +=1
                print('"{}" translated into "{}"'.format(string, str(translated_string)))
                translated_string = "НП: " + translated_string
                out_text = out_text[:(p[0] + 1 + out_text_offset)] + translated_string + out_text[(p[1] + out_text_offset):]
                out_text_offset += (len(translated_string) - len(string))
    except urllib.error.HTTPError:
        print('"Too Many Requests" exception, try again tomorrow. Saving what was translated...')

    with open(outfile, mode='w') as outfile:
        outfile.write(out_text)


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
    parser.add_argument('--engine', help='Select one of three translation engines: googletrans, googlecloud, textblob.',
                        required=False, default='textblob')
    args = parser.parse_args()

    out = args.out
    if not out:
        out = args.infile

    translate_file(args.infile, out, args.lang, args.engine)
