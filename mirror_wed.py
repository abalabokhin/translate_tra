#!/usr/bin/env python3

import argparse
import os
import sys
from functools import cmp_to_key


__desc__ = '''
This program takes wed and mirror all the tiles inside horizontally (it doesn't touch polygon walls, etc, so it rather 
good to fix already mirrored WED - they are shown in EE with glitches, than for mirroring existing ones).
'''

if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile1', help='WED file')
    parser.add_argument('outdir', help='dir to put transformed WED file', default=".")
    args = parser.parse_args()
    style = args.style

    print("Processing file {}".format(args.infile1))
    wed_in = open(args.infile1, mode="rb")
    wed_data = wed_in.read()
    filepath_no_ext = os.path.splitext(args.infile1)[0]
    basename = os.path.basename(filepath_no_ext).upper()

    n_doors = int.from_bytes(wed_data[0xc:0xc + 4], "little")
    n_overlays = int.from_bytes(wed_data[0x8:0x8 + 4], "little")
    overlays_offset = int.from_bytes(wed_data[0x10:0x10 + 4], "little")
    doors_offset = int.from_bytes(wed_data[0x18:0x18 + 4], "little")
    door_tile_cell_offset = int.from_bytes(wed_data[0x1c:0x1c + 4], "little")

    overlay_found = False
    for overlay_i in range(n_overlays):
        overlay_offset = overlays_offset + overlay_i * 0x18
        overlay_w = int.from_bytes(wed_data[overlay_offset:overlay_offset + 2], "little")
        overlay_h = int.from_bytes(wed_data[overlay_offset + 0x2:overlay_offset + 0x2 + 2], "little")
        tileset_name = wed_data[overlay_offset + 0x4:overlay_offset + 0x4 + 8].split(b'\0')[0].decode().upper()
        tilemap_offset = int.from_bytes(wed_data[overlay_offset + 0x10:overlay_offset + 0x10 + 4], "little")
        tile_index_lookup_offset = int.from_bytes(wed_data[overlay_offset + 0x14:overlay_offset + 0x14 + 4], "little")
        if tileset_name == basename:
            overlay_found = True
            break

    if not overlay_found:
        sys.exit("Cannot find appropriate overlay name in WED file")

    output_wed_data = bytearray(wed_data)
    bytes_negative_one = (-1).to_bytes(2, 'little', signed=True)

    for tile_i in range(overlay_w * overlay_h):
        tilemap_offset_i = tilemap_offset + tile_i * 0xa
        tile_start_i = int.from_bytes(wed_data[tilemap_offset_i:tilemap_offset_i + 2], "little")
        tile_count = int.from_bytes(wed_data[tilemap_offset_i + 0x2:tilemap_offset_i + 0x2 + 2], "little")
        second_tile_offset = tilemap_offset_i + 0x4
        second_tile = int.from_bytes(wed_data[second_tile_offset:second_tile_offset + 2], "little", signed=True)
        is_overlay = not (int.from_bytes(wed_data[tilemap_offset_i + 0x6:tilemap_offset_i + 0x6 + 1], "little", signed=True) == 0)

        for tile_ii in range(tile_count):
            tile_ii_offset = tile_index_lookup_offset + (tile_start_i + tile_ii) * 2
            first_tile = int.from_bytes(wed_data[tile_ii_offset:tile_ii_offset + 2], "little")
            tile_x = first_tile % overlay_w
            new_tile_x = overlay_w - 1 - tile_x
            new_first_tile = first_tile - tile_x + new_tile_x
            new_first_tile_bytes = new_first_tile.to_bytes(2, 'little')
            output_wed_data[tile_ii_offset] = new_first_tile_bytes[0]
            output_wed_data[tile_ii_offset + 1] = new_first_tile_bytes[1]

        if second_tile >= 0:
            tile_x = second_tile % overlay_w
            new_tile_x = overlay_w - 1 - tile_x
            new_second_tile = second_tile - tile_x + new_tile_x
            new_second_tile_bytes = new_second_tile.to_bytes(2, 'little')
            output_wed_data[second_tile_offset] = new_second_tile_bytes[0]
            output_wed_data[second_tile_offset + 1] = new_second_tile_bytes[1]

    filepath_out_wed = os.path.join(args.outdir, basename + ".WED")
    wed_out = open(filepath_out_wed, mode="wb")
    wed_out.write(output_wed_data)
