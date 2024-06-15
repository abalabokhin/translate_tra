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
    parser.add_argument('file1', help='PNG in file')
    parser.add_argument('file2', help='PNG in file')
    parser.add_argument('file_out', help='PNG out file')

    args = parser.parse_args()

    print(args.file1)
    im1 = Image.open(args.file1)
    im2 = Image.open(args.file2)

    n_x_tiles = im1.width / 64
    tile_i = 1537
    tile_i_2 = 3372
    tile_x_i = tile_i % n_x_tiles
    tile_y_i = tile_i // n_x_tiles
    tile_x_i_2 = tile_i_2 % n_x_tiles
    tile_y_i_2 = tile_i_2 // n_x_tiles
    print(n_x_tiles, tile_x_i, tile_y_i)
    tile_1 = im1.crop((tile_x_i * 64, tile_y_i * 64, (tile_x_i + 1) * 64, (tile_y_i + 1) * 64))
    tile_1_2 = im1.crop((tile_x_i_2 * 64, tile_y_i_2 * 64, (tile_x_i_2 + 1) * 64, (tile_y_i_2 + 1) * 64))
    tile_2 = im2.crop((tile_x_i * 64, tile_y_i * 64, (tile_x_i + 1) * 64, (tile_y_i + 1) * 64))

    # tile_1.save("1.png")
    # tile_1_2.save("1_2.png")
    # tile_2.save("2.png")

    for x in range(64):
        for y in range(64):
            if tile_1.getpixel((x, y)) == (0, 0, 0, 0):
                tile_1_2.putpixel((x, y), tile_2.getpixel((x, y)))

    im1.paste(tile_1_2, (int(tile_x_i_2) * 64, int(tile_y_i_2) * 64))
    im1.save(args.file_out)
    # tile_1_2.save("1_2_m.png")

    # tile_1.save("1.png")
    # tile_1_2.save("1_2.png")
    # tile_2.save("2.png")

    #
    # first_tile = input_im.crop(first_tile_rect)
    # second_tile = input_im.crop(second_tile_rect)
    # output_im.paste(second_tile, (first_tile_rect[0], first_tile_rect[1]))
    # for x in range(64):
    #     for y in range(64):
    #         if second_tile.getpixel((x, y)) != (0, 0, 0, 0):
    #             first_tile.putpixel((x, y), (0, 0, 0, 0))
    # output_im.paste(first_tile, out_second_tile_offset)


    sys.exit()

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
