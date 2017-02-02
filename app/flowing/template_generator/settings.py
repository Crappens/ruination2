__author__ = 'bcrysler'

import os

# WIDTH = 612
# HEIGHT = 792
# LEFT_PAGE_OFFSET = 18
# TOP_OFFSET = 18
LEFT_PAGE_OFFSET = 30
TOP_OFFSET = 30
RIGHT_PAGE_OFFSET = 618
NAME_LENGTH = 130
PADDING = 6.0
# SPREAD_HEIGHT = 828
# SPREAD_WIDTH = 1296
SPREAD_HEIGHT = 804
SPREAD_WIDTH = 1236
PARTIAL_HEIGHT = (SPREAD_HEIGHT - 2 * TOP_OFFSET) * .85

dir_path = os.path.abspath(os.curdir)

if not os.path.exists(os.path.join(dir_path, "tmp")):
    os.makedirs(os.path.join(dir_path, "tmp"))