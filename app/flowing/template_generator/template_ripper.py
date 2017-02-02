__author__ = 'bcrysler'

from itertools import chain
from lxml import etree

import copy
import os

try:
    from test_template import data
except:
    data = [
        {"name": "None",  # No template to rip
         "svg": ''''''}]

dir_path = "finished_templates"


# Strips newlines, tabs and all extra spacing out of the prettified bs4 soup object
def stringify(prettified):
    finalized = prettified.replace('\n', '').replace('\t', '')
    while ' <' in finalized or '> ' in finalized:
        finalized = finalized.replace(' <', '<')
        finalized = finalized.replace('> ', '>')
    return finalized

for page in data:
    svg = etree.fromstring(page["svg"])

    background_layer, guide_left_layer, guide_right_layer, gg_layer, folio_layer, layer_1 = (None,) * 6

    for child in list(svg):
        temp_id = child.get("id")
        if temp_id == 'background_layer':
            background_layer = child
        elif temp_id == 'guide_LEFT':
            guide_left_layer = child
        elif temp_id == 'guide_RIGHT':
            guide_right_layer = child
        elif temp_id == "gg_layer":
            gg_layer = child
        elif temp_id == "folio_layer":
            folio_layer = child
        elif temp_id == "layer_1":
            layer_1 = child

    left_page = []
    right_page = []

    page_width = svg.get("width")
    middle_line = int(page_width) / 2

    for element in layer_1:
        # This MUST be a if/else if.  DO NOT refactor in to an if/else.
        if element.tag == "{http://www.w3.org/2000/svg}g":
            child_rect = [x for x in list(element) if x.tag == "{http://www.w3.org/2000/svg}rect"][0]
            if float(child_rect.get("x")) < middle_line:
                left_page.append(element)
            else:
                right_page.append(element)
        elif element.tag == "{http://www.w3.org/2000/svg}rect":
            if float(element.get("x")) < middle_line:
                left_page.append(element)
            else:
                right_page.append(element)

    nsmap = {None: 'http://www.w3.org/2000/svg',
             'se': 'http://svg-edit.googlecode.com',
             'lyb': 'http://www.myyear.com',
             'xlink': "http://www.w3.org/1999/xlink"}

    left_svg = etree.Element("svg", nsmap=nsmap)
    left_svg.set("height", "804")
    left_svg.set("width", "1236")
    right_svg = etree.Element("svg", nsmap=nsmap)
    right_svg.set("height", "804")
    right_svg.set("width", "1236")
    full_svg = etree.Element("svg", nsmap=nsmap)
    full_svg.set("height", "804")
    full_svg.set("width", "1236")

    for canvas in [left_svg, right_svg, full_svg]:
        canvas.append(background_layer)

    left_layer_1 = etree.SubElement(left_svg, "g", id="layer_1")
    right_layer_1 = etree.SubElement(right_svg, "g", id="layer_1")
    full_layer_1 = etree.SubElement(full_svg, "g", id="layer_1")

    print left_page
    print right_page

    for element in left_page:
        left_layer_1.append(copy.deepcopy(element))

    for element in right_page:
        right_layer_1.append(copy.deepcopy(element))

    for element in chain(left_page, right_page):
        full_layer_1.append(copy.deepcopy(element))

    layer_1_title = etree.Element("title")
    layer_1_title.text = "Layer 1"
    left_layer_1.insert(0, copy.deepcopy(layer_1_title))
    right_layer_1.insert(0, copy.deepcopy(layer_1_title))
    full_layer_1.insert(0, copy.deepcopy(layer_1_title))

    left_svg.append(left_layer_1)
    right_svg.append(right_layer_1)
    full_svg.append(full_layer_1)

    for each in [left_svg, full_svg, right_svg]:
        each.append(copy.deepcopy(guide_left_layer))
        each.append(copy.deepcopy(guide_right_layer))
        each.append(copy.deepcopy(gg_layer))
        each.append(copy.deepcopy(folio_layer))

    f = open(os.path.join(dir_path, '%s_%s.svg' % (page["name"], "left")), 'wb+')
    f.write(stringify(etree.tostring(left_svg, pretty_print=True)))
    f.close()

    f = open(os.path.join(dir_path, '%s_%s.svg' % (page["name"], "right")), 'wb+')
    f.write(stringify(etree.tostring(right_svg, pretty_print=True)))
    f.close()

    f = open(os.path.join(dir_path, '%s_%s.svg' % (page["name"], "full")), 'wb+')
    f.write(stringify(etree.tostring(full_svg, pretty_print=True)))
    f.close()
