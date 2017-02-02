__author__ = 'bcrysler'


from app.flowing.template_generator.generate import test_thoughts


'''rows -> int
columns -> int
names -> int:
    1 -> Names under pictures
    2 -> Names on outer edges
    3 -> Names on inner edges
    *4 -> Names on left edge, spanning both pages
    *5 -> Names on right edge, spanning both pages
    6 -> Names above pictures
    7 -> Names on left edges
    8 -> Names on right edges
teacher -> int:
    0 -> No teacher
    1 -> Teacher, single, top left corners
    2 -> Double (1)
    3 -> Teacher, single, top right corners
    4 -> Double (3)
    5 -> Teacher, single, outer corners
    6 -> Double (5)
    7 -> Teacher, single, inner corners
    8 -> Double (7)
    9 -> Teacher, double, alternating corners, top left both pages
    10 -> Teacher, double, alternating corners, top right both pages
    11 -> Teacher, double, alternating corners, top outer both pages
    12 -> Teacher, double, alternating corners, top inner both pages
fill_page -> bool
dual_classes -> bool
font_size -> int
font_color -> str
font_style -> str
top_title -> bool
side_title -> int:
    0 -> None
    1 -> outer edges
    2 -> inner edges
    3 -> left edges
    4 -> right edges


* = not available as of now'''


test_thoughts(rows=6, columns=4, names=2, teacher=7, fill_page=True, side_title=0, top_title=True, font_size=10,
              save_name=1, top_width=50, side_width=50, percent=0.7)
test_thoughts(rows=5, columns=4, names=2, teacher=7, fill_page=True, side_title=0, top_title=True, font_size=10, 
              save_name=2, top_width=50, side_width=50, percent=0.7)
test_thoughts(rows=4, columns=4, names=2, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=10, 
              save_name=3, top_width=50, side_width=50, percent=0.7)
test_thoughts(rows=6, columns=4, names=1, teacher=7, fill_page=True, side_title=0, top_title=True, font_size=9, 
              save_name=4, top_width=50, side_width=50, percent=0.7)
test_thoughts(rows=5, columns=4, names=1, teacher=7, fill_page=True, side_title=0, top_title=True, font_size=10, 
              save_name=5, top_width=50, side_width=50, percent=0.7)
test_thoughts(rows=4, columns=4, names=1, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=10, 
              save_name=6, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=6, columns=4, names=2, teacher=0, fill_page=True, side_title=0, top_title=True, font_size=10, 
              save_name=7, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=5, columns=4, names=2, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=10, 
              save_name=8, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=4, columns=4, names=2, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=10, 
              save_name=9, top_width=50, side_width=50, percent=0.78)
test_thoughts(rows=6, columns=4, names=1, teacher=0, fill_page=True, side_title=0, top_title=True, font_size=10, 
              save_name=10, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=5, columns=4, names=1, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=10, 
              save_name=11, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=4, columns=4, names=1, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=10, 
              save_name=12, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=4, columns=4, names=2, teacher=8, fill_page=True, side_title=0, top_title=True, font_size=10, 
              save_name=13, top_width=50, side_width=100, percent=0.70)
test_thoughts(rows=7, columns=5, names=2, teacher=7, fill_page=True, side_title=0, top_title=True, font_size=10, 
              save_name=14, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=6, columns=5, names=2, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=10, 
              save_name=15, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=5, columns=5, names=2, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=10, 
              save_name=16, top_width=50, side_width=50, percent=0.77)
test_thoughts(rows=7, columns=5, names=1, teacher=7, fill_page=True, side_title=0, top_title=True, font_size=9, 
              save_name=17, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=6, columns=5, names=1, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=9, 
              save_name=18, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=5, columns=5, names=1, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=19, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=7, columns=5, names=2, teacher=0, fill_page=True, side_title=0, top_title=True, font_size=10,
              save_name=20, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=6, columns=5, names=2, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=10,
              save_name=21, top_width=50, side_width=50, percent=0.80)
test_thoughts(rows=5, columns=5, names=2, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=10,
              save_name=22, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=7, columns=5, names=1, teacher=0, fill_page=True, side_title=0, top_title=True, font_size=10,
              save_name=23, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=6, columns=5, names=1, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=24, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=5, columns=5, names=1, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=25, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=4, columns=5, names=2, teacher=8, fill_page=True, side_title=0, top_title=True, font_size=9,
              save_name=26, top_width=50, side_width=75, percent=0.70)
test_thoughts(rows=8, columns=6, names=2, teacher=7, fill_page=True, side_title=0, top_title=True, font_size=9,
              save_name=27, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=7, columns=6, names=2, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=28, top_width=50, side_width=50, percent=0.88)
test_thoughts(rows=6, columns=6, names=2, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=29, top_width=50, side_width=50, percent=0.80)
test_thoughts(rows=8, columns=6, names=1, teacher=7, fill_page=True, side_title=0, top_title=True, font_size=9,
              save_name=30, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=7, columns=6, names=1, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=31, top_width=50, side_width=50, percent=0.88)
test_thoughts(rows=6, columns=6, names=1, teacher=7, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=32, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=8, columns=6, names=2, teacher=0, fill_page=True, side_title=0, top_title=True, font_size=9,
              save_name=33, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=7, columns=6, names=2, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=34, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=6, columns=6, names=2, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=35, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=8, columns=6, names=1, teacher=0, fill_page=True, side_title=0, top_title=True, font_size=9,
              save_name=36, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=7, columns=6, names=1, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=37, top_width=50, side_width=50, percent=0.88)
test_thoughts(rows=6, columns=6, names=1, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=38, top_width=50, side_width=50, percent=0.88)
test_thoughts(rows=5, columns=6, names=2, teacher=8, fill_page=True, side_title=0, top_title=True, font_size=9,
              save_name=39, top_width=30, side_width=70, percent=0.70)
test_thoughts(rows=9, columns=7, names=2, teacher=0, fill_page=True, side_title=0, top_title=True, font_size=9,
              save_name=40, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=8, columns=7, names=2, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=41, top_width=50, side_width=50, percent=0.90)
test_thoughts(rows=7, columns=7, names=2, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=9,
              save_name=42, top_width=50, side_width=50, percent=0.85)
test_thoughts(rows=9, columns=7, names=1, teacher=0, fill_page=True, side_title=0, top_title=True, font_size=8,
              save_name=43, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=8, columns=7, names=1, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=8,
              save_name=44, top_width=50, side_width=50, percent=0.90)
test_thoughts(rows=7, columns=7, names=1, teacher=0, fill_page=False, side_title=0, top_title=True, font_size=8,
              save_name=45, top_width=50, side_width=50, percent=0.90)
test_thoughts(rows=5, columns=7, names=2, teacher=8, fill_page=True, side_title=0, top_title=True, font_size=8,
              save_name=46, top_width=50, side_width=50, percent=0.70)
test_thoughts(rows=6, columns=8, names=2, teacher=8, fill_page=True, side_title=0, top_title=True, font_size=8,
              save_name=47, top_width=25, side_width=40, percent=0.70)