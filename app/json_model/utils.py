from math import cos, log, radians, sin
from reportlab.pdfbase.pdfmetrics import stringWidth


def convert_color(rgb_string):
    """Convert color represented by three int values to hex triplet.

    :param str rgb_string: string in format rgb(val1,val2,val3) to be converted
    :return: hex color representation
    :rtype: str
    """

    color_ints = rgb_string.replace('rgb(', '').rstrip(')').split(',')
    color_ints = map(int, color_ints)

    return '#%02x%02x%02x' % tuple(color_ints)


def convert_to_object_coord(pos, point):
    """
    :param pos:
    :param point:
    """

    vector_x = point['x'] - pos['x']
    vector_y = point['y'] - pos['y']

    angle = -1 * pos.get('r')
    r_vx, r_vy = rotate_by_degrees(angle, vector_x, vector_y)

    scale = pos.get('scale')

    return (r_vx / scale, r_vy / scale)


def generate_empty_model(add_first_layer=True):
    """Generate empty json model.

    :param bool add_first_layer: generate model with first layer
    :return: empty json model
    :rtype: dict
    """

    new_model = {
        'svgObjectsLinks': {},
        'svgLayers': [],
        'layersFoldersTree': {
            'id': 'rootFolder',
            'name': 'rootFolder',
            'folderType': 'root',
            'visible': True,
            'folders': [],
        },
        'svgObjects': {},
        # 'selectedObjectId': None,
        # 'postAction': None,
        'editorSettings': {
            'rulers': {
                'guides': [],
            },
        },
    }

    if add_first_layer:
        new_model['svgLayers'].append({
            'id': 'Layer1',
            'visible': True,
            'selected': True,
            'svgObjects': [],
        })
        new_model['layersFoldersTree']['folders'].append({
            'id': 'Layer1',
            'name': 'Layer1',
            'folderType': 'layer',
        })

    return new_model


def rotate_by_degrees(angle, pos_x, pos_y):
    """
    https://github.com/maxkueng/victor/blob/master/build/victor.js
    """

    angle = radians(angle)

    return (
        (pos_x * cos(angle)) - (pos_y * sin(angle)),
        (pos_x * sin(angle)) + (pos_y * cos(angle))
    )


TEXT_PADDING = 3
MAX_PADDING_MODIFIER = 5


def get_font_height_modifier(font_size):
    if font_size < 10:
        return 2
    elif font_size < 18:
        return 3
    elif font_size < 30:
        return 4
    elif font_size < 40:
        return 6
    elif font_size < 50:
        return 8
    elif font_size < 62:
        return 9
    elif font_size < 70:
        return 10
    elif font_size < 81:
        return 12
    elif font_size < 110:
        return 16
    elif font_size < 120:
        return 18
    else:
        return 22


def get_height_modifier(svg_obj, height, line_num):
    if not list(svg_obj):
        # empty text box
        return

    max_font_size = max([
        int(node.get('font-size')) for node in list(svg_obj)
    ])

    font_height_mod = get_font_height_modifier(max_font_size)

    expected_height = (max_font_size + font_height_mod) * line_num + 2 * TEXT_PADDING

    return None if expected_height < height else expected_height


def get_width_modifier(svg_obj, width):
    if not list(svg_obj):
        return

    width_list = []
    for node in list(svg_obj):
        if not node.text:
            continue

        line_len = stringWidth(node.text, node.get('font-family'), float(node.get('font-size')))

        if node.get('dy') is None and width_list:
            width_list[-1] += line_len
            continue

        width_list.append(line_len)

    if not width_list:
        return

    max_text_width = max(width_list) + 2 * TEXT_PADDING

    return None if max_text_width < width else max_text_width


def get_text_padding_modifier(svg_obj, height, line_num):
    if not list(svg_obj):
        # empty text box
        return

    max_font_size = max([
        int(node.get('font-size')) for node in list(svg_obj)
    ])

    if max_font_size <= 10:
        return 1 if line_num > 1 else 0

    font_mod = 2 * int(log(max_font_size))

    text_height = (max_font_size + font_mod) * line_num
    padding = line_num * 2 * TEXT_PADDING

    if (height - text_height) > padding:
        return

    padding_modifier = max(int(log(max_font_size)), 2)

    while (height + padding_modifier * TEXT_PADDING - text_height) < padding:
        padding_modifier += 1
        if padding_modifier == MAX_PADDING_MODIFIER:
            break

    return padding_modifier
