#!/usr/bin/env python3

import argparse
import urllib.error
import os
import sys
import chardet
import re

__desc__ = '''
This program takes wed and corresponding png files and convert them both to prepare them to export in EE games on infinity engine.
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile1', help='WED file')
    parser.add_argument('out_dir', help='dir to put transformed wed and png files', default="")
    args = parser.parse_args()

    
