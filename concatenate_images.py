#!/usr/bin/env python3

import argparse
import os
import sys
from functools import cmp_to_key
from PIL import Image, ImageOps

__desc__ = '''
This program takes groups of png, concatenate them and put them into outfolder 
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('inmask1', help='PNG in file')
    parser.add_argument('inmask2', help='PNG in file')
    parser.add_argument('outfolder', help='out folder')

    args = parser.parse_args()
    for i in range(34):
        path1, basename1 = os.path.split(args.inmask1)
        im1 = os.path.join(path1, basename1 + str(i).zfill(5) + ".PNG")
        path2, basename2 = os.path.split(args.inmask2)
        im2 = os.path.join(path2, basename2 + str(i).zfill(5) + ".PNG")
        out = os.path.join(args.outfolder, basename1 + str(i).zfill(5) + ".PNG")
        print(im1, im2, out)
        im1 = Image.open(im1)
        im2 = Image.open(im2)
        output_image = Image.new(mode="RGBA", size=(im1.width, im1.height + im2.height))
        output_image.paste(im1, (0, 0))
        output_image.paste(im2, (0, im1.height))
        output_image.save(out)

    # im = Image.open(args.infile1)
    #
    # image_w, image_h = im.size
    # output_image = Image.new(mode="RGBA", size=im.size)
    # image_w //= 64
    # image_h
    # for x in range(image_w):
    #     mirror_img = ImageOps.mirror(im.crop((x * 64, 0, (x + 1) * 64, image_h)))
    #     output_image.paste(mirror_img, (x * 64, 0))
    #
    # output_image.save(args.outfile1)
