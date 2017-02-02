__author__ = 'bcrysler'


class TextBox():
    def __init__(self, data):
        self.x = float(data['x'])
        self.y = float(data['y'])
        self.width = float(data['width'])
        self.height = float(data['height'])
        self.extra = data['extra']

    def __repr__(self):
        return "TextBox -- x: %s, y: %s, width: %s, height: %s" % (self.x, self.y, self.width, self.height)

    def get_cx(self):
        return self.x + self.width / 2

    def get_cy(self):
        return self.y + self.height / 2

    def get_rx(self):
        return self.x + self.width


class Rectangle():
    def __init__(self, data):
        self.x = float(data['x'])
        self.y = float(data['y'])
        self.width = float(data['width'])
        self.height = float(data['height'])
        self.extra = data['extra']
        self.column = data['column']
        self.row = data['row']

    def __repr__(self):
        return "Rectangle -- x: %s, y: %s, width: %s, height: %s" % (self.x, self.y, self.width, self.height)

    def get_cx(self):
        return self.x + self.width / 2

    def get_cy(self):
        return self.y + self.height / 2

    def get_rx(self):
        return self.x + self.width


class Teacher():
    def __init__(self, data):
        self.top_left = data['top_left']
        self.top_right = data['top_right']
        self.bottom_left = data['bottom_left']
        self.bottom_right = data['bottom_right']

    def get_width(self):
        return self.top_left.width * 2

    def get_height(self):
        return self.top_left.height * 2

    def get_x(self):
        return self.top_left.x + (self.top_right.get_rx() - self.top_left.x - self.get_width()) / 2

    def get_y(self):
        temp = (self.bottom_left.y + self.bottom_left.height - self.top_left.y - self.get_height())
        return self.top_left.y + temp / 2


class Spread():
    def __init__(self, data):
        self.left_page = data['left']
        self.right_page = data['right']
        self.left_count = self.left_page.__len__()
        self.right_count = self.right_page.__len__()
        self.total_count = self.left_count + self.right_count
