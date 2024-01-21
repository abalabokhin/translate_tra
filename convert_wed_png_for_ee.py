#!/usr/bin/env python3

import argparse
import os
import sys
from functools import cmp_to_key
import numpy as np
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
    parser.add_argument('outdir', help='dir to put transformed wed and png files', default=".")
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
    image_w, image_h = im.size
    image_w //= 64
    image_h //= 64


    elements = []
    all_secondary_tile = []
    for k in tile_map.keys():
        elements.append([k % overlay_w, k // overlay_w])
        all_secondary_tile.append(tile_map[k][0])

    # todo: implement sanity check
    groups = find_groups(elements)
    groups_info = []

    for g_i in range(len(groups)):
        g = groups[g_i]
        bb = bounding_box(g)
        bb_ex = [[max(bb[0][0] - 1, 0), max(bb[0][1] - 1, 0)], [min(bb[1][0] + 1, overlay_w - 1), min(bb[1][1] + 1, overlay_h - 1)]]
        rect = (bb_ex[0][0] * 64, bb_ex[0][1] * 64, (bb_ex[1][0] + 1) * 64, (bb_ex[1][1] + 1) * 64)
        # groups_info.append({"offset_to_insert": (w_start, h_start), "bb_ex": bb_ex, "rect": rect, "elements": g})
        groups_info.append({"bb_ex": bb_ex, "rect": rect, "elements": g})

    def compare(a, b):
        a_w = a["bb_ex"][1][0] - a["bb_ex"][0][0]
        a_h = a["bb_ex"][1][1] - a["bb_ex"][0][1]
        b_w = b["bb_ex"][1][0] - b["bb_ex"][0][0]
        b_h = b["bb_ex"][1][1] - b["bb_ex"][0][1]
        max_a = max(a_w, a_h)
        min_a = min(a_w, a_h)
        max_b = max(b_w, b_h)
        min_b = min(b_w, b_h)
        if max_a < max_b:
            return -1
        if max_a > max_b:
            return 1
        if min_a < min_b:
            return -1
        if min_a > min_b:
            return 1
        return 0

    groups_info = sorted(groups_info, key=cmp_to_key(compare))
    groups_info.reverse()
    # groups are sorted, so let's start to place them
    field_h = (image_h + 1) * len(groups)
    field_w = image_w + 1
    print(field_h, field_w)
    field = np.zeros((field_h, field_w))
    new_image_h = 0
    for group in groups_info:
        bb_w = group["bb_ex"][1][0] - group["bb_ex"][0][0] + 1
        bb_h = group["bb_ex"][1][1] - group["bb_ex"][0][1] + 1
        for y in range(field_h - bb_h):
            if "offset_to_insert" in group:
                break
            for x in range(field_w - bb_w):
                found_place = True
                for bb_y in range(bb_h):
                    if not found_place:
                        break
                    for bb_x in range(bb_w):
                        if field[y+bb_y][x+bb_x] != 0:
                            found_place = False
                            break
                if found_place:
                    group["offset_to_insert"] = (x, y)
                    break
        for bb_y in range(bb_h):
            for bb_x in range(bb_w):
                y = group["offset_to_insert"][1] + bb_y
                new_image_h = max(y, new_image_h)
                field[y][group["offset_to_insert"][0] + bb_x] = 1
    print(new_image_h, overlay_h)
    output_image = Image.new(mode="RGB", size=(image_w * 64, (overlay_h + new_image_h + 1) * 64))
    output_image.paste(im.crop((0, 0, overlay_w * 64, overlay_h * 64)))

    output_wed_data = bytearray(wed_data)

    for group in groups_info:
        group_rect_offset = (group["offset_to_insert"][0] * 64, (overlay_h + group["offset_to_insert"][1]) * 64)
        output_image.paste(im.crop((group["rect"])), group_rect_offset)
        for first_tile_coord in group["elements"]:
            first_tile = first_tile_coord[1] * overlay_w + first_tile_coord[0]
            second_tile = tile_map[first_tile][0]
            second_tile_coords = [second_tile % image_w, second_tile // image_w]
            second_tile_rect = (second_tile_coords[0] * 64, second_tile_coords[1] * 64, second_tile_coords[0] * 64 + 64, second_tile_coords[1] * 64 + 64)
            im.crop(second_tile_rect)
            second_tile_offset = (group_rect_offset[0] + 64 * (first_tile_coord[0] - group["bb_ex"][0][0]),
                                  group_rect_offset[1] + 64 * (first_tile_coord[1] - group["bb_ex"][0][1]))
            output_image.paste(im.crop(second_tile_rect), second_tile_offset)
            new_second_tile = second_tile_offset[0] // 64 + second_tile_offset[1] // 64 * image_w
            st_bytes = new_second_tile.to_bytes(2, 'little')
            output_wed_data[tile_map[first_tile][1]] = st_bytes[0]
            output_wed_data[tile_map[first_tile][1] + 1] = st_bytes[1]

    filepath_out_wed = os.path.join(args.outdir, basename + ".WED")
    filepath_out_png = os.path.join(args.outdir, basename + ".PNG")
    output_image.save(filepath_out_png)
    wed_out = open(filepath_out_wed, mode="wb")
    wed_out.write(output_wed_data)

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





