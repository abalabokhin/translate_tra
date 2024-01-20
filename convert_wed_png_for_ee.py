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

    wed_in = open(args.infile1, mode="rb")
    wed_data = wed_in.read()
    png_filename = os.path.splitext(args.infile1)[0] + ".PNG"
    png_in = open(png_filename, mode="rb")

    n_doors = int.from_bytes(wed_data[0xc:0xc + 4], "little")
    n_overlays = int.from_bytes(wed_data[0x8:0x8 + 4], "little")
    overlays_offset = int.from_bytes(wed_data[0x10:0x10 + 4], "little")
    doors_offset = int.from_bytes(wed_data[0x18:0x18 + 4], "little")
    door_tile_cell_offset = int.from_bytes(wed_data[0x1c:0x1c + 4], "little")

    for door_i in range(n_doors):
        door_offset = doors_offset + door_i * 0xa1
        first_door_tile_cell_i = int.from_bytes(wed_data[door_offset + 0xa:door_offset + 0xa + 2], "little")
        n_door_tile_cell = int.from_bytes(wed_data[door_offset + 0xc:door_offset + 0xc + 2], "little")
        print(n_door_tile_cell, first_door_tile_cell_i)
        door_tile_indexes = []
        for door_tile_i in range(n_door_tile_cell):
            tile_offset = door_tile_cell_offset + 2 * (first_door_tile_cell_i + door_tile_i)
            door_tile_indexes.append(int.from_bytes(wed_data[tile_offset:tile_offset + 2], "little"))

        print(door_tile_indexes)



