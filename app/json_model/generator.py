from collections import Counter
from lxml.etree import fromstring

from app.json_model.utils import (convert_color, convert_to_object_coord, generate_empty_model, get_height_modifier,
    get_width_modifier, TEXT_PADDING)
from app.ripper.ripper import register_fonts


class JSONModelGenerator(object):

    LAYERS_SKIP = ('background_layer', 'guide_LEFT', 'guide_RIGHT', 'my_gg_layer', 'gg_layer')
    POLYGON_C_COORDS = (('x', 'y'), ('x1', 'y1'), ('x2', 'y2'))
    TEXT_OPTIONAL_PARAMS = (
        ('stroke', 'stroke', lambda x: x),
        ('stroke-width', 'stroke-width', int),
        ('%sparagraphAlignment', 'paragraphAlignment', int),
        ('text-decoration', 'text-decoration', lambda x: x)
    )
    TEXT_ANCHOR_MAPPING = {
        'start': 1,  # ALIGN_LEFT
        'middle': 4,  # ALIGN_CENTER
        'end': 2,  # ALIGN_RIGHT
    }

    def __init__(self):
        self.current_layer = None
        self.json_model = None
        self.obj_counter = Counter()

        self.clip_paths = {}
        self.filter_mapping = {}

        # namespaces
        self.ns = None
        self.lyb_ns = None
        self.xlink_ns = None

        # register_fonts
        register_fonts()

    def add_new_layer(self, layer_id):
        """Create new layer in the model.

        :param string layer_id: SVG layer id
        :return: current layer object
        """

        if layer_id is None:
            layer_id = 'layer_%s' % self.obj_counter.get('layer', 0)
            self.obj_counter['layer'] += 1

        new_layer = {
            'id': layer_id,
            'name': layer_id,
            'visible': True,
            'svgObjects': [],
        }

        # append new layer to the model
        self.json_model['svgLayers'].append(new_layer)
        self.json_model['layersFoldersTree']['folders'].append({
            'id': layer_id,
            'name': layer_id,
            'folderType': 'layer'
        })

        return new_layer

    def add_new_object(self, obj_type, pos):
        return {
            'type': obj_type,
            'position': dict(pos, r=0, scale=1),
        }

    def add_new_object_to_layer(self, new_obj):
        # add to object mapping
        self.json_model['svgObjects'][new_obj['id']] = new_obj

        # add object to current layer
        if new_obj.get('photobox'):
            obj_photos = [
                key for key, value in self.json_model['svgObjectsLinks'].get(new_obj['id'], {}).iteritems()
                if 'photoboxLink' in value and value['photoboxLink']['linkData']['photobox']
            ]

            if obj_photos and self.current_layer['svgObjects'][-1] == obj_photos[0]:
                # insert object before it's linked photo
                self.current_layer['svgObjects'].insert(-1, new_obj['id'])
                return

        # append to current layer
        self.current_layer['svgObjects'].append(new_obj['id'])

    def add_obj_id(self, obj, obj_id):
        if not obj_id:
            obj_id = '%s%s' % (obj['type'], self.obj_counter.get(obj['type'], 0))
            self.obj_counter[obj['type']] += 1

        obj['id'] = obj_id

    def add_photobox_attrs(self, obj, svg_obj):
        if obj['id'].startswith('border_') \
          or '%sdropTarget' % self.lyb_ns in svg_obj.attrib \
          or '%sdroptarget' % self.lyb_ns in svg_obj.attrib:
            obj['photobox'] = True
            # remove "border_" from id
            obj['id'] = obj['id'].replace('border_', '')

    def add_obj_link(self, obj1, obj2, inner_data):
        self.json_model['svgObjectsLinks'][obj1] = {
            obj2: inner_data
        }
        self.json_model['svgObjectsLinks'][obj2] = {
            obj1: inner_data
        }

    # attributes converters
    def convert_color_params(self, obj, svg_obj):
        fill = svg_obj.get('fill')
        if fill and fill != 'none':
            obj['fill'] = fill

        # TODO: uncomment when supported by FE
        # fill_opacity = svg_obj.get('fill-opacity')
        # if fill_opacity:
        #     obj['fillOpacity'] = fill_opacity

    def convert_round_borders(self, obj, svg_obj):
        if svg_obj.get('rx'):
            obj['borderRadiusX'] = svg_obj.get('rx')
        if svg_obj.get('ry'):
            obj['borderRadiusY'] = svg_obj.get('ry')

    def convert_border_params(self, obj, svg_obj):
        if svg_obj.get('stroke-width'):
            obj['borderWidth'] = float(svg_obj.get('stroke-width'))

        border_color = svg_obj.get('stroke')
        if border_color and border_color != 'none':
            obj['borderColor'] = border_color

        stroke_dasharray = svg_obj.get('stroke-dasharray')
        if stroke_dasharray and stroke_dasharray != 'none':
            obj['borderDash'] = stroke_dasharray

    def convert_transform(self, obj, svg_obj):
        rotation = svg_obj.get('transform')
        if not rotation:
            if svg_obj.getparent().get('%stext-group' % self.lyb_ns) == 'true':
                rotation = svg_obj.getparent().get('transform')
            elif obj['type'] == 'photo':
                rotation = svg_obj.getparent().getparent().get('transform')
            elif obj.get('photobox'):
                rotation = svg_obj.getparent().get('transform')

        if rotation and 'rotate' in rotation:
            obj['position']['r'] = float(rotation.split("(")[1].split(" ")[0])

    def convert_filter(self, obj, svg_obj):
        svg_filter = svg_obj.get('filter')
        if not svg_filter:
            return

        obj['filter'] = svg_filter.split('#')[1].replace(')', '')

        if obj['filter'].startswith('filter_'):
            # if not found -> raise an error
            try:
                obj['filter'] = self.filter_mapping[obj['filter']]
            except KeyError:
                # TODO: remove unknown filters
                print 'Filter "%s" not found' % obj['filter']
                del obj['filter']

    def convert_custom_attributes(self, obj, svg_obj):
        if svg_obj.get('%stextHole' % self.lyb_ns) == 'true':
            obj['textHole'] = True

    # other heplers
    def process_defs_layer(self, defs_layer):
        for node in list(defs_layer):
            tag = node.tag.replace(self.ns, '')

            if tag == 'clipPath':
                if not len(node):
                    # missing child node
                    # -> ignore
                    continue

                self.clip_paths[node.get('id')] = node[0].get('%shref' % self.xlink_ns).strip('#')
                continue

            if tag == 'filter':
                for child_node in list(node):
                    if child_node.get('filter_purpose') == 'drop_shadow':
                        # guess that the filter is drop shadow
                        self.filter_mapping[node.get('id')] = 'dropShadow'
                        break

    # main generate function
    def generate(self, svg):
        """Generate JSON model from given svg.

        :param str svg: svg to be "converted" to json model
        """

        # get empty model
        self.json_model = generate_empty_model(add_first_layer=False)

        # parse input SVG
        parsed_svg = fromstring(svg)

        # get namespaces from parsed_svg
        self.ns = '{%s}' % parsed_svg.nsmap.get(None)
        self.lyb_ns = '{%s}' % parsed_svg.nsmap.get('lyb')
        self.xlink_ns = '{%s}' % parsed_svg.nsmap.get('xlink')

        # handle defs layer
        defs_layer = parsed_svg.xpath(
            'ns:defs', namespaces={
                'ns': parsed_svg.nsmap.get(None)
            }
        )
        if defs_layer:
            self.process_defs_layer(defs_layer[0])

        # convert svg to model
        for layer in list(parsed_svg):
            # skip background layer
            if layer.get('id') in self.LAYERS_SKIP:
                continue

            # folio_layer -> should be part of the JSON model
            # page numbers
            if layer.get('id') == 'folio_layer':
                # temporary skip of folio layer -> until it's supported by json model
                continue

            if 'defs' in layer.tag:
                # skip defs layer
                continue

            self.current_layer = self.add_new_layer(layer.get('id'))

            for obj in layer.getiterator():
                tag = obj.tag.replace(self.ns, '')

                if tag == 'title':
                    self.current_layer['name'] = obj.text
                elif tag == 'rect':
                    self.handle_rect(obj)
                elif tag == 'ellipse':
                    self.handle_ellipse(obj)
                elif tag == 'line':
                    self.handle_line(obj)
                elif tag == 'path':
                    self.handle_path(obj)
                elif tag == 'image':
                    self.handle_image(obj)
                elif tag == 'text':
                    # handle also tspan-s inside text tag
                    self.handle_text(obj)

        return self.json_model

    # object handlers
    def handle_ellipse(self, svg_obj):
        new_obj = self.add_new_object('ellipse', {
            'x': float(svg_obj.get('cx')),
            'y': float(svg_obj.get('cy')),
            'width': float(svg_obj.get('rx')) * 2.0,
            'height': float(svg_obj.get('ry')) * 2.0,
        })

        self.add_obj_id(new_obj, svg_obj.get('id'))
        self.add_photobox_attrs(new_obj, svg_obj)

        self.convert_color_params(new_obj, svg_obj)
        self.convert_border_params(new_obj, svg_obj)
        self.convert_transform(new_obj, svg_obj)
        self.convert_filter(new_obj, svg_obj)
        self.convert_custom_attributes(new_obj, svg_obj)

        self.add_new_object_to_layer(new_obj)

    def handle_image(self, svg_obj):
        width = float(svg_obj.get('width'))
        height = float(svg_obj.get('height'))

        new_obj = self.add_new_object('photo', {
            'width': width,
            'height': height,
            'x': float(svg_obj.get('x')) + (width / 2.0),
            'y': float(svg_obj.get('y')) + (height / 2.0),
        })

        img_id = svg_obj.get('id')
        if not img_id:
            # try to use srcId attr
            img_id = svg_obj.get('%ssrcId' % self.lyb_ns)

        self.add_obj_id(new_obj, img_id)

        new_obj['src'] = svg_obj.get('%shref' % self.xlink_ns)

        self.convert_transform(new_obj, svg_obj)
        self.convert_filter(new_obj, svg_obj)

        raw_path_id = svg_obj.getparent().get('clip-path')
        path_id = raw_path_id.split('#')[1].rstrip(')')
        try:
            photobox_id = self.clip_paths[path_id]
        except KeyError:
            # clippath id not found --> try to find rect sibling and use it
            rect_siblings = [node for node in list(svg_obj.getparent().getparent()) if 'rect' in node.tag]
            if not rect_siblings:
                rect_siblings = [node for node in list(svg_obj.getparent()) if 'rect' in node.tag]

            photobox_id = rect_siblings[0].get('id')

        if photobox_id.startswith('border_'):
            photobox_id = photobox_id.replace('border_', '')

        self.add_obj_link(new_obj['id'], photobox_id, {'photoboxLink': {'linkData': {'photobox': True}}})

        new_obj['clipPath'] = '%s-clip-path' % photobox_id

        self.add_new_object_to_layer(new_obj)

    def handle_line(self, svg_obj):
        pos_x1 = float(svg_obj.get('x1'))
        pos_y1 = float(svg_obj.get('y1'))

        pos_x2 = float(svg_obj.get('x2'))
        pos_y2 = float(svg_obj.get('y2'))

        new_obj = self.add_new_object('line', {
            'width': abs(pos_x2 - pos_x1),
            'height': abs(pos_y2 - pos_y1),
            'x': pos_x1 + (pos_x2 - pos_x1) / 2,
            'y': pos_y1 + (pos_y2 - pos_y1) / 2,
        })

        self.add_obj_id(new_obj, svg_obj.get('id'))

        new_obj['x1'], new_obj['y1'] = convert_to_object_coord(
            new_obj['position'], {'x': pos_x1, 'y': pos_y1}
        )

        new_obj['x2'], new_obj['y2'] = convert_to_object_coord(
            new_obj['position'], {'x': pos_x2, 'y': pos_y2}
        )

        self.convert_border_params(new_obj, svg_obj)
        self.convert_filter(new_obj, svg_obj)
        self.convert_transform(new_obj, svg_obj)

        self.add_new_object_to_layer(new_obj)

    def handle_path(self, svg_obj):
        path_d = svg_obj.get('d').strip()

        if path_d.endswith('Z'):
            path_type = 'polygon'
            path_d = path_d.rstrip('Z').strip()
        else:
            path_type = 'path'

        coords = path_d.split(' ')

        x_coords = []
        y_coords = []
        raw_polygon = []

        i = 0
        while i < len(coords):
            if coords[i] == 'C':
                x_coords.extend([float(coords[i + 1]), float(coords[i + 3]), float(coords[i + 5])])
                y_coords.extend([
                    float(coords[i + 2].rstrip(',')), float(coords[i + 4].rstrip(',')), float(coords[i + 6])
                ])

                raw_polygon.append({
                    'cmd': 'C',
                    'x': float(coords[i + 5]), 'y': float(coords[i + 6]),
                    'x1': float(coords[i + 1]), 'y1': float(coords[i + 2].rstrip(',')),
                    'x2': float(coords[i + 3]), 'y2': float(coords[i + 4].rstrip(',')),
                })

                i += 7
            else:
                x_coords.append(float(coords[i + 1]))
                y_coords.append(float(coords[i + 2]))

                raw_polygon.append({
                    'cmd': coords[i], 'x': float(coords[i + 1]), 'y': float(coords[i + 2]),
                })
                i += 3

        # find center
        min_x = min(x_coords)
        max_x = max(x_coords)
        min_y = min(y_coords)
        max_y = max(y_coords)

        new_obj = self.add_new_object(path_type, {
            'width': abs(max_x - min_x),
            'height': abs(max_y - min_y),
            'x': min_x + (max_x - min_x) / 2,
            'y': min_y + (max_y - min_y) / 2,
        })

        new_obj['polygon'] = []
        for item in raw_polygon:
            if item['cmd'] == 'C':
                for var_x, var_y in self.POLYGON_C_COORDS:
                    item[var_x], item[var_y] = convert_to_object_coord(
                        new_obj['position'], {'x': item[var_x], 'y': item[var_y]}
                    )
            else:
                item['x'], item['y'] = convert_to_object_coord(
                    new_obj['position'], item
                )

            new_obj['polygon'].append(item)

        self.add_obj_id(new_obj, svg_obj.get('id'))
        self.add_photobox_attrs(new_obj, svg_obj)

        self.convert_color_params(new_obj, svg_obj)
        self.convert_border_params(new_obj, svg_obj)
        self.convert_filter(new_obj, svg_obj)
        self.convert_custom_attributes(new_obj, svg_obj)

        self.add_new_object_to_layer(new_obj)

    def handle_rect(self, svg_obj):
        width = float(svg_obj.get('width'))
        height = float(svg_obj.get('height'))

        new_obj = self.add_new_object('rect', {
            'width': width,
            'height': height,
            'x': float(svg_obj.get('x')) + (width / 2.0),
            'y': float(svg_obj.get('y')) + (height / 2.0),
        })

        self.add_obj_id(new_obj, svg_obj.get('id'))
        self.add_photobox_attrs(new_obj, svg_obj)

        self.convert_color_params(new_obj, svg_obj)
        self.convert_round_borders(new_obj, svg_obj)
        self.convert_border_params(new_obj, svg_obj)
        self.convert_transform(new_obj, svg_obj)
        self.convert_filter(new_obj, svg_obj)
        self.convert_custom_attributes(new_obj, svg_obj)

        self.add_new_object_to_layer(new_obj)

    def handle_text(self, svg_obj):
        new_obj = self.add_new_object('text', {})
        new_obj['text'] = []

        self.add_obj_id(new_obj, svg_obj.get('id'))

        # get position from rectangle
        rect_id = self.current_layer['svgObjects'][-1]
        new_obj['clipPath'] = '%s-clip-path' % rect_id
        self.add_obj_link(new_obj['id'], rect_id, {'textLink': {'linkData': {'textOverflowing': True}}})

        # enable to show overflown text
        # new_obj['expandText'] = True
        # new_obj['overflown'] = True

        prev_tspan_end = None
        paragraph_alignment = self.TEXT_ANCHOR_MAPPING.get(svg_obj.get('text-anchor'), None)
        for node in list(svg_obj):
            node_text = node.text
            if node_text is None:
                continue

            if '\t' in node_text:
                node_text = node_text.replace('\t', '')

            node_attrs = {
                'font-family': node.get('font-family'),
                'font-size': float(node.get('font-size')),
                'fill': node.get('fill'),
                'font-weight': node.get('font-weight'),
                'font-style': node.get('font-style'),
            }

            if node_attrs['font-style'] in ['undefined', None]:
                node_attrs['font-style'] = 'normal'

            if node_attrs['font-weight'] in ['undefined', None]:
                node_attrs['font-weight'] = 'normal'

            if node_attrs['fill'].startswith('rgb'):
                node_attrs['fill'] = convert_color(node_attrs['fill'])

            for svg_param, json_param, convertor in self.TEXT_OPTIONAL_PARAMS:
                if '%s' in svg_param:
                    svg_param = svg_param % self.lyb_ns

                if node.get(svg_param):
                    node_attrs[json_param] = convertor(node.get(svg_param))

            if paragraph_alignment and 'paragraphAlignment' not in node_attrs:
                node_attrs['paragraphAlignment'] = paragraph_alignment

            parts = node_text.split(' ')
            for part in parts:
                if new_obj['text'] and not part and new_obj['text'][-1][0][0][-1] == ' ':
                    # put all spaces into one object - instead of multiple ones
                    new_obj['text'][-1][0][0] = new_obj['text'][-1][0][0] + ' '
                    continue

                new_obj['text'].append([[
                    part or ' ',
                    node_attrs.copy()
                ]])

                if 'paragraphAlignment' in node_attrs:
                    # use it only for first "tspan" of the text
                    del node_attrs['paragraphAlignment']

                # add space
                new_obj['text'].append([[
                    ' ',
                    node_attrs.copy()
                ]])

            if paragraph_alignment and 'paragraphAlignment' not in new_obj['text'][-1][0][1]:
                new_obj['text'][-1][0][1]['paragraphAlignment'] = paragraph_alignment

            # change last space with new line
            # --> each tspan represents new line
            new_obj['text'][-1][0][0] = '\n'

            if node.get('dy') is None and prev_tspan_end is not None:
                new_obj['text'][prev_tspan_end][0][0] = ' '

            prev_tspan_end = len(new_obj['text']) - 1

        # remove spaces and newlines from end of the text
        while len(new_obj['text']) and new_obj['text'][-1][0][0] in [' ', '\n']:
            new_obj['text'].pop(-1)

        line_num = 1 + len([
            item for item in new_obj['text'] if item[0][0] == '\n'
        ])

        expected_height = get_height_modifier(
            svg_obj,
            self.json_model['svgObjects'][rect_id]['position']['height'],
            line_num
        )
        expected_width = get_width_modifier(
            svg_obj,
            self.json_model['svgObjects'][rect_id]['position']['width']
        )

        if expected_height:
            original_height = self.json_model['svgObjects'][rect_id]['position']['height']
            self.json_model['svgObjects'][rect_id]['position']['height'] = expected_height
            self.json_model['svgObjects'][rect_id]['position']['y'] -= original_height / 2.0
            self.json_model['svgObjects'][rect_id]['position']['y'] += expected_height / 2.0

        if expected_width:
            original_width = self.json_model['svgObjects'][rect_id]['position']['width']
            self.json_model['svgObjects'][rect_id]['position']['width'] = expected_width
            self.json_model['svgObjects'][rect_id]['position']['x'] -= original_width / 2.0
            self.json_model['svgObjects'][rect_id]['position']['x'] += expected_width / 2.0

        if expected_height or expected_width:
            # shift x + y of text padding
            self.json_model['svgObjects'][rect_id]['position']['x'] -= TEXT_PADDING
            self.json_model['svgObjects'][rect_id]['position']['y'] -= TEXT_PADDING

        rect_pos = self.json_model['svgObjects'][rect_id]['position']
        self.json_model['svgObjects'][rect_id]['textLink'] = new_obj['id']

        new_obj['position'] = rect_pos.copy()

        self.add_new_object_to_layer(new_obj)
