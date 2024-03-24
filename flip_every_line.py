#!/usr/bin/env python3

import argparse
import os
import sys
from functools import cmp_to_key
import numpy as np
from PIL import Image, ImageOps

__desc__ = '''
This program takes png file file and flip every column (64 px width)
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile1', help='PNG in file')
    parser.add_argument('outfile1', help='PNG out file')

    args = parser.parse_args()
    im = Image.open(args.infile1)

    image_w, image_h = im.size
    output_image = Image.new(mode="RGBA", size=im.size)
    image_w //= 64
    image_h
    for x in range(image_w):
        mirror_img = ImageOps.mirror(im.crop((x * 64, 0, (x + 1) * 64, image_h)))
        output_image.paste(mirror_img, (x * 64, 0))

    output_image.save(args.outfile1)
