#!/usr/bin/env python3

import argparse
import urllib.error
import os
import sys
import chardet
import re
from PIL import Image


def bounding_box(points):
    x_coordinates, y_coordinates = zip(*points)
    return [(min(x_coordinates), min(y_coordinates)), (max(x_coordinates), max(y_coordinates))]


def find_groups(elements):
    def dfs(x, y, group):
        if (x, y) in visited:
            return
        visited.add((x, y))
        group.append([x, y])

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = x + dx, y + dy
                if (nx, ny) in elements_set and (nx, ny) not in visited:
                    dfs(nx, ny, group)

    elements_set = set(map(tuple, elements))
    visited = set()
    groups = []

    for x, y in elements_set:
        if (x, y) not in visited:
            current_group = []
            dfs(x, y, current_group)
            groups.append(current_group)

    return groups

__desc__ = '''
This program takes wed and corresponding png files and convert them both to prepare them to export in EE games on infinity engine.
'''

if __name__ == '__main__':
    # still don't know what to do with fireplaces
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile1', help='WED file')
    parser.add_argument('out_dir', help='dir to put transformed wed and png files', default="")
    args = parser.parse_args()

    wed_in = open(args.infile1, mode="rb")
    wed_data = wed_in.read()
    filepath_no_ext = os.path.splitext(args.infile1)[0]
    png_filename = filepath_no_ext + ".PNG"
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

    print(overlay_w, overlay_h)

    tile_map = {}
    for tile_i in range(overlay_w * overlay_h):
        tilemap_offset_i = tilemap_offset + tile_i * 0xa
        tile_start_i = int.from_bytes(wed_data[tilemap_offset_i:tilemap_offset_i + 2], "little")
        tile_count = int.from_bytes(wed_data[tilemap_offset_i + 0x2:tilemap_offset_i + 0x2 + 2], "little")
        second_tile_offset = tilemap_offset_i + 0x4
        second_tile = int.from_bytes(wed_data[second_tile_offset:second_tile_offset + 2], "little", signed=True)
        if second_tile < 0:
            continue

        for tile_ii in range(tile_count):
            tile_ii_offset = tile_index_lookup_offset + (tile_start_i + tile_ii) * 2
            first_tile = int.from_bytes(wed_data[tile_ii_offset:tile_ii_offset + 2], "little")
            tile_map[first_tile] = [second_tile, second_tile_offset]

    im = Image.open(png_filename)

    elements = []
    for k in tile_map.keys():
        elements.append([k % overlay_w, k // overlay_w])
    print(elements)
    groups = find_groups(elements)

    for g_i in range(len(groups)):
        g = groups[g_i]
        bb = bounding_box(g)
        bb_ex = [[max(bb[0][0] - 1, 0), max(bb[0][1] - 1, 0)], [min(bb[1][0] + 1, overlay_w - 1), min(bb[1][1] + 1, overlay_h - 1)]]
        rect = (bb_ex[0][0] * 64, bb_ex[0][1] * 64, (bb_ex[1][0] + 1) * 64, (bb_ex[1][1] + 1) * 64)
        print(bb, bb_ex, rect)
        im.crop((rect)).save(str(g_i) + ".png")


    # for door_i in range(n_doors):
    #
    #     door_offset = doors_offset + door_i * 0x1a
    #     first_door_tile_cell_i = int.from_bytes(wed_data[door_offset + 0xa:door_offset + 0xa + 2], "little")
    #     n_door_tile_cell = int.from_bytes(wed_data[door_offset + 0xc:door_offset + 0xc + 2], "little")
    #     door_tile_indexes = []
    #     for door_tile_i in range(n_door_tile_cell):
    #         tile_offset = door_tile_cell_offset + 2 * (first_door_tile_cell_i + door_tile_i)
    #         door_tile_indexes.append(int.from_bytes(wed_data[tile_offset:tile_offset + 2], "little"))
    #
    #     door_elements = []
    #     for k in door_tile_indexes:
    #         door_elements.append([k % overlay_w, k // overlay_w])
    #     print(door_elements)





