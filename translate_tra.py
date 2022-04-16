#!/usr/bin/env python3

import argparse
import sys
import urllib.error
import chardet
import re

from textblob import TextBlob
from googletrans import Translator
import pycld2 as cld2
from google.cloud import translate_v2 as translate
from yandex.Translater import Translater
import deepl


def translate_file(infile, outfile, lang, engine, add_prefix):
    with open(infile, mode='rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)

    print("\n\nStarted processing file {} with encoding {}\n\n".format(args.infile, result['encoding']))
    with open(infile, mode='r', encoding=result['encoding']) as file:
        text = file.read()
    out_text = text

    find_delimiter_re = re.compile('@[0-9]+[\\s]*=[\\s]*(.)')
    find_string_re = re.compile('@[0-9]+[^@]*')
    find_replica_re0 = re.compile('~([^~]*)~')
    find_replica_re1 = re.compile('"([^"]*)"')

    lines = find_string_re.findall(text)
    # indexes = [i for i, ltr in enumerate(text) if ltr == '~']
    # pairs = list(zip(indexes[::2], indexes[1::2]))
    n_processed = 0
    translator = Translator()
    out_text_offset = 0

    if engine == 'googlecloud':
        translate_client = translate.Client()
    elif engine == 'yandex':
        translate_client = Translater()
        file = open('YANDEX_API_KEY', mode='r')
        yandex_key = file.read()
        translate_client.set_key(yandex_key)
        translate_client.set_to_lang(lang)
    elif engine == 'deepl':
        file = open('DEEPL_API_KEY', mode='r')
        deepl_key = file.read().rstrip()
        translator = deepl.Translator(deepl_key)

    try:
        r = True
        start_i = -1
        while True:
            r = find_string_re.search(text, start_i + 1)
            if not r:
                break
            start_i = r.start()
            end_i = r.end() - 1
            if end_i == len(text) - 1:
                end_i += 1
            n_processed += 1
            print('processing {} out of {}'.format(n_processed, len(lines)))
            line = text[start_i:end_i]
            translated_line = line
            delimiters = find_delimiter_re.findall(line)
            if len(delimiters) != 1 or (delimiters[0] != '~' and delimiters[0] != '"'):
                print("Cannot process line: \"{}\", skipping".format(line))
                continue
            if delimiters[0] == "~":
                find_replica_re = find_replica_re0
            else:
                find_replica_re = find_replica_re1

            strings = find_replica_re.findall(line)
            for string in strings:
                translated_string = ""
                if string:
                    translated_string = string
                    reliable, _, details = cld2.detect(string)
                    if details[0][1] != lang:
                        if engine == 'googletrans':
                            translated_string = translator.translate(string, dest=lang).text
                        elif engine == 'googlecloud':
                            result = translate_client.translate(string, target_language=lang)
                            translated_string = result['translatedText']
                        elif engine == 'textblob':
                            blob = TextBlob(string)
                            translated_string = str(blob.translate(from_lang=details[0][1], to=lang))
                        elif engine == 'yandex':
                            translate_client.set_text(string)
                            translated_string = translate_client.translate()
                        elif engine == 'deepl':
                            translated_string = str(translator.translate_text(string, target_lang=lang))
                        else:
                            sys.exit('Unknown engine name: {}. Use googletrans, googlecloud, textblob, yandex or deepl'.format(engine))

                if string != translated_string:
                    if add_prefix:
                        translated_string = "НП: " + translated_string
                    translated_line = translated_line.replace(string, translated_string)

            if line != translated_line:
                print('"{}" translated into "{}"'.format(line, translated_line))
                out_text = out_text[:(start_i + out_text_offset)] + translated_line + out_text[(end_i + out_text_offset):]
                out_text_offset += (len(translated_line) - len(line))

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
string, prefix 'НП: ' can be added added to mark that this string needs correction.
By default the language to translate is Russian (ru). Also by default the output file is the same as input file, 
so the original file is exchanged with the translated one.
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='Input filename.')
    parser.add_argument('--out', help='Output filename.', required=False)
    parser.add_argument('--lang', help='Language to translate to.', required=False, default='ru')
    parser.add_argument('--engine', help='Select one of the next translation engines: googletrans, googlecloud, textblob, yandex, deepl',
                        required=False, default='textblob')
    parser.add_argument('--add-prefix', required=False, dest='add_prefix', action='store_true')
    parser.add_argument('--no-add-prefix', required=False, dest='add_prefix', action='store_false')
    parser.set_defaults(add_prefix=True)
    args = parser.parse_args()

    out = args.out
    if not out:
        out = args.infile

    translate_file(args.infile, out, args.lang, args.engine, args.add_prefix)
