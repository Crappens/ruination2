__author__ = 'bcrysler'


from copy import deepcopy
from lxml import etree


class TextBox():
    def __init__(self, data):
        self.raw = data['raw']
        self.id = data['id']
        self.x = float(data['x'])
        self.y = float(data['y'])
        self.width = float(data['width'])
        self.height = float(data['height'])
        self.place = 0

    def __repr__(self):
        return "%s, %s : TextBox" % (self.x, self.y)

    def cX(self):
        return self.x + self.width / 2

    def cY(self):
        return self.y + self.height / 2

    def area(self):
        return self.width * self.height


class Rectangle():
    def __init__(self, data):
        self.raw = data['raw']
        self.id = data['id']
        self.x = float(data['x'])
        self.y = float(data['y'])
        self.width = float(data['width'])
        self.height = float(data['height'])
        self.place = 0

    def __repr__(self):
        return "%s, %s : Rectangle" % (self.x, self.y)

    def cX(self):
        return self.x + self.width / 2

    def cY(self):
        return self.y + self.height / 2

    def area(self):
        return self.width * self.height


class Spread():
    def __init__(self, data):
        self.left_page = data['left']
        self.right_page = data['right']
        self.left_count = len(self.left_page)
        self.right_count = len(self.right_page)
        self.total_count = self.left_count + self.right_count


class Rwar():
    def __init__(self, data):
        self.svg_open = None
        self.background = data['background']
        self.layer_one = data['layer_one']
        self.guide_left = data['guide_left']
        self.guide_right = data['guide_right']
        self.spread = None


class SVGDoc():
    def __init__(self, data):
        self.original = data

    def new_svg_tag(self):
        dimensions = self.original.get("viewBox").split(" ")
        height = dimensions[3]
        width = dimensions[2]
        svg = etree.Element("{http://www.w3.org/2000/svg}svg", nsmap={None: 'http://www.w3.org/2000/svg',
                                                                      'se': 'http://svg-edit.googlecode.com',
                                                                      'lyb': 'http://www.myyear.com',
                                                                      'xlink': "http://www.w3.org/1999/xlink"})
        svg.set("width", str(width))
        svg.set("height", str(height))

        for child in list(self.original):
            svg.append(deepcopy(child))

        self.original = svg

    def remove_pattern_tag(self):
        defs = (x for x in list(self.original) if "defs" in x.tag).next()
        for child in defs:
            if "pattern" in child.tag:
                defs.remove(child)

    def fix_tags(self):
        for each in self.original.getiterator():
            if "{http://www.w3.org/2000/svg}" not in each.tag:
                each.tag = "{http://www.w3.org/2000/svg}" + each.tag


class XSDException(Exception):
    """An exception for when the post data is incomplete."""

    def __init__(self, message, status_code):
        self.status_code = status_code
        super(XSDException, self).__init__(message)


class LimeException(Exception):
    """An exception for when Lime returns an empty list for a project ID."""

    def __init__(self, message, status_code):
        self.status_code = status_code
        super(LimeException, self).__init__(message)


class SheetCountException(Exception):
    """An exception for when flowing requires more template boxes than are provided."""

    def __init__(self, message, status_code):
        self.status_code = status_code
        super(SheetCountException, self).__init__(message)


class ImproperRequestException(Exception):
    """An exception for when the post data is incomplete."""

    def __init__(self, message, status_code):
        self.status_code = status_code
        super(ImproperRequestException, self).__init__(message)


class PageInUseException(Exception):
    """An exception for when the post data is incomplete."""

    def __init__(self, message, status_code):
        self.status_code = status_code
        super(PageInUseException, self).__init__(message)


class PageLockException(Exception):
    """An exception for when the post data is incomplete."""

    def __init__(self, message, status_code):
        self.status_code = status_code
        super(PageLockException, self).__init__(message)
