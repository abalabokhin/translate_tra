#!/usr/bin/env python3

import argparse
import os
import sys
from functools import cmp_to_key
from PIL import Image, ImageOps

__desc__ = '''
This program performs a specific image manipulation by merging parts of a tile
from a source image into a tile of a destination image, using another tile from
the destination image as a transparency mask. The tile indices are hardcoded.
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('dest_file', help='Destination PNG file (will be modified)')
    parser.add_argument('source_file', help='Source PNG file')
    parser.add_argument('output_file', help='Output PNG file path')

    args = parser.parse_args()

    print(args.dest_file)
    dest_image = Image.open(args.dest_file)
    source_image = Image.open(args.source_file)

    # The script assumes images are composed of 64x64 tiles.
    tile_width = 64
    tiles_per_row = dest_image.width / tile_width

    # Hardcoded tile indices
    mask_tile_index = 1537  # This tile from dest_file provides the transparency mask.
    dest_tile_index = 3372  # This tile from dest_file will be modified.

    # Calculate coordinates for the mask tile
    mask_tile_x = mask_tile_index % tiles_per_row
    mask_tile_y = mask_tile_index // tiles_per_row

    # Calculate coordinates for the destination tile
    dest_tile_x = dest_tile_index % tiles_per_row
    dest_tile_y = dest_tile_index // tiles_per_row

    print(tiles_per_row, mask_tile_x, mask_tile_y)

    # Crop the tiles from the images.
    # The mask tile is from the destination image.
    mask_tile = dest_image.crop((mask_tile_x * tile_width, mask_tile_y * tile_width, (mask_tile_x + 1) * tile_width, (mask_tile_y + 1) * tile_width))

    # The destination tile is also from the destination image, but a different one.
    dest_tile = dest_image.crop((dest_tile_x * tile_width, dest_tile_y * tile_width, (dest_tile_x + 1) * tile_width, (dest_tile_y + 1) * tile_width))

    # The source tile is from the source image, at the same location as the mask tile.
    source_tile = source_image.crop((mask_tile_x * tile_width, mask_tile_y * tile_width, (mask_tile_x + 1) * tile_width, (mask_tile_y + 1) * tile_width))

    # For debugging, save the tiles before modification
    # mask_tile.save("mask_tile.png")
    # dest_tile.save("dest_tile_before.png")
    # source_tile.save("source_tile.png")

    # For each pixel, if the mask_tile is transparent, copy the pixel from
    # the source_tile to the dest_tile.
    for x in range(tile_width):
        for y in range(tile_width):
            if mask_tile.getpixel((x, y)) == (0, 0, 0, 0):
                dest_tile.putpixel((x, y), source_tile.getpixel((x, y)))

    # Paste the modified tile back into the destination image.
    # The paste location is the top-left corner of the destination tile's area.
    paste_coord = (int(dest_tile_x) * tile_width, int(dest_tile_y) * tile_width)
    dest_image.paste(dest_tile, paste_coord)
    dest_image.save(args.output_file)
    # For debugging, save the modified destination tile
    # dest_tile.save("dest_tile_after.png")

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
