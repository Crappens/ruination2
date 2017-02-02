__author__ = 'bcrysler'

import math
from itertools import chain

import numpy
from lxml import etree
from models import Rectangle, TextBox, Teacher
from app.flowing.template_generator.settings import *


def test_thoughts(rows, columns, names, teacher, fill_page, top_title, side_title, font_size, percent, save_name,
                  top_width, side_width):
    left = []
    right = []
    # height = SPREAD_HEIGHT - 2 * TOP_OFFSET - 12
    # l_width = SPREAD_WIDTH / 2 - LEFT_PAGE_OFFSET * 2 - 12
    # r_width = l_width
    # top_offset = TOP_OFFSET + 6
    # left_offset = LEFT_PAGE_OFFSET + 6
    # right_offset = RIGHT_PAGE_OFFSET + LEFT_PAGE_OFFSET + 6
    height = SPREAD_HEIGHT - 2 * TOP_OFFSET
    l_width = SPREAD_WIDTH / 2 - LEFT_PAGE_OFFSET - 6
    r_width = l_width
    top_offset = TOP_OFFSET
    left_offset = LEFT_PAGE_OFFSET
    right_offset = RIGHT_PAGE_OFFSET + 6

    if side_title in [1, 3]:
        left.append(TextBox({'x': left_offset,
                             'y': top_offset,
                             'height': height,
                             'width': side_width,
                             'extra': 'l_side'}))
        left_offset += (side_width + PADDING)
        l_width -= (side_width + PADDING)
        if side_title == 1:
            right.append(TextBox({'x': right_offset + r_width - side_width,
                                  'y': top_offset,
                                  'height': height,
                                  'width': side_width,
                                  'extra': 'r_side'}))
            r_width -= (side_width + PADDING)
        elif side_title == 3:
            right.append(TextBox({'x': right_offset,
                                  'y': top_offset,
                                  'height': height,
                                  'width': side_width,
                                  'extra': 'l_side'}))
            right_offset += (side_width + PADDING)
            r_width -= (side_width + PADDING)
    elif side_title in [2, 4]:
        left.append(TextBox({'x': left_offset + l_width - side_width,
                             'y': top_offset,
                             'height': height,
                             'width': side_width,
                             'extra': 'r_side'}))
        l_width -= (side_width + PADDING)
        if side_title == 2:
            right.append(TextBox({'x': right_offset,
                                  'y': top_offset,
                                  'height': height,
                                  'width': side_width,
                                  'extra': 'l_side'}))
            right_offset += (side_width + PADDING)
            r_width -= (side_width + PADDING)
        elif side_title == 4:
            right.append(TextBox({'x': right_offset + r_width - side_width,
                                  'y': top_offset,
                                  'height': height,
                                  'width': side_width,
                                  'extra': 'r_side'}))
            r_width -= (side_width + PADDING)

    if fill_page is False:
        height *= percent

    if top_title is True:
        left.append(TextBox({'x': left_offset,
                             'y': top_offset,
                             'height': top_width,
                             'width': l_width,
                             'extra': 'top'}))
        right.append(TextBox({'x': right_offset,
                              'y': top_offset,
                              'height': top_width,
                              'width': r_width,
                              'extra': 'top'}))
        height -= (top_width + PADDING)
        top_offset += (top_width + PADDING)

    # Start name math
    text_height = (height - (rows - 1) * PADDING) / rows
    if teacher in [2, 4, 6, 8, 9, 10, 11, 12]:
        height /= 2
        height -= (top_width / 2)
        height -= PADDING
        text_height = (height - (rows - 1) * PADDING) / rows
        left.append(TextBox({'x': left_offset,
                             'y': top_offset + height + PADDING,
                             'height': top_width,
                             'width': l_width,
                             'extra': 'separator'}))
        right.append(TextBox({'x': right_offset,
                              'y': top_offset + height + PADDING,
                              'height': top_width,
                              'width': r_width,
                              'extra': 'separator'}))
    name_list = []
    temp = 0
    for box in range(1, rows + 1):
        name_list.append(TextBox({'x': left_offset,
                                  'y': top_offset + temp,
                                  'height': text_height,
                                  'width': NAME_LENGTH,
                                  'extra': 'name_left'}))
        temp += (text_height + PADDING)

    if teacher in [2, 4, 6, 8, 9, 10, 11, 12]:
        name_list += push_down(name_list, height, top_width)

    if names == 2:
        left_offset += (NAME_LENGTH + PADDING)
        l_width -= (NAME_LENGTH + PADDING)
        left += name_list
        mirrored = reverse_boxes(name_list, width=l_width, offset=left_offset, cols=columns)
        right += shift_right(mirrored, l=left_offset, r=right_offset)
        r_width -= (NAME_LENGTH + PADDING)
    elif names == 3:
        right += shift_right(name_list, l=left_offset, r=right_offset)
        mirrored = reverse_boxes(name_list, width=l_width, offset=left_offset, cols=columns)
        left += mirrored
        r_width -= (NAME_LENGTH + PADDING)
        l_width -= (NAME_LENGTH + PADDING)
        right_offset += (NAME_LENGTH + PADDING)
    elif names == 7:
        left += name_list
        right += shift_right(name_list, l=left_offset, r=right_offset)
        left_offset += (NAME_LENGTH + PADDING)
        l_width -= (NAME_LENGTH + PADDING)
        right_offset += (NAME_LENGTH + PADDING)
        r_width -= (NAME_LENGTH + PADDING)
    elif names == 8:
        mirrored = reverse_boxes(name_list, width=l_width, offset=left_offset, cols=columns)
        left += mirrored
        right += shift_right(mirrored, l=left_offset, r=right_offset)
        l_width -= (NAME_LENGTH + PADDING)
        r_width -= (NAME_LENGTH + PADDING)

    if teacher in [2, 4, 6, 8, 9, 10, 11, 12]:
        height += PADDING
        height += (top_width / 2)
        height *= 2

    #Start picture rectangle math
    if teacher in [2, 4, 6, 8, 9, 10, 11, 12]:
        height /= 2
        height -= (top_width / 2)
        height -= PADDING
    row_width = (l_width - (columns - 1) * PADDING) / columns
    column_height = (height - (rows - 1) * PADDING) / rows
    if row_width / 4 * 5 <= column_height:
        column_height = row_width / 4 * 5
    else:
        row_width = column_height / 5 * 4
    new_group = []
    tempy = top_offset
    for y in range(1, rows + 1):
        tempx = left_offset
        for x in range(1, columns + 1):
            new_group.append(Rectangle({'x': tempx,
                                        'y': tempy,
                                        'height': column_height,
                                        'width': row_width,
                                        'extra': 'student',
                                        'column': x,
                                        'row': y}))
            tempx += (row_width + PADDING)
        tempy += (column_height + PADDING)

    # Space horizontally
    new_group = space_horizontally(new_group, width=l_width, row_width=row_width, columns=columns, offset=left_offset)
    if names not in [1, 6]:
        new_group = space_vertically(new_group, height=height, c_height=column_height,
                                     rows=rows, top_offset=top_offset, text_height=text_height)
    else:
        new_group = space_vertically(new_group, height=height, c_height=column_height, rows=rows, top_offset=top_offset)

    # Generate teacher box
    if teacher != 0:
        teacher_box = Teacher({'bottom_right': new_group.pop(columns + 1),
                               'bottom_left': new_group.pop(columns),
                               'top_right': new_group.pop(1),
                               'top_left': new_group.pop(0)})
        new_group.insert(0, Rectangle({'x': teacher_box.get_x(),
                                       'y': teacher_box.get_y(),
                                       'height': teacher_box.get_height(),
                                       'width': teacher_box.get_width(),
                                       'extra': 'teacher',
                                       'column': 1,
                                       'row': 1}))
    # Use above rectangle list to flip, rotate, push to fill both pages
    if teacher == 1:
        left += new_group
        right += shift_right(new_group, l=left_offset, r=right_offset)
    elif teacher == 2:
        left = left + new_group + push_down(new_group, height=height, top=top_width)
        right += shift_right(new_group, l=left_offset, r=right_offset)
        right += push_down(shift_right(new_group, l=left_offset, r=right_offset), height=height, top=top_width)
    elif teacher == 3:
        mirrored = reverse_boxes(new_group, width=l_width, offset=left_offset, cols=columns)
        left += mirrored
        right += shift_right(mirrored, l=left_offset, r=right_offset)
    elif teacher == 4:
        mirrored = reverse_boxes(new_group, width=l_width, offset=left_offset, cols=columns)
        left += mirrored
        left += push_down(mirrored, height=height, top=top_width)
        right += shift_right(mirrored, l=left_offset, r=right_offset)
        right += shift_right(push_down(mirrored, height=height, top=top_width), l=left_offset, r=right_offset)
    elif teacher == 5:
        left += new_group
        right += shift_right(reverse_boxes(new_group, width=l_width, offset=left_offset, cols=columns),
                             l=left_offset, r=right_offset)
    elif teacher == 6:
        left += new_group
        left += push_down(new_group, height=height, top=top_width)
        mirrored = reverse_boxes(new_group, width=l_width, offset=left_offset, cols=columns)
        shifted = shift_right(mirrored, l=left_offset, r=right_offset)
        right += shifted
        right += push_down(shifted, height=height, top=top_width)
    elif teacher == 7:
        left += reverse_boxes(new_group, width=l_width, offset=left_offset, cols=columns)
        right += shift_right(new_group, l=left_offset, r=right_offset)
    elif teacher == 8:
        mirrored = reverse_boxes(new_group, width=l_width, offset=left_offset, cols=columns)
        left += mirrored
        left += push_down(mirrored, height=height, top=top_width)
        shifted = shift_right(new_group, l=left_offset, r=right_offset)
        right += shifted
        right += push_down(shifted, height=height, top=top_width)
    elif teacher == 9:
        left += new_group
        mirrored = reverse_boxes(push_down(new_group, height=height, top=top_width),
                                 width=l_width, offset=left_offset, cols=columns)
        left += mirrored
        right += shift_right(new_group, l=left_offset, r=right_offset)
        right += shift_right(mirrored, l=left_offset, r=right_offset)
    elif teacher == 10:
        mirrored = reverse_boxes(new_group, width=l_width, offset=left_offset, cols=columns)
        left += mirrored
        left += push_down(new_group, height=height, top=top_width)
        right += shift_right(mirrored, l=left_offset, r=right_offset)
        right += push_down(shift_right(new_group, l=left_offset, r=right_offset), height=height, top=top_width)
    elif teacher == 11:
        mirrored = reverse_boxes(new_group, width=l_width, offset=left_offset, cols=columns)
        left += new_group
        left += push_down(mirrored, height=height, top=top_width)
        right += shift_right(mirrored, l=left_offset, r=right_offset)
        right += push_down(shift_right(new_group, l=left_offset, r=right_offset), height=height, top=top_width)
    elif teacher == 12:
        mirrored = reverse_boxes(new_group, width=l_width, offset=left_offset, cols=columns)
        left += mirrored
        left += push_down(new_group, height=height, top=top_width)
        right += shift_right(new_group, l=left_offset, r=right_offset)
        right += shift_right(push_down(mirrored, height=height, top=top_width), l=left_offset, r=right_offset)
    else:  # teacher == 0
        left += new_group
        right += shift_right(new_group, l=left_offset, r=right_offset)

    if names == 1:
        left = split_below(left, font_size=font_size, width=l_width, offset=left_offset, columns=columns)
        right = split_below(right, font_size=font_size, width=r_width, offset=right_offset, columns=columns)
    if names == 6:
        left = split_above(left, font_size=font_size, width=l_width, offset=left_offset, columns=columns)
        right = split_above(right, font_size=font_size, width=r_width, offset=right_offset, columns=columns)

    build_page(left, right, save_name, font_size)


def split_above(group, font_size, width, offset, columns):
    text_width = (width - (columns - 1) * PADDING) / columns
    name_boxes = []
    for box in group:
        if box.extra == 'teacher':
            double_width = (text_width * 2 + PADDING)
            if box.column == 1:
                center_over = offset + double_width / 2
            else:
                center_over = offset + (text_width * (columns - 2) + PADDING * (columns - 2)) + double_width / 2
            teacher_center = box.get_cx()
            box.x += (center_over - teacher_center)
        elif box.extra == 'student':
            rect_y = box.y + (font_size * 1.1715) * 2 + PADDING
            new_height = box.height - ((font_size * 1.1715) * 2 + PADDING)
            text = TextBox({'x': offset + text_width * (box.column - 1) + PADDING * (box.column - 1),
                            'y': box.y,
                            'width': text_width,
                            'height': (font_size * 1.1715) * 2,
                            'extra': box.extra})
            box.x = text.x + (text_width - new_height / 5 * 4) / 2
            box.y = rect_y
            box.width = new_height / 5 * 4
            box.height = new_height
            name_boxes.append(text)
    return group + name_boxes


def split_below(group, font_size, width, offset, columns):
    text_width = (width - (columns - 1) * PADDING) / columns
    name_boxes = []
    for box in group:
        if box.extra == 'teacher':
            double_width = (text_width * 2 + PADDING)
            if box.column == 1:
                center_over = offset + double_width / 2
            else:
                center_over = offset + (text_width * (columns - 2) + PADDING * (columns - 2)) + double_width / 2
            teacher_center = box.get_cx()
            box.x += (center_over - teacher_center)
        elif box.extra == 'student':
            text_y = box.y + box.height - (font_size * 1.1715) * 2
            new_height = box.height - ((font_size * 1.1715) * 2 + PADDING)
            text = TextBox({'x': offset + text_width * (box.column - 1) + PADDING * (box.column - 1),
                            'y': text_y,
                            'width': text_width,
                            'height': (font_size * 1.1715) * 2,
                            'extra': box.extra})
            box.x = text.x + (text_width - new_height / 5 * 4) / 2
            box.width = new_height / 5 * 4
            box.height = new_height
            name_boxes.append(text)
    return group + name_boxes


def space_horizontally(group, width, row_width, columns, offset):
    space_between_columns = (width - row_width * columns) / (columns - 1)
    start = offset
    level = 0
    temp = start
    for each in group:
        if isinstance(each, Rectangle):
            if level == 0:
                level = each.y
            elif each.y != level:
                temp = start
                level = each.y
            each.x = temp
            temp += row_width
            temp += space_between_columns
    return group


def space_vertically(group, height, c_height, rows, top_offset, text_height=None):
    if text_height is None:
        space_between_rows = (height - c_height * rows) / (rows - 1)
        if space_between_rows != PADDING:
            if space_between_rows > PADDING:
                space_between_rows = (height - c_height * rows) / rows
            start = top_offset
            col = 0
            for each in group:
                if each.x < col:
                    start += c_height
                    start += space_between_rows
                col = each.x
                each.y = start
    else:
        if group[0].height != text_height:
            height_diff = text_height - group[0].height
            height_offset = height_diff / 2
            start = top_offset
            col = 0
            for each in group:
                if each.x < col:
                    start += (text_height + PADDING)
                col = each.x
                each.y = start + height_offset
    return group


def reverse_boxes(group, width, offset, cols):
    temp = {}
    for k, v in enumerate(reversed(range(1, cols + 1)), start=1):
        temp[k] = v
    new_list = []
    for each in group:
        if each.extra == 'teacher':
            if each.column == 1:
                new_col = 5
            else:
                new_col = 1
            new_list.append(Rectangle({'x': width + offset - each.get_rx() + offset,
                                       'y': each.y,
                                       'height': each.height,
                                       'width': each.width,
                                       'extra': each.extra,
                                       'column': new_col,
                                       'row': each.row}))
        elif isinstance(each, Rectangle):
            new_list.append(Rectangle({'x': width + offset - each.get_rx() + offset,
                                       'y': each.y,
                                       'height': each.height,
                                       'width': each.width,
                                       'extra': each.extra,
                                       'column': temp[each.column],
                                       'row': each.row}))
        else:
            new_list.append(TextBox({'x': width + offset - each.get_rx() + offset,
                                     'y': each.y,
                                     'height': each.height,
                                     'width': each.width,
                                     'extra': 'name_right'}))
    return new_list


def push_down(group, height, top):
    row_count = []
    for cell in group:
        if cell.y not in row_count:
            row_count.append(cell.y)
    new_list = []
    for each in group:
        if isinstance(each, Rectangle):
            new_list.append(Rectangle({'x': each.x,
                                       'y': each.y + height + PADDING * 2 + top,
                                       'height': each.height,
                                       'width': each.width,
                                       'extra': each.extra,
                                       'column': each.column,
                                       'row': each.row + row_count.__len__()}))
        else:
            new_list.append(TextBox({'x': each.x,
                                     'y': each.y + height + PADDING * 2 + top,
                                     'height': each.height,
                                     'width': each.width,
                                     'extra': each.extra}))
    return new_list


def shift_right(group, l, r):
    new_list = []
    difference = r - l
    for each in group:
        if isinstance(each, Rectangle):
            new_list.append(Rectangle({'x': each.x + difference,
                                       'y': each.y,
                                       'height': each.height,
                                       'width': each.width,
                                       'extra': each.extra,
                                       'column': each.column,
                                       'row': each.row}))
        else:
            new_list.append(TextBox({'x': each.x + difference,
                                     'y': each.y,
                                     'height': each.height,
                                     'width': each.width,
                                     'extra': each.extra}))
    return new_list


# Strips newlines, tabs and all extra spacing out of the prettified bs4 soup object
def stringify(prettified):
    finalized = prettified.replace('\n', '').replace('\t', '')
    while ' <' in finalized or '> ' in finalized:
        finalized = finalized.replace(' <', '<')
        finalized = finalized.replace('> ', '>')
    return finalized


def find_original(point, center, angle):
    theta = angle * math.pi / 180
    A = [[math.cos(theta), -1*math.sin(theta)], [math.sin(theta), math.cos(theta)]]
    # Inverse A to x' side in order to solve for x (above formula)
    inv_a = numpy.linalg.inv(A)
    b = [point[0] - center[0], point[1] - center[1]]
    x = numpy.linalg.lstsq(inv_a, b)
    return (x[0][0] + center[0], x[0][1] + center[1])


def build_page(left, right, name, font_size):
    object_count = 1

    for each in [[left, "left"], [right, "right"], [chain(left, right), "full"]]:

        if os.path.isfile(os.path.join(dir_path, 'tmp/%s_%s.txt' % (name, each[1]))):
            os.remove(os.path.join(dir_path, 'tmp/%s_%s.txt' % (name, each[1])))

        svg = etree.Element("svg", nsmap={None: 'http://www.w3.org/2000/svg',
                                          'se': 'http://svg-edit.googlecode.com',
                                          'lyb': 'http://www.myyear.com',
                                          'xlink': "http://www.w3.org/1999/xlink"})
        svg.set("height", str(SPREAD_HEIGHT))
        svg.set("width", str(SPREAD_WIDTH))
        svg.set("preserveAspectRatio", "xMinYMin meet")
        svg.set("{http://www.myyear.com}templateName", "%s_%s" % (name, each[1]))

        # <g id="background_layer">
        background = etree.SubElement(svg, "g", id="background_layer")

        # <title>Background</title>
        background_title = etree.SubElement(background, "title")
        background_title.text = "Background"

        # <g lyb:dropTarget="g" id="background_group_F">
        background_group_f = etree.SubElement(background, "g", id="background_group_F")
        background_group_f.set("{http://www.myyear.com}dropTarget", "g")

        # <rect lyb:background="F" lyb:dropTarget="border" y="0" x="0" width="1236"
        # stroke-width="0" stroke="#000000" id="border_219" height="804" fill-opacity="0" fill="#000000"/>
        f_rect = etree.SubElement(background_group_f, "rect", id="background_F")
        f_rect.set("{http://www.myyear.com}background", "F")
        f_rect.set("{http://www.myyear.com}dropTarget", "border")
        f_rect.set("fill", "#FFFFFF")
        f_rect.set("fill-opacity", "1")
        f_rect.set("height", str(SPREAD_HEIGHT))
        f_rect.set("stroke", "#000000")
        f_rect.set("stroke-width", "0")
        f_rect.set("width", str(SPREAD_WIDTH))
        f_rect.set("x", "0")
        f_rect.set("y", "0")

        # <g lyb:dropTarget="g" id="background_group_L">
        background_group_l = etree.SubElement(background, "g", id="background_group_L")
        background_group_l.set("{http://www.myyear.com}dropTarget", "g")

        # <rect lyb:background="L" lyb:dropTarget="border" y="0" x="0" width="618" stroke-width="0" stroke="#000000"
        # id="background_L" height="804" fill-opacity="0" fill="#000000"/>
        l_rect = etree.SubElement(background_group_l, "rect", id="background_L")
        l_rect.set("{http://www.myyear.com}background", "L")
        l_rect.set("{http://www.myyear.com}dropTarget", "border")
        l_rect.set("fill", "#000000")
        l_rect.set("fill-opacity", "0")
        l_rect.set("height", str(SPREAD_HEIGHT))
        l_rect.set("stroke", "#000000")
        l_rect.set("stroke-width", "0")
        l_rect.set("width", str(SPREAD_WIDTH / 2))
        l_rect.set("x", "0")
        l_rect.set("y", "0")

        # <g lyb:dropTarget="g" id="background_group_R">
        background_group_r = etree.SubElement(background, "g", id="background_group_R")
        background_group_r.set("{http://www.myyear.com}dropTarget", "g")

        # <rect lyb:background="R" lyb:dropTarget="border" y="0" x="618" width="618" stroke-width="0" stroke="#000000"
        # id="background_R" height="804" fill-opacity="0" fill="#000000"/>
        r_rect = etree.SubElement(background_group_r, "rect", id="background_R")
        r_rect.set("{http://www.myyear.com}background", "R")
        r_rect.set("{http://www.myyear.com}dropTarget", "border")
        r_rect.set("fill", "#000000")
        r_rect.set("fill-opacity", "0")
        r_rect.set("height", str(SPREAD_HEIGHT))
        r_rect.set("stroke", "#000000")
        r_rect.set("stroke-width", "0")
        r_rect.set("width", str(SPREAD_WIDTH / 2))
        r_rect.set("x", str(SPREAD_WIDTH / 2))
        r_rect.set("y", "0")

        # <g>
        layer_1 = etree.SubElement(svg, "g", id="layer_1")
        if each[1] == "full":
            layer_1.set("{http://svg-edit.googlecode.com}template-type", "spread")
        else:
            layer_1.set("{http://svg-edit.googlecode.com}template-type", each[1])

        # <title>Layer 1</title>
        layer_1_title = etree.SubElement(layer_1, "title")
        layer_1_title.text = "Layer 1"

        for box in each[0]:
            if isinstance(box, Rectangle):
                # <rect lyb:dropTarget="undropped" id="svg_3" stroke-opacity="1" fill-opacity="0.8" fill="#8084bf"
                # stroke="#000000" stroke-width="1" x="244.44023" y="44.38847" width="66.66666" height="83.95061"/>
                rectangle = etree.SubElement(layer_1, "rect", id="svg_%s" % object_count)
                object_count += 1
                rectangle.set("{http://www.myyear.com}dropTarget", "undropped")
                rectangle.set("fill-opacity", "0.8")
                rectangle.set("fill", "#8084bf")
                rectangle.set("stroke", "#000000")
                rectangle.set("stroke-width", "1")
                rectangle.set("stroke-opacity", "1")
                rectangle.set("x", str(box.x))
                rectangle.set("y", str(box.y))
                rectangle.set("height", str(box.height))
                rectangle.set("width", str(box.width))
                if box.extra == "student":
                    rectangle.set("{http://svg-edit.googlecode.com}generated", "portrait_box")
            elif isinstance(box, TextBox):
                # <g lyb:text-group="true" text-anchor="end" font-style="normal" font-weight="normal" id="svg_10"
                # font-family="Cochise Regular" font-size="12" stroke-width="0" stroke="#000000" fill="#000000">
                g_text = etree.Element("g", id="svg_%s" % object_count)
                object_count += 1

                g_text.set("{http://www.myyear.com}text-group", "true")
                if box.extra not in ["top", "r_side", "l_side"]:
                    g_text.set("{http://svg-edit.googlecode.com}generated", "portrait_text")
                g_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

                # <rect width="144.44444" height="97.53086" stroke="#666666" stroke-opacity="1" stroke-width="2"
                # fill-opacity="0" id="svg_11" y="37.59834" x="21.41975"/>
                text_rect = etree.SubElement(g_text, "rect", id="guide_svg_%s" % object_count)
                object_count += 1
                text_rect.set("x", str(box.x))
                text_rect.set("y", str(box.y))
                text_rect.set("height", str(box.height))
                text_rect.set("width", str(box.width))
                text_rect.set("stroke", "#666666")
                text_rect.set("stroke-opacity", "1")
                text_rect.set("stroke-width", "1")
                text_rect.set("fill-opacity", "0")

                # <text lyb:autowrap="true" se:autowrap_width="130.93093" font-style="normal" font-weight="normal"
                # text-anchor="end" font-family="Cochise Regular" font-size="12" id="svg_8"
                # y="51.65634" x="21.41975" opacity="1" fill-opacity="1" stroke-opacity="1" stroke-linecap="butt"
                # stroke-linejoin="miter" stroke-dasharray="none" stroke-width="0" stroke="#000000" fill="#000000">
                text_text = etree.SubElement(g_text, "text", id="svg_%s" % object_count)
                object_count += 1
                text_text.set("font-style", "normal")
                text_text.set("font-weight", "normal")
                text_text.set("{http://www.myyear.com}autowrap", "true")
                text_text.set("{http://svg-edit.googlecode.com}autowrap_width", str(box.width))
                text_text.set("font-family", "Cochise Regular")
                text_text.set("font-size", str(font_size))
                text_text.set("{http://www.myyear.com}autowrap", "true")
                text_text.set("y", str(box.y + font_size * 1.1715))
                text_text.set("opacity", "1")
                text_text.set("fill-opacity", "1")
                text_text.set("stroke-opacity", "1")
                text_text.set("stroke-linecap", "butt")
                text_text.set("stroke-linejoin", "miter")
                text_text.set("stroke-dasharray", "none")
                text_text.set("stroke-width", "0")
                text_text.set("stroke", "#000000")
                text_text.set("fill", "#000000")

                if box.extra == "r_side":
                    g_text.set("text-anchor", "start")
                    text_text.set("text-anchor", "start")
                    text_text.set("{http://svg-edit.googlecode.com}autowrap_width", str(box.height))

                    text_rect.set("width", str(box.height))
                    text_rect.set("height", str(box.width))

                    new_coordinate = find_original(point=(SPREAD_WIDTH - 30, -30),
                                                   center=(SPREAD_WIDTH - 281, -250),
                                                   angle=90)
                    text_rect.set("x", str(new_coordinate[0]))
                    text_rect.set("y", str(new_coordinate[1] * -1))
                    text_text.set("x", str(new_coordinate[0]))
                    text_text.set("y", str(new_coordinate[1] * -1 + font_size * 1.2))

                    g_text.set("transform", "rotate(90 %s,%s)" % (955, 250))
                elif box.extra == "l_side":
                    text_text.set("text-anchor", "start")
                    text_text.set("{http://svg-edit.googlecode.com}autowrap_width", str(box.height))

                    text_rect.set("width", str(box.height))
                    text_rect.set("height", str(box.width))

                    new_coordinate = find_original(point=(30, -SPREAD_HEIGHT + 30),
                                                   center=(55, -250),
                                                   angle=-90)
                    text_rect.set("x", str(new_coordinate[0]))
                    text_rect.set("y", str(new_coordinate[1] * -1))
                    text_text.set("x", str(new_coordinate[0]))
                    text_text.set("y", str(new_coordinate[1] * -1 + font_size * 1.2))

                    g_text.set("transform", "rotate(-90 %s,%s)" % (55, 250))
                elif box.extra in ["top", "separator"]:
                    # g_text.set("text-anchor", "start")
                    text_text.set("text-anchor", "start")
                    text_text.set("x", str(box.x))
                elif box.extra == "name_left":
                    # g_text.set("text-anchor", "end")
                    text_text.set("text-anchor", "end")
                    text_text.set("x", str(box.x + box.width))
                elif box.extra == "name_right":
                    # g_text.set("text-anchor", "start")
                    text_text.set("text-anchor", "start")
                    text_text.set("x", str(box.x))
                else:  # box.extra == "name_middle":
                    # g_text.set("text-anchor", "middle")
                    text_text.set("text-anchor", "middle")
                    text_text.set("x", str(box.x + box.width / 2))

                # <tspan x="165.86419" dy="0" se:leadingwhitespacecount="0" stroke-width="0" stroke-opacity="1"
                # stroke-linejoin="miter" stroke-linecap="butt" stroke-dasharray="none" stroke="#000000" opacity="1"
                # font-weight="normal" font-style="normal" font-size="12" font-family="Cochise Regular"
                # fill-opacity="1" fill="#000000" id="svg_127">Text Box...</tspan>
                text_tspan = etree.SubElement(text_text, "tspan", id="svg_%s" % object_count)
                object_count += 1
                text_tspan.set("x", text_text.get("x"))
                text_text.set("x", text_rect.get("x"))
                text_tspan.set("dy", "0")
                # text_tspan.set("{http://svg-edit.googlecode.com}leadingwhitespacecount", "0")
                # text_tspan.set("stroke-width", "0")
                # text_tspan.set("stroke-opacity", "1")
                # text_tspan.set("stroke-linejoin", "miter")
                # text_tspan.set("stroke-linecap", "butt")
                # text_tspan.set("stroke-dasharray", "none")
                # text_tspan.set("stroke", "#000000")
                text_tspan.set("opacity", "1")
                text_tspan.set("font-weight", "normal")
                text_tspan.set("font-style", "normal")
                text_tspan.set("font-size", str(font_size))
                text_tspan.set("font-family", "Cochise Regular")
                # text_tspan.set("fill-opacity", "1")
                text_tspan.set("fill", "rgb(0,0,0)")
                text_tspan.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                text_tspan.text = "Text Box..."

                layer_1.append(g_text)

        # <g lyb:zHeight="1125" lyb:zWidth="875" lyb:zx="0" lyb:zy="0" se:guide="true" se:lock="L" id="guide_LEFT">
        g_guide_l = etree.SubElement(svg, "g", id="guide_LEFT")
        g_guide_l.set("{http://svg-edit.googlecode.com}guide", "true")
        g_guide_l.set("{http://svg-edit.googlecode.com}lock", "L")
        g_guide_l.set("{http://www.myyear.com}zHeight", "1125")
        g_guide_l.set("{http://www.myyear.com}zWidth", "875")
        g_guide_l.set("{http://www.myyear.com}zx", "0")
        g_guide_l.set("{http://www.myyear.com}zy", "0")

        # <title>Safety Zone LEFT</title>
        guide_l_title = etree.SubElement(g_guide_l, "title")
        guide_l_title.text = "Safety Zone LEFT"

        # <rect y="0" x="0" width="648" stroke="#0000ff" id="guide_LEFT_BLEED_rect" height="828" fill="none"/>
        guide_l_rect_1 = etree.SubElement(g_guide_l, "rect", id="guide_LEFT_rect")
        guide_l_rect_1.set("fill", "none")
        guide_l_rect_1.set("height", str(SPREAD_HEIGHT))
        guide_l_rect_1.set("stroke", "#ff0000")
        guide_l_rect_1.set("width", str(SPREAD_WIDTH / 2))
        guide_l_rect_1.set("x", "0")
        guide_l_rect_1.set("y", "0")

        # <rect y="18" x="18" width="612" stroke="#00ff00" id="guide_LEFT_SAFETY_rect" height="792" fill="none"/>
        guide_l_rect_2 = etree.SubElement(g_guide_l, "rect", id="guide_LEFT_CUT_rect")
        guide_l_rect_2.set("fill", "none")
        guide_l_rect_2.set("height", str(SPREAD_HEIGHT - 12))
        guide_l_rect_2.set("stroke", "#0000ff")
        guide_l_rect_2.set("width", str(SPREAD_WIDTH / 2 - 6))
        guide_l_rect_2.set("x", str(6))
        guide_l_rect_2.set("y", str(6))

        # <rect y="9" x="9" width="630" stroke="#ff0000" id="guide_LEFT_CUT_rect" height="810" fill="none"
        # stroke-width="18" opacity="0.5" />
        guide_l_rect_3 = etree.SubElement(g_guide_l, "rect", id="guide_LEFT_SAFETY_rect")
        guide_l_rect_3.set("fill", "none")
        guide_l_rect_3.set("height", str(SPREAD_HEIGHT - 60))
        guide_l_rect_3.set("stroke", "#00ff00")
        guide_l_rect_3.set("width", str(SPREAD_WIDTH / 2 - 36))
        guide_l_rect_3.set("x", str(30))
        guide_l_rect_3.set("y", str(30))

        # # <rect y="0" x="0" width="648" stroke="#0000ff" id="guide_LEFT_BLEED_rect" height="828" fill="none"/>
        # guide_l_rect_1 = etree.SubElement(g_guide_l, "rect", id="guide_LEFT_BLEED_rect")
        # guide_l_rect_1.set("fill", "none")
        # guide_l_rect_1.set("height", str(SPREAD_HEIGHT))
        # guide_l_rect_1.set("stroke", "#0000ff")
        # guide_l_rect_1.set("width", str(SPREAD_WIDTH / 2))
        # guide_l_rect_1.set("x", "0")
        # guide_l_rect_1.set("y", "0")
        #
        # # <rect y="18" x="18" width="612" stroke="#00ff00" id="guide_LEFT_SAFETY_rect" height="792" fill="none"/>
        # guide_l_rect_2 = etree.SubElement(g_guide_l, "rect", id="guide_LEFT_SAFETY_rect")
        # guide_l_rect_2.set("fill", "none")
        # guide_l_rect_2.set("height", str(SPREAD_HEIGHT - TOP_OFFSET * 2))
        # guide_l_rect_2.set("stroke", "#00ff00")
        # guide_l_rect_2.set("width", str(SPREAD_WIDTH / 2 - LEFT_PAGE_OFFSET * 2))
        # guide_l_rect_2.set("x", str(LEFT_PAGE_OFFSET))
        # guide_l_rect_2.set("y", str(TOP_OFFSET))
        #
        # # <rect y="9" x="9" width="630" stroke="#ff0000" id="guide_LEFT_CUT_rect" height="810" fill="none"
        # # stroke-width="18" opacity="0.5" />
        # guide_l_rect_3 = etree.SubElement(g_guide_l, "rect", id="guide_LEFT_CUT_rect")
        # guide_l_rect_3.set("fill", "none")
        # guide_l_rect_3.set("height", str(SPREAD_HEIGHT - TOP_OFFSET))
        # guide_l_rect_3.set("stroke", "#ff0000")
        # guide_l_rect_3.set("width", str(SPREAD_WIDTH / 2 - LEFT_PAGE_OFFSET))
        # guide_l_rect_3.set("x", str(LEFT_PAGE_OFFSET / 2))
        # guide_l_rect_3.set("y", str(TOP_OFFSET / 2))
        # guide_l_rect_3.set("opacity", "0.5")
        # guide_l_rect_3.set("stroke-width", str(TOP_OFFSET))
        #
        # # <rect y="24" x="24" width="600" stroke="#0000ff" id="guide_LEFT_SPACER_rect" height="780" fill="none"/>
        # guide_l_rect_4 = etree.SubElement(g_guide_l, "rect", id="guide_LEFT_SPACER_rect")
        # guide_l_rect_4.set("fill", "none")
        # guide_l_rect_4.set("height", str(SPREAD_HEIGHT - (TOP_OFFSET + 6) * 2))
        # guide_l_rect_4.set("stroke", "#0000ff")
        # guide_l_rect_4.set("width", str(SPREAD_WIDTH / 2 - (LEFT_PAGE_OFFSET + 6) * 2))
        # guide_l_rect_4.set("x", str(LEFT_PAGE_OFFSET + 6))
        # guide_l_rect_4.set("y", str(TOP_OFFSET + 6))

        # <g lyb:zHeight="1125" lyb:zWidth="875" lyb:zx="875" lyb:zy="0" se:guide="true" se:lock="L" id="guide_RIGHT">
        g_guide_r = etree.SubElement(svg, "g", id="guide_RIGHT")
        g_guide_r.set("{http://svg-edit.googlecode.com}guide", "true")
        g_guide_r.set("{http://svg-edit.googlecode.com}lock", "L")
        g_guide_r.set("{http://www.myyear.com}zHeight", "1125")
        g_guide_r.set("{http://www.myyear.com}zWidth", "875")
        g_guide_r.set("{http://www.myyear.com}zx", "0")
        g_guide_r.set("{http://www.myyear.com}zy", "0")

        # <title>Safety Zone RIGHT</title>
        guide_r_title = etree.SubElement(g_guide_r, "title")
        guide_r_title.text = "Safety Zone RIGHT"

        # <rect y="0" x="0" width="648" stroke="#0000ff" id="guide_LEFT_BLEED_rect" height="828" fill="none"/>
        guide_r_rect_1 = etree.SubElement(g_guide_r, "rect", id="guide_RIGHT_rect")
        guide_r_rect_1.set("fill", "none")
        guide_r_rect_1.set("height", str(SPREAD_HEIGHT))
        guide_r_rect_1.set("stroke", "#ff0000")
        guide_r_rect_1.set("width", str(SPREAD_WIDTH / 2))
        guide_r_rect_1.set("x", str(SPREAD_WIDTH / 2))
        guide_r_rect_1.set("y", "0")

        # <rect y="18" x="18" width="612" stroke="#00ff00" id="guide_LEFT_SAFETY_rect" height="792" fill="none"/>
        guide_r_rect_2 = etree.SubElement(g_guide_r, "rect", id="guide_RIGHT_CUT_rect")
        guide_r_rect_2.set("fill", "none")
        guide_r_rect_2.set("height", str(SPREAD_HEIGHT - 12))
        guide_r_rect_2.set("stroke", "#0000ff")
        guide_r_rect_2.set("width", str(SPREAD_WIDTH / 2 - 6))
        guide_r_rect_2.set("x", str(SPREAD_WIDTH / 2))
        guide_r_rect_2.set("y", str(6))

        # <rect y="9" x="9" width="630" stroke="#ff0000" id="guide_LEFT_CUT_rect" height="810" fill="none"
        # stroke-width="18" opacity="0.5" />
        guide_r_rect_3 = etree.SubElement(g_guide_r, "rect", id="guide_RIGHT_SAFETY_rect")
        guide_r_rect_3.set("fill", "none")
        guide_r_rect_3.set("height", str(SPREAD_HEIGHT - 60))
        guide_r_rect_3.set("stroke", "#00ff00")
        guide_r_rect_3.set("width", str(SPREAD_WIDTH / 2 - 36))
        guide_r_rect_3.set("x", str(SPREAD_WIDTH / 2 + 6))
        guide_r_rect_3.set("y", str(30))
        # # <rect y="0" x="648" width="648" stroke="#0000ff" id="guide_RIGHT_CUT_rect" height="828" fill="none"/>
        # guide_r_rect_1 = etree.SubElement(g_guide_r, "rect", id="guide_RIGHT_CUT_rect")
        # guide_r_rect_1.set("fill", "none")
        # guide_r_rect_1.set("height", str(SPREAD_HEIGHT))
        # guide_r_rect_1.set("stroke", "#0000ff")
        # guide_r_rect_1.set("width", str(SPREAD_WIDTH / 2))
        # guide_r_rect_1.set("x", str(SPREAD_WIDTH / 2))
        # guide_r_rect_1.set("y", "0")
        #
        # # <rect y="18" x="666" width="612" stroke="#00ff00" id="guide_RIGHT_SAFETY_rect" height="792" fill="none"/>
        # guide_r_rect_2 = etree.SubElement(g_guide_r, "rect", id="guide_RIGHT_SAFETY_rect")
        # guide_r_rect_2.set("fill", "none")
        # guide_r_rect_2.set("height", str(SPREAD_HEIGHT - TOP_OFFSET * 2))
        # guide_r_rect_2.set("stroke", "#00ff00")
        # guide_r_rect_2.set("width", str(SPREAD_WIDTH / 2 - LEFT_PAGE_OFFSET * 2))
        # guide_r_rect_2.set("x", str(SPREAD_WIDTH / 2 + LEFT_PAGE_OFFSET))
        # guide_r_rect_2.set("y", str(TOP_OFFSET))
        #
        # # <rect y="9" x="657" width="630" stroke="#ff0000" id="guide_LEFT_CUT_rect" height="810" fill="none"
        # # stroke-width="18" opacity="0.5" />
        # guide_r_rect_3 = etree.SubElement(g_guide_r, "rect", id="guide_LEFT_CUT_rect")
        # guide_r_rect_3.set("fill", "none")
        # guide_r_rect_3.set("height", str(SPREAD_HEIGHT - TOP_OFFSET))
        # guide_r_rect_3.set("stroke", "#ff0000")
        # guide_r_rect_3.set("width", str(SPREAD_WIDTH / 2 - LEFT_PAGE_OFFSET))
        # guide_r_rect_3.set("x", str(RIGHT_PAGE_OFFSET + LEFT_PAGE_OFFSET / 2))
        # guide_r_rect_3.set("y", str(TOP_OFFSET / 2))
        # guide_r_rect_3.set("opacity", "0.5")
        # guide_r_rect_3.set("stroke-width", str(TOP_OFFSET))
        #
        # # <rect y="24" x="672" width="600" stroke="#0000ff" id="guide_LEFT_SPACER_rect" height="780" fill="none"/>
        # guide_r_rect_4 = etree.SubElement(g_guide_l, "rect", id="guide_LEFT_SPACER_rect")
        # guide_r_rect_4.set("fill", "none")
        # guide_r_rect_4.set("height", str(SPREAD_HEIGHT - (LEFT_PAGE_OFFSET + 6) * 2))
        # guide_r_rect_4.set("stroke", "#0000ff")
        # guide_r_rect_4.set("width", str(SPREAD_WIDTH / 2 - (LEFT_PAGE_OFFSET + 6) * 2))
        # guide_r_rect_4.set("x", str(RIGHT_PAGE_OFFSET + LEFT_PAGE_OFFSET + 6))
        # guide_r_rect_4.set("y", str(TOP_OFFSET + 6))

        # <g se:guide="true" se:lock="L" id="my_gg_layer">
        my_grid_and_guides = etree.SubElement(svg, "g", id="my_gg_layer")
        my_grid_and_guides.set("{http://svg-edit.googlecode.com}guide", "true")
        my_grid_and_guides.set("{http://svg-edit.googlecode.com}lock", "L")

        outer_rect = etree.SubElement(g_guide_r, "rect", id="outer_rect")
        outer_rect.set("fill", "none")
        outer_rect.set("height", str(SPREAD_HEIGHT - 6))
        outer_rect.set("stroke", "#ff0000")
        outer_rect.set("stroke-width", "6")
        outer_rect.set("width", str(SPREAD_WIDTH - 6))
        outer_rect.set("x", str(3))
        outer_rect.set("y", str(3))
        outer_rect.set("stroke-opacity", "0.4")

        # <title>MY Grid and Guides Layer</title>
        my_grid_and_guides_title = etree.SubElement(my_grid_and_guides, "title")
        my_grid_and_guides_title.text = "MY Grid and Guides Layer"

        f = open(os.path.join(dir_path, 'tmp/%s_%s.svg' % (name, each[1])), 'w+b')
        f.write(stringify(etree.tostring(svg, pretty_print=True)))
        f.close()
