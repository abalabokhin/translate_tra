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


def tile_is_empty(image, tile, width):
    offset = (tile % width * 64, tile // width * 64)
    first_pixel = image.getpixel(offset)
    for x in range(64):
        for y in range(64):
            if not image.getpixel((offset[0] + x, offset[1] + y)) == first_pixel:
                return False
    return True


def place_shape_if_possible(field, shape, corner):
    for x in range(shape.shape[0]):
        for y in range(shape.shape[1]):
            if shape[x][y] == 1 and not field[corner[0]+x][corner[1]+y] == 0:
                return False
            elif shape[x][y] == 2 and field[corner[0]+x][corner[1]+y] == 1:
                return False
    for x in range(shape.shape[0]):
        for y in range(shape.shape[1]):
            if not shape[x][y] == 0:
                field[corner[0] + x][corner[1] + y] = shape[x][y]
    return True


def prepare_and_paste_overlay(input_im, output_im, in_first_tile, in_second_tile, out_second_tile_offset, image_w):
    first_tile_rect = (in_first_tile % image_w * 64, in_first_tile // image_w * 64, in_first_tile % image_w * 64 + 64, in_first_tile // image_w * 64 + 64)
    second_tile_rect = (in_second_tile % image_w * 64, in_second_tile // image_w * 64, in_second_tile % image_w * 64 + 64, in_second_tile // image_w * 64 + 64)
    first_tile = input_im.crop(first_tile_rect)
    second_tile = input_im.crop(second_tile_rect)
    output_im.paste(second_tile, (first_tile_rect[0], first_tile_rect[1]))
    for x in range(64):
        for y in range(64):
            if second_tile.getpixel((x, y)) != (0, 0, 0, 0):
                first_tile.putpixel((x, y), (0, 0, 0, 0))
    output_im.paste(first_tile, out_second_tile_offset)


__desc__ = '''
This program takes WED and corresponding PNG files and convert them both to prepare them to export in EE games on infinity engine.
'''

if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile1', help='WED file')
    parser.add_argument('outdir', help='dir to put transformed WED and PNG files', default=".")
    parser.add_argument('--style', help='style, how to place additional tiles: [chess|grouping|optimal]', default="optimal")
    args = parser.parse_args()
    style = args.style

    print("Processing file {}".format(args.infile1))
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

    output_wed_data = bytearray(wed_data)
    bytes_negative_one = (-1).to_bytes(2, 'little', signed=True)

    # (second_tyle, first_tyle, second_tile_offset, is_overlay)
    tile_map = []
    im = Image.open(png_filename)
    image_w, image_h = im.size
    image_w //= 64
    image_h //= 64

    all_second_tiles = set()
    for tile_i in range(overlay_w * overlay_h):
        tilemap_offset_i = tilemap_offset + tile_i * 0xa
        tile_start_i = int.from_bytes(wed_data[tilemap_offset_i:tilemap_offset_i + 2], "little")
        tile_count = int.from_bytes(wed_data[tilemap_offset_i + 0x2:tilemap_offset_i + 0x2 + 2], "little")
        second_tile_offset = tilemap_offset_i + 0x4
        second_tile = int.from_bytes(wed_data[second_tile_offset:second_tile_offset + 2], "little", signed=True)
        is_overlay = not (int.from_bytes(wed_data[tilemap_offset_i + 0x6:tilemap_offset_i + 0x6 + 1], "little", signed=True) == 0)

        if tile_count > 1:
            # force chess style if there are fireplaces, because it is not clear how to group in this case
            style = "chess"
            for tile_ii in range(tile_count):
                tile_ii_offset = tile_index_lookup_offset + (tile_start_i + tile_ii) * 2
                first_tile = int.from_bytes(wed_data[tile_ii_offset:tile_ii_offset + 2], "little")
                all_second_tiles.add(first_tile)
                tile_map.append({"st": first_tile, "ft": first_tile, "sto": tile_ii_offset, "is_o": is_overlay})

        if second_tile < 0:
            continue
        all_second_tiles.add(second_tile)

        # if tile_is_empty(im, second_tile, image_w):
        #     output_wed_data[second_tile_offset] = bytes_negative_one[0]
        #     output_wed_data[second_tile_offset + 1] = bytes_negative_one[1]
        #     continue

        for tile_ii in range(tile_count):
            tile_ii_offset = tile_index_lookup_offset + (tile_start_i + tile_ii) * 2
            first_tile = int.from_bytes(wed_data[tile_ii_offset:tile_ii_offset + 2], "little")
            tile_map.append({"st": second_tile, "ft": first_tile, "sto": second_tile_offset, "is_o": is_overlay})

    if len(tile_map) == 0:
        sys.exit("Nothing to do, exiting")

    # sanity check
    for tile_coord_y in range(overlay_h, image_h):
        for tile_coord_x in range(0, image_w):
            tile = tile_coord_y * image_w + tile_coord_x
            if tile not in all_second_tiles:
                if not tile_is_empty(im, tile, image_w):
                    print("Unknown non empty tile ({} : [{}, {}]) that was not found in WED file, please make sure it is ok".format(tile, tile_coord_x, tile_coord_y))

    if style == "chess" or style == "optimal":
        n_additional_rows_chess = (len(tile_map) // image_w + 1) * 4
    if style == "grouping" or style == "optimal":
        n_additional_rows_grouping = 0
        elements = []
        for k in tile_map:
            elements.append([k["ft"] % overlay_w, k["ft"] // overlay_w])

        groups = find_groups(elements)
        groups_info = []

        for g in groups:
            bb = bounding_box(g)
            bb_ex = [[max(bb[0][0] - 1, 0), max(bb[0][1] - 1, 0)], [min(bb[1][0] + 1, overlay_w - 1), min(bb[1][1] + 1, overlay_h - 1)]]
            rect = (bb_ex[0][0] * 64, bb_ex[0][1] * 64, (bb_ex[1][0] + 1) * 64, (bb_ex[1][1] + 1) * 64)
            shape = np.zeros((bb_ex[1][0] - bb_ex[0][0] + 1, bb_ex[1][1] - bb_ex[0][1] + 1))
            for element in g:
                shape[element[0] - bb_ex[0][0]][element[1] - bb_ex[0][1]] = 1

            for x in range(shape.shape[0]):
                for y in range(shape.shape[1]):
                    if shape[x][y] == 1:
                        for dx in range(-1, 2):
                            for dy in range(-1, 2):
                                nx = x + dx
                                ny = y + dy
                                if nx < 0 or ny < 0 or nx >= shape.shape[0] or ny >= shape.shape[1]:
                                    continue
                                if shape[nx][ny] == 0:
                                    shape[nx][ny] = 2
            groups_info.append({"bb_ex": bb_ex, "rect": rect, "elements": g, "shape": shape})

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
        field = np.zeros((field_w, field_h))
        for group in groups_info:
            bb_w = group["bb_ex"][1][0] - group["bb_ex"][0][0] + 1
            bb_h = group["bb_ex"][1][1] - group["bb_ex"][0][1] + 1
            for y in range(field_h - bb_h):
                if "offset_to_insert" in group:
                    break
                for x in range(field_w - bb_w):
                    if place_shape_if_possible(field, group["shape"], (x, y)):
                        group["offset_to_insert"] = (x, y)
                        n_additional_rows_grouping = max(y + bb_h - 1, n_additional_rows_grouping)
                        break

    if style == "optimal":
        if n_additional_rows_grouping <= n_additional_rows_chess:
            style = "grouping"
        else:
            style = "chess"

    if style == "chess":
        n_additional_rows = n_additional_rows_chess
    elif style == "grouping":
        n_additional_rows = n_additional_rows_grouping
    else:
        sys.exit("Unknown style for additional tiles, exiting...")

    output_image = Image.new(mode="RGBA", size=(image_w * 64, (overlay_h + n_additional_rows + 1) * 64))
    output_image.paste(im.crop((0, 0, overlay_w * 64, overlay_h * 64)))

    if style == "chess":
        tile_i = 0
        for tile_el in tile_map:
            first_tile = tile_el["ft"]
            second_tile = tile_el["st"]
            second_tile_coords = [second_tile % image_w, second_tile // image_w]
            second_tile_rect = (second_tile_coords[0] * 64, second_tile_coords[1] * 64, second_tile_coords[0] * 64 + 64, second_tile_coords[1] * 64 + 64)
            second_tile_offset = (tile_i * 2 % image_w * 64, (overlay_h + 2 * (1 + (tile_i * 2) // image_w) - 1) * 64)
            if not tile_el["is_o"]:
                output_image.paste(im.crop(second_tile_rect), second_tile_offset)
            else:
                prepare_and_paste_overlay(im, output_image, first_tile, second_tile, second_tile_offset, image_w)
            tile_i += 1
            new_second_tile = second_tile_offset[0] // 64 + second_tile_offset[1] // 64 * image_w
            st_bytes = new_second_tile.to_bytes(2, 'little')
            output_wed_data[tile_el["sto"]] = st_bytes[0]
            output_wed_data[tile_el["sto"] + 1] = st_bytes[1]

    elif style == "grouping":
        def find_tile_el_by_first_tile(tile_map, first_tile):
            for tile_el in tile_map:
                if tile_el["ft"] == first_tile:
                    return tile_el
            sys.exit("Cannot find second tile for the first on , impossible situation")

        for group in groups_info:
            group_rect_offset = (group["offset_to_insert"][0] * 64, (overlay_h + group["offset_to_insert"][1]) * 64)
            # output_image.paste(im.crop((group["rect"])), group_rect_offset)
            for first_tile_coord in group["elements"]:
                first_tile = first_tile_coord[1] * overlay_w + first_tile_coord[0]
                tile_el = find_tile_el_by_first_tile(tile_map, first_tile)
                second_tile = tile_el["st"]
                second_tile_coords = [second_tile % image_w, second_tile // image_w]
                second_tile_rect = (second_tile_coords[0] * 64, second_tile_coords[1] * 64, second_tile_coords[0] * 64 + 64, second_tile_coords[1] * 64 + 64)
                im.crop(second_tile_rect)
                second_tile_offset = (group_rect_offset[0] + 64 * (first_tile_coord[0] - group["bb_ex"][0][0]),
                                      group_rect_offset[1] + 64 * (first_tile_coord[1] - group["bb_ex"][0][1]))
                if not tile_el["is_o"]:
                    output_image.paste(im.crop(second_tile_rect), second_tile_offset)
                else:
                    prepare_and_paste_overlay(im, output_image, first_tile, second_tile, second_tile_offset, image_w)
                new_second_tile = second_tile_offset[0] // 64 + second_tile_offset[1] // 64 * image_w
                st_bytes = new_second_tile.to_bytes(2, 'little')
                output_wed_data[tile_el["sto"]] = st_bytes[0]
                output_wed_data[tile_el["sto"] + 1] = st_bytes[1]

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





