from app.common.utils import pagesize_map, pagesize_map_new
from app.models import db, Book, Sheet, Project, ProjectMeta
from app.thumbnails import upload, delete
from app.pdf_storage import upload as pdf_upload

import copy
import math
import os
import requests

from cStringIO import StringIO
from flask import current_app
from lxml import etree
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from wand.color import Color
from wand.image import Image as Img


Image.MAX_IMAGE_PIXELS = None

# Nasty Globals
file_path = os.path.abspath(__file__)
folder_path = file_path.rsplit(os.path.sep, 2)[0]
DESIRED_DPI = 72
# -------------
# Set up temp folder if it doesn't exist
folder_check = os.path.join(folder_path, "temp_pdfs")
if not os.path.exists(folder_check):
    os.makedirs(folder_check)
folder_check = os.path.join(folder_path, "split_pdfs")
if not os.path.exists(folder_check):
    os.makedirs(folder_check)
# -------------
FONT_FACES = [("Brown Pro", "brown_pro-light.ttf"),
    ("Checkpoint Regular", "checkpoint-webfont.ttf"),
    ("Cochise Regular", "cochise-webfont.ttf"),
    ("Cottons", "cottons_light.ttf"),
    ("CrayonHand", "CrayonHandRegular.ttf"),
    ("Cupido", "cupido-webfont.ttf"),
    ("Elevations", "ElevationsLCBB.ttf"),
    ("Emmy", "Emmy.ttf"),
    ("Emmy-Bold", "Emmy_Bold2.ttf"),
    ("Emmy-Bold-Italic", "EmmyBoldItalic.ttf"),
    ("Emmy-Italic", "EmmyItalic.ttf"),
    ("Eponymous Regular", "eponymous-regular.ttf"),
    ("Eponymous-Bold", "eponymous-bold.ttf"),
    ("Eponymous-Bold-Italic", "eponymous-bolditalic.ttf"),
    ("Eponymous-Italic", "eponymous-italic.ttf"),
    ("Felt Point Bold", "feltpointbold-webfont.ttf"),
    ("Felt That", "felt_that_ot_ps.ttf"),
    ("Grinched", "grinched_2.0.ttf"),
    ("Jonathan", "jonathan-webfont.ttf"),
    ("Kaleidoskop Regular", "kaleidoskop-webfont.ttf"),
    ("Kettering", "kettering_105_book.ttf"),
    ("Lifetime Regular", "lifetime-webfont.ttf"),
    ("Limerick", "limerick-regular-webfont.ttf"),
    ("Limerick-Xlight", "limerick-xlight-webfont.ttf"),
    ("Marbachxbol", "marbachxbol.ttf"),
    ("Marvin", "Marvin.ttf"),
    ("Momento", "momento-webfont.ttf"),
    ("Momento-Bold", "momentobold-webfont.ttf"),
    ("Momento-Bold-Italic", "momentobolditalic-webfont.ttf"),
    ("Momento-Italic", "momentoitalic-webfont.ttf"),
    ("Mr Robot", "mrrobot.ttf"),
    ("Newton", "nwt55.ttf"),
    ("Newton-Bold", "nwt75.ttf"),
    ("Newton-Bold-Italic", "nwt76.ttf"),
    ("Newton-Italic", "nwt56.ttf"),
    ("NexaRustSans", "nexarustsans-black3.ttf"),
    ("Olympia-Heavy Regular", "olympia-heavy-webfont.ttf"),
    ("Olympia-Medium", "olympia-medium-webfont.ttf"),
    ("Olympia-MediumCond Regular", "olympia-mediumcond-webfont.ttf"),
    ("Proximanova", "proximanova-regular.ttf"),
    ("Proximanova-Bold", "proximanova-bold.ttf"),
    ("Proximanova-Bold-Italic", "proximanova-boldit.ttf"),
    ("Proximanova-Italic", "proximanova-regularit.ttf"),
    ("Rough Brush Script", "roughbrushscript-rg.ttf"),
    ("Saycheez", "Saycheez-Regular.ttf"),
    ("Shabby", "shabby-webfont.ttf"),
    ("Sunflower Regular", "sunflower-webfont.ttf"),
    ("TabascoTwin Regular", "tabascotwin-webfont.ttf"),
    ("Times", "timestpc-webfont.ttf"),
    ("Times-Bold", "timetb__-webfont.ttf"),
    ("Times-Bold-Italic", "timetbi_-webfont.ttf"),
    ("Times-Italic", "timeti__-webfont.ttf"),
    ("TT Marks", "tt_marks_medium.ttf"),
    ("Zephyr", "zephyr-webfont.ttf")]

def register_fonts():
    for fontname, filename in FONT_FACES:
        pdfmetrics.registerFont(TTFont(fontname, "%s/fonts/%s" % (folder_path, filename)))


def get_rgb(raw):
    if "rgb" in raw:
        int_tuple = tuple(raw.lstrip("rgb(").rstrip(")").split(","))
        return tuple(int(x) / 255.0 for x in int_tuple)
    else:
        value = raw.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) / 255.0 for i in range(0, lv, lv // 3))


def rip_book(sheet_id=None, split_spread=True, user_id=None, project_name=None, project_id=None,
             token=None, thumbnail=False, image_type="MediumRes"):
    _headers_ = {"user-id": user_id, "project-id": project_id, "x-subject-token": token}

    if sheet_id is not None and type(sheet_id) in [str, unicode]:
        sheets = [db.session.query(Sheet).filter_by(id_=sheet_id).first()]
    elif sheet_id is not None and type(sheet_id) is list:
        sheets = [db.session.query(Sheet).filter_by(id_=x).first() for x in sheet_id]
    else:
        sheets = db.session.query(Sheet).filter_by(book_id=project_id).order_by(Sheet.sort_order)

    if not sheets:
        return

    book = db.session.query(Book).filter_by(id_=project_id).first()

    project = db.session.query(Project).filter_by(project_uuid=project_id).first()
    project_meta = db.session.query(ProjectMeta).filter_by(project_id=project.project_id,
                                                           project_meta_name="bind_type").first()
    if project_meta:
        bind_type = project_meta.project_meta_value
    else:
        bind_type = 3

    if book is None:
        return

    page_height = pagesize_map[str(book.trim_size)][1]
    page_width = pagesize_map[str(book.trim_size)][0]

    trim_boxes = []
    for sheet_index, sheet in enumerate(sheets):
        if sheet.type == "COVER":
            continue
        print sheet.id

        if sheet_id is not None:
            _canvas = canvas.Canvas(os.path.join(folder_path, "temp_pdfs", project_id + "_proof.pdf"),
                                    pagesize=(page_width, page_height))
        else:
            _canvas = canvas.Canvas(os.path.join(folder_path, "temp_pdfs", project_id + "_" + str(sheet_index - 1) +
                                                 ".pdf"),
                                    pagesize=(page_width, page_height))
        _canvas.setPageCompression(1)

        # decoded_svg = base64.b64decode(sheet["compressed"])
        # decompressed = zlib.decompress(decoded_svg)
        # sheet["decompressed"] = decompressed

        # svg = normalize_units(etree.fromstring(decompressed))
        # svg = scale_units_down(etree.fromstring(decompressed))
        # svg = etree.fromstring(decompressed)
        svg = etree.fromstring(sheet.svg)

        if sheet_id is not None and sheet.id != sheet_id:
            continue

        # with open(os.path.join(os.getcwd(), "ripper", 'svg', sheet["id"] + '.svg'), 'wb') as f:
        #     f.write(etree.tostring(svg))

        # Set the clippath/filter defs layer aside for later.
        defs = None
        for layer in list(svg):
            if "defs" in str(layer.tag):
                defs = layer

        for layer in list(svg):
            if thumbnail is False and layer.get("id") in ["guide_LEFT", "guide_RIGHT", "gg_layer"]:
                for obj in layer.getiterator():
                    if "rect" in obj.tag and obj.get("stroke") in ["#00FF00", "#00ff00"]:
                        x = float(obj.get("x"))
                        y = float(obj.get("y"))
                        height = float(obj.get("height"))
                        width = float(obj.get("width"))
                        trim_boxes.append(((x, y), (x + width, y + height)))
                continue
            for obj in layer.getiterator():
                height = obj.get("height")
                width = obj.get("width")
                x = obj.get("x")
                y = obj.get("y")
                fill = obj.get("fill")
                fill_opacity = obj.get("fill-opacity")
                stroke = obj.get("stroke")
                stroke_width = obj.get("stroke-width")
                stroke_opacity = obj.get("stroke-opacity")
                opacity = obj.get("opacity")

                _canvas.saveState()

                rotation = obj.get("transform")

                if "rect" in obj.tag:
                    text_group = False
                    # Ignore background rectangles
                    if obj.get("{http://www.myyear.com}background") in ["L", "R", "F"]:
                        _canvas.restoreState()
                        continue

                    if rotation is None:
                        obj_parent = obj.getparent()
                        if obj_parent.get("{http://www.myyear.com}text-group") == "true":
                            text_group = True
                            rotation = obj_parent.get("transform")

                    if opacity and opacity == "0":
                        _canvas.restoreState()
                        continue

                    flipped_y = page_height - float(y) - float(height)

                    if stroke_opacity in ["None", "none"]:
                        stroke_opacity = 0
                    if stroke_opacity is None:
                        if opacity is None:
                            stroke_opacity = 1
                        else:
                            stroke_opacity = opacity
                    if stroke_opacity and float(stroke_opacity) > 1:
                        stroke_opacity = 1
                    alpha = float(stroke_opacity)
                    if stroke and stroke != "none":
                        rgb = get_rgb(stroke)
                        _canvas.setStrokeColorRGB(r=rgb[0], g=rgb[1], b=rgb[2],
                                                  alpha=alpha)

                    if fill_opacity in ["None", "none"]:
                        fill_opacity = 0
                    if fill_opacity is None:
                        if opacity is None:
                            fill_opacity = 1
                        else:
                            fill_opacity = opacity
                    if float(fill_opacity) > 1:
                        fill_opacity = 1
                    alpha = float(fill_opacity)
                    if fill and fill not in ["none"]:
                        if fill == "transparent":
                            _canvas.setFillColorRGB(r=0, g=0, b=0, alpha=0)
                        else:
                            rgb = get_rgb(fill)
                            _canvas.setFillColorRGB(r=rgb[0], g=rgb[1], b=rgb[2], alpha=alpha)
                    if fill and fill == "#000000" and fill_opacity == "0":
                        _canvas.setFillAlpha(0)
                    if stroke_width and stroke_width not in ["none", "0"]:
                        stroke_width = float(stroke_width)
                        _canvas.setLineWidth(stroke_width)
                    else:
                        _canvas.setLineWidth(0)

                    draw_stroke = True if stroke not in ["none", None] and stroke_width not in ["none", "0"] else False

                    drop_shadow = obj.get("filter")
                    # Account for drop shadows behind color-filled text boxes.
                    if drop_shadow is None and obj.get("fill") not in ["none", None]:
                        if obj.getparent().get("id") not in ["layer_1", "flowing_layer"]:
                            drop_shadow = obj.getparent().get("filter")
                    if drop_shadow:
                        drop_shadow = drop_shadow.split("#")[1].replace(")", "")
                        fil = next((x for x in list(defs) if x.get("id") == drop_shadow), None)
                        fe_offset = next((x for x in list(fil) if "feOffset" in x.tag), None)
                        tx = int(fe_offset.get("dx"))
                        ty = int(fe_offset.get("dy"))
                        offset = (tx, ty, tx * 2, ty * 2)
                        fe_gaussian_blur = next((x for x in list(fil) if "feGaussianBlur" in x.tag), None)
                        if fe_gaussian_blur is not None:
                            totalWidth = int(math.ceil(float(width))) + int(stroke_width) + offset[0] * 3
                            totalHeight = int(math.ceil(float(height))) + int(stroke_width) + offset[1] * 3
                            back = Image.new("RGBA", (totalWidth, totalHeight))
                            black_rect = ImageDraw.Draw(back)
                            if obj.get("fill") in ["none", None] and float(stroke_width) > 0:
                                black_rect.rectangle([(offset[0] - int(stroke_width) / 2,
                                                       offset[1] - int(stroke_width) / 2),
                                                      (totalWidth - offset[0] * 2 + int(stroke_width) / 2,
                                                       totalHeight - offset[1] * 2 + int(stroke_width) / 2)],
                                                     fill="black")
                                black_rect.rectangle([(offset[0] + stroke_width / 2,
                                                       offset[1] + stroke_width / 2),
                                                      (totalWidth - offset[0] * 2 - stroke_width / 2,
                                                       totalHeight - offset[1] * 2 - stroke_width / 2)], fill=0)
                            else:
                                black_rect.rectangle([(offset[0], offset[1]),
                                                      (totalWidth - offset[0], totalHeight - offset[1])],
                                                     fill="black")
                            n = 0
                            while n < 5:
                                back = back.filter(ImageFilter.BLUR)
                                n += 1
                            # back.save(os.path.join('/', 'home', 'crappens', 'Desktop',
                            #                        'test_fuck_temp_%s.png' % obj.get("id")))
                            drop_shadow_img = ImageReader(back)

                    if rotation and "rotate" in rotation:
                        angle = rotation.split("(")[1].split(" ")[0]
                        c = rotation.split(")")[0].split(" ")[1].split(",")
                        flipped_center_y = page_height - float(c[1])
                        if text_group is True:
                            actual_center = (float(x) + float(width) / 2, flipped_y + float(height) / 2)
                            center = (float(c[0]), flipped_center_y)
                            x_start = -(float(width) / 2 + (float(c[0]) - actual_center[0]))
                            y_start = -(float(height) / 2 + (flipped_center_y - actual_center[1]))
                        else:
                            center = (float(x) + float(width) / 2, flipped_y + float(height) / 2)
                            x_start = -float(width) / 2
                            y_start = -float(height) / 2
                        _canvas.translate(center[0], center[1])
                        _canvas.rotate(-float(angle))

                        if drop_shadow:
                            _canvas.drawImage(image=drop_shadow_img,
                                              x=x_start - (math.ceil(float(width)) - float(width)),
                                              y=y_start - offset[3], width=float(width) + offset[2],
                                              height=float(height) + offset[3], mask="auto")

                        _canvas.rect(x=x_start, y=y_start, width=float(width),
                                     height=float(height), fill=True if fill and fill != "none" else False,
                                     stroke=draw_stroke)
                    else:
                        if drop_shadow:
                            _canvas.drawImage(image=drop_shadow_img,
                                              x=float(x) - (math.ceil(float(width)) - float(width)),
                                              y=flipped_y - offset[3], width=float(width) + offset[2],
                                              height=float(height) + offset[3], mask="auto")
                        _canvas.rect(x=float(x), y=flipped_y, width=float(width), height=float(height),
                                     fill=True if fill and fill != "none" else False, stroke=draw_stroke)

                if "image" in obj.tag:
                    if obj.getparent().get("display") == "none":
                        _canvas.restoreState()
                        continue

                    rgb = get_rgb("#000000")
                    _canvas.setFillColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)

                    # flipped_y = page_height - float(y) - float(height)

                    if rotation and "rotate" in rotation:
                        angle = rotation.split("(")[1].split(" ")[0]
                    else:
                        angle = None

                    # Create clipPath for image
                    top_parent = obj.getparent().getparent()
                    # Ignore mysterious mal-formatted images
                    if "rect" in top_parent.tag:
                        _canvas.restoreState()
                        continue

                    rect_sibling = next((x for x in list(top_parent) if "rect" in x.tag), None)
                    if rect_sibling is None:
                        rect_sibling = next((x for x in list(obj.getparent()) if "rect" in x.tag), None)

                    if obj.get("{http://www.myyear.com}imgType"):
                        rect_sibling = obj

                    path_center = None
                    if rotation and "rotate" in rotation:
                        path_flipped_y = page_height - float(rect_sibling.get("y")) - float(rect_sibling.get("height"))
                        path_center = (float(rect_sibling.get("x")) + float(rect_sibling.get("width")) / 2,
                                       path_flipped_y + float(rect_sibling.get("height")) / 2)
                        _canvas.translate(path_center[0], path_center[1])
                        _canvas.rotate(-float(angle))
                        p = _canvas.beginPath()
                        p.rect(x=-float(rect_sibling.get("width")) / 2, y=-float(rect_sibling.get("height")) / 2,
                               height=float(rect_sibling.get("height")), width=float(rect_sibling.get("width")))
                    else:
                        p = _canvas.beginPath()
                        p.rect(x=float(rect_sibling.get("x")),
                               y=page_height - float(rect_sibling.get("y")) - float(rect_sibling.get("height")),
                               height=float(rect_sibling.get("height")), width=float(rect_sibling.get("width")))

                    # if image_type in ["HighResProof", "LowRes"]:
                    crop_box = {"x": float(rect_sibling.get("x")),
                                "y": float(rect_sibling.get("y")),
                                "height": float(rect_sibling.get("height")),
                                "width": float(rect_sibling.get("width"))}
                    # if image_type != "HighRes":
                    flipped_y = page_height - crop_box["y"] - crop_box["height"]

                    _canvas.saveState()
                    _canvas.clipPath(p, stroke=False)

                    link = obj.get("{http://www.w3.org/1999/xlink}href")

                    # Ignore loading gif if it got saved in to the svg
                    # Ignore svg images that managed to get embedded in the svg
                    if any(x in link for x in ["loading.gif", ".svg"]):
                        _canvas.restoreState()
                        continue
                    # If the link in the svg is for a s3 bucket item...
                    low_res_version = None
                    if "https://s3.amazonaws.com" in link:
                        # Make sure that the version you're pulling matches the pdf requested.
                        if image_type not in ["HighRes", "MediumRes"] and "_thumb" not in link:
                            if "_lowres" in link:
                                link.replace("_lowres", "_thumb")
                            else:
                                t = os.path.splitext(link)
                                link = "_thumb".join(t)
                        elif image_type in ["HighRes", "MediumRes"] and ("_thumb" in link or "_lowres" in link):
                            link.replace("_thumb", "")
                            link.replace("_lowres", "")
                        resp = requests.get(link)
                        # If S3 blocks you or the image doesn't exist...ask image-repo for the blob.
                        if resp.status_code != 200:
                            src_id = obj.get("{http://www.myyear.com}srcId")
                            if src_id is None or not int(src_id):
                                src_id = link.split("?")[0].rsplit("/", 1)[1]
                            if image_type in ["HighRes", "MediumRes"]:
                                url = current_app.config["IMAGE_REPO"] + "/images/blob/" + str(src_id)
                            else:
                                url = current_app.config["IMAGE_REPO"] + "/images/blob/" + str(src_id) + "?thumb"
                            resp = requests.get(url, headers=_headers_, verify=False, stream=True)
                            # If image isn't found, because it's been deleted, skip it.
                            if resp.status_code != 200:
                                _canvas.restoreState()
                                continue
                        if image_type in ["HighRes", "MediumRes"] and obj.getparent().getparent().get("filter") not in ["none", None]:
                            src_id = obj.get("{http://www.myyear.com}srcId")
                            url = current_app.config["IMAGE_REPO"] + "/images/blob/" + str(src_id) + "?thumb"
                            resp2 = requests.get(url, headers=_headers_, verify=False, stream=True, timeout=10)
                            if resp2.status_code != 200:
                                url = current_app.config["IMAGE_REPO"] + "/images/blob/" + str(src_id) + "?thumb"
                                resp2 = requests.get(url, headers=_headers_, verify=False, stream=True, timeout=10)
                                # If image isn't found, because it's been deleted, skip it.
                                if resp2.status_code != 200:
                                    _canvas.restoreState()
                                    continue
                            low_res_version = Image.open(StringIO(resp2.content))
                            if low_res_version.mode != "RGBA":
                                low_res_version = low_res_version.convert("RGBA")
                    else:
                        src_id = obj.get("{http://www.myyear.com}srcId")
                        if src_id is None or type(src_id) is not int:
                            # For future reference...
                            # {http://www.w3.org/1999/xlink}href="/api_1_0/images/blob/3391?lowres"
                            src_id = link.split("?")[0].rsplit("/", 1)[1]
                        if image_type in ["HighRes", "MediumRes"]:
                            url = current_app.config["IMAGE_REPO"] + "/images/blob/" + str(src_id)
                        else:
                            url = current_app.config["IMAGE_REPO"] + "/images/blob/" + str(src_id) + "?thumb"
                        resp = requests.get(url, headers=_headers_, verify=False, stream=True)
                        # If image isn't found, because it's been deleted, skip it.
                        if resp.status_code != 200:
                            _canvas.restoreState()
                            continue

                        if image_type in ["HighRes", "MediumRes"] and obj.getparent().getparent().get("filter") not in ["none", None]:
                            src_id = obj.get("{http://www.myyear.com}srcId")
                            url = current_app.config["IMAGE_REPO"] + "/images/blob/" + str(src_id) + "?thumb"
                            resp2 = requests.get(url, headers=_headers_, verify=False, stream=True)
                            if resp2.status_code != 200:
                                url = current_app.config["IMAGE_REPO"] + "/images/blob/" + str(src_id) + "?thumb"
                                resp2 = requests.get(url, headers=_headers_, verify=False, stream=True)
                                # If image isn't found, because it's been deleted, skip it.
                                if resp2.status_code != 200:
                                    _canvas.restoreState()
                                    continue
                            low_res_version = Image.open(StringIO(resp2.content))
                            if low_res_version.mode != "RGBA":
                                low_res_version = low_res_version.convert("RGBA")

                    base_image = Image.open(StringIO(resp.content))
                    if base_image.mode != "RGBA":
                        base_image = base_image.convert("RGBA")

                    if image_type in ["LowRes"]:
                        # PIL requires that measurements be ints (as not not have .25/.5/.75/etc of a pixel).
                        # Therefore, when resizing/cropping the image down, use the rounded down value of the x/y and
                        # the rounded up (no matter the decimal value) of the height/width.  This will make the image
                        # slightly larger than needed, but keep the original dimensions/ratio from MyYear.  The
                        # clip-path defined above will trim off any remaining image that shouldn't be shown.
                        c_x = int(crop_box["x"])
                        c_y = int(crop_box["y"])
                        c_w = int(math.ceil(crop_box["width"]))
                        c_h = int(math.ceil(crop_box["height"]))

                        x = float(x)
                        y = float(y)
                        height = int(math.ceil(float(height)))
                        width = int(math.ceil(float(width)))
                        # Resize it down to the pdf size, so long as you're not going to make the image bigger.
                        resized = base_image.resize((width, height), Image.ANTIALIAS)

                        x = int(x)
                        y = int(y)
                        # Crop the image to the svg clippath rather than have hidden pixels in the pdf
                        cropped = resized.crop((c_x - x, c_y - y, c_x - x + c_w, c_y - y + c_h))

                        x = crop_box["x"]
                        y = crop_box["y"]
                        height = crop_box["height"]
                        width = crop_box["width"]

                        base_image = cropped

                        del cropped
                        del resized

                    elif image_type in ["HighRes", "MediumRes"]:
                        if image_type == "HighRes":
                            ratio = 300.0/72.0
                        else:
                            ratio = 150.0/72.0
                        # If the original image is larger than the box (scaled to 300dpi) that it's going in to...
                        if float(height) * ratio < base_image.height:
                            modified_height = int(math.ceil(float(height) * ratio))
                            modified_width = int(math.ceil(float(width) * ratio))

                            c_w = int(math.ceil(crop_box["width"] * ratio))
                            c_h = int(math.ceil(crop_box["height"] * ratio))
                            c_x = int((crop_box["x"] - float(x)) * ratio)
                            c_y = int((crop_box["y"] - float(y)) * ratio)

                            resized = base_image.resize((modified_width, modified_height), Image.ANTIALIAS)
                            cropped = resized.crop((c_x, c_y, c_x + c_w, c_y + c_h))

                            x = crop_box["x"]
                            y = crop_box["y"]
                            height = crop_box["height"]
                            width = crop_box["width"]

                            # flipped_y = page_height - y - height

                            base_image = cropped

                            del cropped
                            del resized
                        else:
                            ratio = base_image.height / float(height)

                            c_w = int(math.ceil(crop_box["width"] * ratio))
                            c_h = int(math.ceil(crop_box["height"] * ratio))
                            c_x = int((crop_box["x"] - float(x)) * ratio)
                            c_y = int((crop_box["y"] - float(y)) * ratio)

                            cropped = base_image.crop((c_x, c_y, c_x + c_w, c_y + c_h))

                            x = crop_box["x"]
                            y = crop_box["y"]
                            height = crop_box["height"]
                            width = crop_box["width"]

                            base_image = cropped

                            del cropped

                    drop_shadow = obj.getparent().getparent().get("filter")
                    if drop_shadow:
                        drop_shadow = drop_shadow.split("#")[1].replace(")", "")
                        fil = next((x for x in list(defs) if x.get("id") == drop_shadow), None)
                        fe_offset = next((x for x in list(fil) if "feOffset" in x.tag), None)
                        tx = int(fe_offset.get("dx"))
                        ty = int(fe_offset.get("dy"))
                        offset = (tx, ty, tx * 2, ty * 2)
                        fe_gaussian_blur = next((x for x in list(fil) if "feGaussianBlur" in x.tag), None)
                        if fe_gaussian_blur is not None:
                            # Create the backdrop image -- a box in the background color with a shadow on it.
                            base_image.convert("RGBA")
                            if image_type in ["HighRes", "MediumRes"]:
                                totalWidth = low_res_version.size[0] + offset[0] * 2
                                totalHeight = low_res_version.size[1] + offset[1] * 2
                                back = Image.new(low_res_version.mode, (totalWidth, totalHeight))
                                # Place the shadow, taking into account the offset from the image
                                blacked_out = low_res_version.copy()
                                gray = blacked_out.convert('L')
                                bw = gray.point(lambda x: 0)
                                bw.putalpha(low_res_version.split()[3])
                                back.paste(bw, (offset[1], offset[0]))
                            else:
                                totalWidth = base_image.size[0] + offset[0] * 2
                                totalHeight = base_image.size[1] + offset[1] * 2
                                back = Image.new(base_image.mode, (totalWidth, totalHeight))
                                # Place the shadow, taking into account the offset from the image
                                blacked_out = base_image.copy()
                                gray = blacked_out.convert('L')
                                bw = gray.point(lambda x: 0)
                                bw.putalpha(base_image.split()[3])
                                back.paste(bw, (offset[1], offset[0]))
                            # Apply the filter to blur the edges of the shadow.  Since a small kernel
                            # is used, the filter must be applied repeatedly to get a decent blur.
                            n = 0
                            while n < 5:
                                back = back.filter(ImageFilter.BLUR)
                                n += 1
                            # back.save(os.path.join('/', 'home', 'crappens', 'Desktop',
                            #                        'test_fuck_temp_%s.png' % obj.get("id")))

                            drop_shadow_img = ImageReader(back)

                            _canvas.restoreState()
                            _canvas.saveState()
                            if rotation and "rotate" in rotation:
                                center = (float(x) + float(width) / 2, flipped_y + float(height) / 2)
                                _canvas.translate(center[0] - path_center[0], center[1] - path_center[1])

                                _canvas.drawImage(image=drop_shadow_img, x=-float(width) / 2,
                                                  y=-float(height) / 2 - offset[3],
                                                  width=float(width) + offset[2], height=float(height) + offset[3],
                                                  mask="auto")

                            else:
                                _canvas.drawImage(image=drop_shadow_img, x=float(x), y=flipped_y - offset[3],
                                                  width=float(width) + offset[2],
                                                  height=float(height) + offset[3], mask="auto")
                            _canvas.restoreState()
                            _canvas.clipPath(p, stroke=False)

                    # Add filter effects to an image/clipart.
                    img_filter = obj.get("filter")
                    if img_filter:
                        img_filter = img_filter.split("#")[1].replace(")", "")
                        for fil in defs:
                            if str(fil.get("id")) == img_filter:
                                raw_filter = list(fil)[1].get("values").split(" ")
                                r = float(raw_filter[4])
                                g = float(raw_filter[9])
                                b = float(raw_filter[14])
                                if not all(x == 0.0 for x in [r, g, b]):
                                    fil_red = int(r * 255)
                                    fil_green = int(g * 255)
                                    fil_blue = int(b * 255)
                                    white = (255, 255, 255)
                                    if len(base_image.split()) == 4:
                                        a = base_image.split()[3]
                                    else:
                                        a = None
                                    gray = ImageOps.grayscale(base_image)
                                    result = ImageOps.colorize(gray, (fil_red, fil_green, fil_blue), white)
                                    if a:
                                        result.putalpha(a)
                                    base_image = result

                                    del gray
                                    del result

                    image = ImageReader(base_image)
                    # Rotate if need be then draw, otherwise just draw it
                    # _canvas.clipPath(p, stroke=False)
                    if rotation and "rotate" in rotation:
                        center = (float(x) + float(width) / 2, flipped_y + float(height) / 2)
                        _canvas.translate(center[0] - path_center[0], center[1] - path_center[1])

                        _canvas.drawImage(image=image, x=-float(width) / 2, y=-float(height) / 2,
                                          width=float(width), height=float(height), mask="auto")
                        _canvas.setFillColor("#00ff00", alpha=1)
                        # _canvas.circle(x_cen=0, y_cen=0, r=5, fill=True)
                    else:
                        _canvas.drawImage(image=image, x=float(x), y=flipped_y, width=float(width),
                                          height=float(height), mask="auto")
                    _canvas.restoreState()
                    del base_image

                if "ellipse" in obj.tag:
                    rx = float(obj.get("rx"))
                    ry = float(obj.get("ry"))
                    cx = float(obj.get("cx"))
                    cy = float(obj.get("cy"))

                    flipped_y_top = page_height - cy - ry
                    flipped_y_bottom = page_height - cy + ry

                    if stroke_opacity in ["None", "none"]:
                        stroke_opacity = 0
                    if stroke_opacity is None:
                        if opacity is None:
                            stroke_opacity = 1
                        else:
                            stroke_opacity = opacity
                    if stroke_opacity and float(stroke_opacity) > 1:
                        stroke_opacity = 1
                    alpha = float(stroke_opacity)
                    if stroke and stroke != "none":
                        rgb = get_rgb(stroke)
                        _canvas.setStrokeColorRGB(r=rgb[0], g=rgb[1], b=rgb[2],
                                                  alpha=alpha)

                    if fill_opacity in ["None", "none"]:
                        fill_opacity = 0
                    if fill_opacity is None:
                        if opacity is None:
                            fill_opacity = 1
                        else:
                            fill_opacity = opacity
                    if float(fill_opacity) > 1:
                        fill_opacity = 1
                    alpha = float(fill_opacity)
                    if fill and fill not in ["none"]:
                        if fill == "transparent":
                            _canvas.setFillColorRGB(r=0, g=0, b=0, alpha=0)
                        else:
                            rgb = get_rgb(fill)
                            _canvas.setFillColorRGB(r=rgb[0], g=rgb[1], b=rgb[2], alpha=alpha)
                    if fill and fill == "#000000" and fill_opacity == "0":
                        _canvas.setFillAlpha(0)
                    if stroke_width and stroke_width not in ["none", "0"]:
                        stroke_width = float(stroke_width)
                        _canvas.setLineWidth(stroke_width)
                    else:
                        _canvas.setLineWidth(0)

                    draw_stroke = True if stroke not in ["none", None] and stroke_width not in ["none", "0"] else False

                    # Cancels out those pesky PEP8 warnings of reference before assignment.
                    drop_shadow_img, totalWidth, totalHeight = None, None, None
                    drop_shadow = obj.get("filter")
                    if drop_shadow:
                        drop_shadow = drop_shadow.split("#")[1].replace(")", "")
                        fil = next((x for x in list(defs) if x.get("id") == drop_shadow), None)
                        fe_offset = next((x for x in list(fil) if "feOffset" in x.tag), None)
                        tx = int(fe_offset.get("dx"))
                        ty = int(fe_offset.get("dy"))
                        offset = (tx, ty, tx * 2, ty * 2)
                        fe_gaussian_blur = next((x for x in list(fil) if "feGaussianBlur" in x.tag), None)
                        if fe_gaussian_blur is not None:
                            totalWidth = int(math.ceil(rx)) * 2 + offset[0] * 2
                            totalHeight = int(math.ceil(ry)) * 2 + offset[1] * 2
                            back = Image.new("RGBA", (totalWidth, totalHeight))
                            black_rect = ImageDraw.Draw(back)
                            if obj.get("fill") in ["none", None] and float(stroke_width) > 0:
                                black_rect.ellipse([(offset[0] / 2, offset[1] / 2),
                                                    (totalWidth - offset[0], totalHeight - offset[1])],
                                                   fill="black")
                                black_rect.ellipse([(offset[0] / 2 + int(stroke_width),
                                                     offset[1] / 2 + int(stroke_width)),
                                                    (totalWidth - offset[0] - int(stroke_width),
                                                     totalHeight - offset[1] - int(stroke_width))], fill=0)
                            else:
                                black_rect.ellipse([(offset[0], offset[1]),
                                                    (totalWidth - offset[0], totalHeight - offset[1])],
                                                   fill="black")
                            n = 0
                            while n < 5:
                                back = back.filter(ImageFilter.BLUR)
                                n += 1
                            # back.save(os.path.join('/', 'home', 'crappens', 'Desktop',
                            #                        'test_fuck_temp_%s.png' % obj.get("id")))
                            drop_shadow_img = ImageReader(back)

                    if rotation and "rotate" in rotation:
                        angle = float(rotation.split("(")[1].split(" ")[0])
                        flipped_cy = page_height - cy
                        _canvas.translate(cx, flipped_cy)
                        _canvas.rotate(-angle)

                        if drop_shadow:
                            # TODO match correct for float to int conversion
                            _canvas.drawImage(image=drop_shadow_img, x=-rx, y=-ry - offset[3], width=totalWidth,
                                              height=totalHeight, mask="auto")

                        _canvas.ellipse(-rx, ry, rx, -ry,
                                        fill=True if fill and fill != "none" else False,
                                        stroke=draw_stroke)
                    else:
                        if drop_shadow:
                            # TODO match correct for float to int conversion
                            _canvas.drawImage(image=drop_shadow_img, x=cx - rx, y=flipped_y_top - offset[3],
                                              width=totalWidth, height=totalHeight, mask="auto")

                        _canvas.ellipse(cx - rx, flipped_y_top, cx + rx, flipped_y_bottom,
                                        fill=True if fill and fill != "none" else False,
                                        stroke=draw_stroke)

                if "line" in obj.tag:
                    if obj.get("{http://svg-edit.googlecode.com}guide") == "true":
                        _canvas.restoreState()
                        continue

                    flipped_y1 = page_height - float(obj.get("y1"))
                    flipped_y2 = page_height - float(obj.get("y2"))
                    x1 = float(obj.get("x1"))
                    x2 = float(obj.get("x2"))
                    width = abs(x2 - x1)
                    height = abs(flipped_y2 - flipped_y1)
                    if stroke_opacity in ["None", "none"]:
                        stroke_opacity = 0
                    if stroke_opacity is None:
                        if opacity is None:
                            stroke_opacity = 1
                        else:
                            stroke_opacity = opacity
                    if stroke_opacity and float(stroke_opacity) > 1:
                        stroke_opacity = 1
                    alpha = float(stroke_opacity)
                    if stroke and stroke != "none":
                        rgb = get_rgb(stroke)
                        _canvas.setStrokeColorRGB(rgb[0], rgb[1], rgb[2], alpha=alpha)
                    if stroke_width and stroke_width != "none":
                        _canvas.setLineWidth(float(stroke_width))
                    else:
                        _canvas.setLineWidth(0)

                    drop_shadow_img, totalWidth, totalHeight = None, None, None
                    drop_shadow = obj.get("filter")
                    if drop_shadow:
                        drop_shadow = drop_shadow.split("#")[1].replace(")", "")
                        fil = next((x for x in list(defs) if x.get("id") == drop_shadow), None)
                        fe_offset = next((x for x in list(fil) if "feOffset" in x.tag), None)
                        tx = int(fe_offset.get("dx"))
                        ty = int(fe_offset.get("dy"))
                        offset = (tx, ty, tx * 2, ty * 2)
                        fe_gaussian_blur = next((x for x in list(fil) if "feGaussianBlur" in x.tag), None)
                        if fe_gaussian_blur is not None:
                            totalWidth = int(math.ceil(width)) + offset[0] * 4
                            totalHeight = int(math.ceil(height)) + offset[1] * 4
                            back = Image.new("RGBA", (totalWidth, totalHeight))
                            black_rect = ImageDraw.Draw(back)
                            if flipped_y2 > flipped_y1:
                                black_rect.line([(offset[0] * 2, totalHeight - offset[1] * 2),
                                                 (totalWidth - offset[0] * 2, offset[1] * 2)],
                                                width=int(obj.get("stroke-width")), fill="black")
                            if flipped_y1 >= flipped_y2:
                                black_rect.line([(offset[0] * 2, offset[1] * 2),
                                                 (totalWidth - offset[0] * 2, totalHeight - offset[1] * 2)],
                                                width=int(obj.get("stroke-width")), fill="black")
                            n = 0
                            while n < 5:
                                back = back.filter(ImageFilter.BLUR)
                                n += 1
                            # back.save(os.path.join('/', 'home', 'crappens', 'Desktop',
                            #                        'test_fuck_temp_%s.png' % obj.get("id")))
                            drop_shadow_img = ImageReader(back)

                    if rotation and "rotate" in rotation:
                        angle = float(rotation.split("(")[1].split(" ")[0])
                        center = (x1 + (x2-x1) / 2, flipped_y1 + (flipped_y2 - flipped_y1) / 2)
                        _canvas.translate(center[0], center[1])
                        _canvas.rotate(-angle)

                        if drop_shadow:
                            # TODO match correct for float to int conversion
                            _canvas.drawImage(image=drop_shadow_img, x=-totalWidth / 2 + offset[0],
                                              y=-totalHeight / 2 - offset[1], width=totalWidth,
                                              height=totalHeight, mask="auto")

                        _canvas.line(x1 - center[0], flipped_y1 - center[1], x2 - center[0], center[1] - flipped_y1)
                    else:
                        if drop_shadow:
                            # TODO match correct for float to int conversion
                            _canvas.drawImage(image=drop_shadow_img, x=x1 - offset[0],
                                              y=flipped_y2 - offset[3] - offset[1], width=totalWidth,
                                              height=totalHeight, mask="auto")

                        _canvas.line(float(obj.get("x1")), flipped_y1, float(obj.get("x2")), flipped_y2)

                # TODO: Right aligned text is losing font color
                if "text" in obj.tag:
                    rgb = get_rgb("#000000")
                    _canvas.setFillColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)

                    _canvas.setLineWidth(1)

                    obj_parent = obj.getparent()
                    rect_sibling = None
                    image_sibling = False

                    for each in list(obj_parent):
                        if "rect" in each.tag:
                            rect_sibling = each
                        if "image" in each.tag:
                            image_sibling = True

                    if image_sibling:
                        _canvas.restoreState()
                        continue

                    if rect_sibling is not None:
                        obj_width = float(rect_sibling.get("width"))
                        obj_x = float(rect_sibling.get("x"))
                        obj_height = float(rect_sibling.get("height"))
                    else:
                        obj_x = float(x)
                        obj_width = 0 if width is None else float(width)
                        obj_height = 0 if height is None else float(height)

                    flipped_y = page_height - float(y)

                    offset_y = 0
                    offset_x = 0

                    rotation = obj_parent.get("transform")
                    if rotation and "rotate" in rotation:
                        c = rotation.split(")")[0].split(" ")[1].split(",")
                        flipped_center_y = page_height - float(c[1])
                        angle = float(rotation.split("(")[1].split(" ")[0])
                        center = (float(c[0]), flipped_center_y)
                        actual_center = (obj_x + obj_width / 2, flipped_y + obj_height / 2)

                        x_start = -(float(obj_width) / 2 + (float(c[0]) - actual_center[0]))
                        y_start = -(float(obj_height) / 2 + (flipped_center_y - actual_center[1]))

                        _canvas.translate(center[0], center[1])
                        _canvas.rotate(-angle)
                    else:
                        x_start = 0
                        y_start = 0
                        center = (0, 0)
                        actual_center = (0, 0)

                    drop_shadow = obj.getparent().get("filter")
                    if drop_shadow:
                        if rect_sibling.get("fill") not in ["none", None]:
                            drop_shadow = None
                    back = None
                    if drop_shadow:
                        drop_shadow = drop_shadow.split("#")[1].replace(")", "")
                        fil = next((x for x in list(defs) if x.get("id") == drop_shadow), None)
                        fe_offset = next((x for x in list(fil) if "feOffset" in x.tag), None)
                        tx = int(fe_offset.get("dx"))
                        ty = int(fe_offset.get("dy"))
                        offset = (tx, ty, tx * 2, ty * 2)
                        fe_gaussian_blur = next((x for x in list(fil) if "feGaussianBlur" in x.tag), None)
                        if fe_gaussian_blur is not None:
                            totalWidth = int(math.ceil(float(obj_width))) + offset[0] * 2
                            totalHeight = int(math.ceil(float(obj_height))) + offset[1] * 2
                            back = Image.new("RGBA", (totalWidth, totalHeight))

                    text_anchor = obj.get("text-anchor")
                    if text_anchor == "middle":
                        line_string = []
                        all_strings = []
                        for tspan in list(obj):
                            if tspan.text is not None:
                                if tspan.get("opacity") and tspan.get("opacity") == "0":
                                    continue
                                if tspan.get("dy"):
                                    offset_y += float(tspan.get("dy"))
                                    all_strings.append(line_string)
                                    line_string = []
                                line_string.append({"text": tspan.text, "font": tspan.get("font-family"),
                                                    "size": float(tspan.get("font-size")), "color": tspan.get("fill"),
                                                    "dy": offset_y, "stroke": tspan.get("stroke"),
                                                    "stroke-width": tspan.get("stroke-width")})
                                line_string[-1]["width"] = _canvas.stringWidth(line_string[-1]["text"],
                                                                               line_string[-1]["font"],
                                                                               line_string[-1]["size"])
                        all_strings.append(line_string)

                        for line in all_strings:
                            max_font_size = 0
                            for each in line:
                                if each["size"] > max_font_size:
                                    max_font_size = each["size"]
                            line_length = sum([x["width"] for x in line])
                            obj_center = obj_x + obj_width / 2
                            max_line_left = obj_center - line_length / 2
                            if rotation:
                                current_x = -line_length / 2 - (center[0] - actual_center[0])
                            else:
                                current_x = max_line_left
                            for part in line:
                                _canvas.setFont(part.get("font"), part.get("size"))
                                font_color = part.get("color")
                                rgb = get_rgb(font_color)
                                _canvas.setFillColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)

                                stroke_color = part.get("stroke")
                                stroke_width = part.get("stroke-width")
                                if stroke_color:
                                    if "rgb" in stroke_color:
                                        rgb = get_rgb(stroke_color)
                                        # There is no such thing as stroke opacity for text.
                                        _canvas.setStrokeColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)

                                if stroke_width:
                                    _canvas.setLineWidth(float(stroke_width))
                                else:
                                    _canvas.setLineWidth(0)

                                if stroke_color and stroke_width is not None and float(stroke_width) > 0:
                                    draw_mode = 2
                                else:
                                    draw_mode = None

                                if drop_shadow:
                                    shadow = copy.copy(back)
                                    shadow_text = ImageDraw.Draw(shadow)
                                    f_info = next((x for x in FONT_FACES if x[0] == part.get("font")), None)
                                    fnt = ImageFont.truetype("%s/fonts/%s" % (folder_path, f_info[1]),
                                                             int(part.get("size")))
                                    shadow_text.text((offset[0], offset[1]), part["text"], font=fnt, fill="black")
                                    for x in range(5):
                                        shadow = shadow.filter(ImageFilter.BLUR)
                                    # shadow.save(os.path.join('/', 'home', 'crappens', 'Desktop',
                                    #                          'test_fuck_temp_%s_%s.png' % (obj.get("id"),
                                    #                                                        part["text"])))
                                    drop_shadow_img = ImageReader(shadow)

                                if rotation:
                                    if drop_shadow:
                                        _canvas.drawImage(drop_shadow_img, x=current_x, width=totalWidth,
                                                          y=y_start + offset[3] * 2 - max_font_size * 1.1715,
                                                          height=totalHeight, mask='auto')

                                    _canvas.drawCentredString(x=current_x + float(part["width"]) / 2,
                                                              y=y_start - part["dy"], text=part["text"],
                                                              mode=draw_mode)
                                    current_x += float(part["width"])
                                else:
                                    if drop_shadow:
                                        _canvas.drawImage(drop_shadow_img, x=current_x, width=totalWidth,  mask='auto',
                                                          y=flipped_y + offset[3] * 2 - max_font_size * 1.1715 -
                                                            (max_font_size - part["size"]), height=totalHeight)

                                    _canvas.drawCentredString(x=current_x + float(part["width"]) / 2,
                                                              y=flipped_y - part["dy"], text=part["text"],
                                                              mode=draw_mode)
                                    current_x += float(part["width"])

                    if text_anchor == "end":
                        line_string = []
                        all_strings = []
                        for i, tspan in enumerate(list(obj)):
                            if tspan.get("opacity") and tspan.get("opacity") == "0":
                                continue
                            if i == 0:
                                offset_y += float(tspan.get("dy"))
                            if tspan.text is not None:
                                if len(line_string) > 0 and tspan.get("dy") is not None:
                                    offset_y += float(tspan.get("dy"))
                                    all_strings.append(line_string)
                                    line_string = []
                                line_string.append({"text": tspan.text, "font": tspan.get("font-family"),
                                                    "size": float(tspan.get("font-size")), "color": tspan.get("fill"),
                                                    "dy": offset_y, "stroke": tspan.get("stroke"),
                                                    "stroke-width": tspan.get("stroke-width")})
                                line_string[-1]["width"] = _canvas.stringWidth(line_string[-1]["text"],
                                                                               line_string[-1]["font"],
                                                                               line_string[-1]["size"])
                        all_strings.append(line_string)

                        for line in all_strings:
                            max_font_size = 0
                            for each in line:
                                if each["size"] > max_font_size:
                                    max_font_size = each["size"]
                            for index, part in enumerate(line):
                                if index != len(line) - 1:
                                    x_offset = sum([j["width"] for j in line[index+1:]])
                                else:
                                    x_offset = 0

                                _canvas.setFont(part.get("font"), part.get("size"))
                                font_color = part.get("color")
                                rgb = get_rgb(font_color)
                                _canvas.setFillColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)

                                stroke_color = part.get("stroke")
                                stroke_width = part.get("stroke-width")
                                if stroke_color:
                                    rgb = get_rgb(stroke_color)
                                    if "rgb" in stroke_color:
                                        # There is no such thing as stroke opacity for text.
                                        _canvas.setStrokeColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)
                                else:
                                    _canvas.setStrokeColorRGB(0, 0, 0, alpha=0)

                                if stroke_width:
                                    _canvas.setLineWidth(stroke_width)
                                else:
                                    _canvas.setLineWidth(0)

                                if stroke_color and stroke_width is not None and float(stroke_width) > 0:
                                    draw_mode = 2
                                else:
                                    draw_mode = None

                                # Build drop shadows if needed.
                                if drop_shadow:
                                    shadow = copy.copy(back)
                                    shadow_text = ImageDraw.Draw(shadow)
                                    f_info = next((x for x in FONT_FACES if x[0] == part.get("font")), None)
                                    fnt = ImageFont.truetype("%s/fonts/%s" % (folder_path, f_info[1]),
                                                             int(part.get("size")))
                                    shadow_text.text((offset[0], offset[1]), part["text"], font=fnt, fill="black")
                                    for x in range(5):
                                        shadow = shadow.filter(ImageFilter.BLUR)
                                    # shadow.save(os.path.join('/', 'home', 'crappens', 'Desktop',
                                    #                          'test_fuck_temp_%s_%s.png' % (obj.get("id"), part["text"])))
                                    drop_shadow_img = ImageReader(shadow)

                                if rotation:
                                    if drop_shadow:
                                        _canvas.drawImage(drop_shadow_img, x=x_start + x_offset + offset[2] * 2.5,
                                                          y=y_start + offset[3] * 2 - max_font_size * 1.1715 -
                                                            (max_font_size - part["size"]),
                                                          width=totalWidth, height=totalHeight, mask='auto')

                                    _canvas.drawRightString(x=x_start + obj_width - x_offset,
                                                            y=y_start - part["dy"], text=part["text"],
                                                            mode=draw_mode)
                                else:
                                    if drop_shadow:
                                        _canvas.drawImage(drop_shadow_img, x=obj_x + x_offset + offset[2] * 3,
                                                          y=flipped_y + offset[3] * 2 - max_font_size * 1.1715 -
                                                            (max_font_size - part["size"]),
                                                          width=totalWidth, height=totalHeight, mask='auto')

                                    _canvas.drawRightString(x=obj_x + obj_width - x_offset, y=flipped_y - part["dy"],
                                                            text=part["text"], mode=draw_mode)

                    if text_anchor == "start" or text_anchor is None:
                        for tspan in list(obj):
                            if tspan.text is not None:
                                if tspan.get("opacity") and tspan.get("opacity") == "0":
                                    continue
                                if tspan.get("dy") is not None:
                                    offset_y += float(tspan.get("dy"))
                                    offset_x = 0
                                if tspan.get("x") is not None:
                                    offset_x += float(tspan.get("x")) - obj_x

                                _canvas.setFont(tspan.get("font-family"), float(tspan.get("font-size")))
                                font_color = tspan.get("fill")
                                rgb = get_rgb(font_color)
                                _canvas.setFillColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)

                                stroke_color = tspan.get("stroke")
                                stroke_width = tspan.get("stroke-width")
                                if stroke_color:
                                    if "rgb" in stroke_color:
                                        rgb = get_rgb(stroke_color)
                                        _canvas.setStrokeColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)
                                if stroke_width:
                                    _canvas.setLineWidth(float(stroke_width))
                                else:
                                    _canvas.setLineWidth(0)

                                if stroke_color and stroke_width is not None and float(stroke_width) > 0:
                                    draw_mode = 2
                                else:
                                    draw_mode = None

                                # Build drop shadows if needed.
                                if drop_shadow:
                                    shadow = copy.copy(back)
                                    shadow_text = ImageDraw.Draw(shadow)
                                    f_info = next((x for x in FONT_FACES if x[0] == tspan.get("font-family")), None)
                                    fnt = ImageFont.truetype("%s/fonts/%s" % (folder_path, f_info[1]),
                                                             int(tspan.get("font-size")))
                                    shadow_text.text((offset[0], offset[1]), tspan.text, font=fnt, fill="black")
                                    for x in range(5):
                                        shadow = shadow.filter(ImageFilter.BLUR)
                                    # shadow.save(os.path.join('/', 'home', 'crappens', 'Desktop',
                                    #                          'test_fuck_temp_%s_%s.png' % (obj.get("id"), tspan.text)))
                                    drop_shadow_img = ImageReader(shadow)

                                if rotation:
                                    if drop_shadow:
                                        _canvas.drawImage(drop_shadow_img, x=x_start + offset_x, y=y_start - offset_y - offset[3] * 4,
                                                          width=totalWidth, height=totalHeight, mask='auto')

                                    _canvas.drawString(x=x_start + offset_x, y=y_start - offset_y,
                                                       text=tspan.text, mode=draw_mode)

                                    offset_x += stringWidth(tspan.text, tspan.get("font-family"),
                                                            float(tspan.get("font-size")))
                                else:
                                    if drop_shadow:
                                        _canvas.drawImage(drop_shadow_img, x=obj_x + offset_x, y=flipped_y - offset_y - offset[3] * 4,
                                                          width=totalWidth, height=totalHeight, mask='auto')

                                    _canvas.drawString(x=obj_x + offset_x, y=flipped_y - offset_y, text=tspan.text,
                                                       mode=draw_mode)
                                    offset_x += stringWidth(tspan.text, tspan.get("font-family"),
                                                            float(tspan.get("font-size")))

                _canvas.restoreState()

        # White out the cutbacks
        # Quarter inch cutback on first and last sheets
        if bind_type in [3, "Smythe"]:
            if sheet.type == "LAST_SHEET":
                rgb = get_rgb("#ffffff")
                _canvas.setFillColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)
                # trim_box = trim_boxes[-1]
                _canvas.rect(x=page_width / 2 - 18, y=0, height=page_height, width=36, stroke=False, fill=True)
            if sheet.type == "FIRST_SHEET":
                rgb = get_rgb("#ffffff")
                _canvas.setFillColorRGB(rgb[0], rgb[1], rgb[2], alpha=1)
                # trim_box = trim_boxes[-1]
                _canvas.rect(x=page_width / 2 - 18, y=0, height=page_height, width=36, stroke=False, fill=True)

        _canvas.save()

    print "done_ripping"
    # return
    if split_spread is False:
        if thumbnail is True:
            if not sheet_id:
                for x, sheet in enumerate(sheets, start=1):
                    sheet.thumbnail_url = create_thumbnail(pdf_location(project_id, "_" + str(x) + ".pdf"), [sheet])
                db.session.commit()
            else:
                tn = create_thumbnail(pdf_location(project_id, "_proof.pdf"), [x for x in sheets])
                return tn
        else:
            url_in_s3 = pdf_upload(pdf_location(project_id,
                                                "_proof.pdf"), project_id + "/" + project_name + "_proof.pdf")
            os.remove(pdf_location(project_id, "_proof.pdf"))
            if image_type == "MediumRes":
                print "updating proofed status"
                print sheets[0].id
                sheets[0].proofed = 1
                sheets[0].version += 1
                db.session.commit()
            return url_in_s3
    else:
        return add_trims(trim_boxes, project_name, project_id, book.page_count / 2 + 1)


def pdf_location(project_id, i):
    return os.path.join(folder_path, "temp_pdfs", project_id + i)


# Turned this in to a separate function since it's using a different library
def add_trims(trim_boxes, project_name, project_id, spread_count):
    # This is not a true cut, it's a copy and focus
    # input_file = PdfFileReader(os.path.join(folder_path, "temp_pdfs", project_id + ".pdf"))
    # pages = [input_file.getPage(i) for i in range(0, input_file.getNumPages())]
    return_paths = []
    # for page_count, r in enumerate(pages):
    print "splitting spreads in to single pages for project", project_id
    for n in xrange(0, spread_count):
        pdf_path = os.path.join(folder_path, "temp_pdfs", project_id + "_" + str(n) + ".pdf")
        r = PdfFileReader(pdf_path).getPage(0)

        width, height = r.mediaBox.upperRight
        width = int(width)
        height = int(height)

        counter = n * 2

        output1 = PdfFileWriter()
        output2 = PdfFileWriter()

        l = copy.deepcopy(r)
        # Left Page
        # Media/Art (blue) line
        l.mediaBox.upperLeft = (0, 0)
        l.mediaBox.lowerRight = (width / 2 + 18, height)
        # Trim (green) line
        l.trimBox.upperLeft = (18, 18)
        l.trimBox.lowerRight = (width / 2, height - 18)
        # Bleed (red) line
        l.bleedBox.upperLeft = l.mediaBox.upperLeft
        l.bleedBox.lowerRight = l.mediaBox.lowerRight

        # Right Page
        # Media/Art (blue) line
        r.mediaBox.upperLeft = (width / 2 - 18, 0)
        r.mediaBox.lowerRight = (width, height)
        # Trim (green) line
        r.trimBox.upperLeft = (width / 2, 18)
        r.trimBox.lowerRight = (width - 18, height - 18)
        # Bleed (red) line
        r.bleedBox.upperLeft = r.mediaBox.upperLeft
        r.bleedBox.lowerRight = r.mediaBox.lowerRight

        output1.addPage(l)
        output2.addPage(r)

        for index, output in enumerate([output1, output2]):
            if spread_count > 1:
                # Skip front inside cover
                if n == 0 and index == 0:
                    continue
                # Skip back inside cover
                elif n == spread_count - 1 and index == 1:
                    continue

            if counter + index < 10:
                p = os.path.join(folder_path, "split_pdfs", "%s_00%s_00%s.pdf" % (project_name, str(counter + index),
                                                                                  str(counter + index)))
                end_file = file(p, 'w+b')
            elif counter + index < 100:
                p = os.path.join(folder_path, "split_pdfs", "%s_0%s_0%s.pdf" % (project_name, str(counter + index),
                                                                                str(counter + index)))
                end_file = file(p, 'w+b')
            else:
                p = os.path.join(folder_path, "split_pdfs", "%s_%s_%s.pdf" % (project_name, str(counter + index),
                                                                              str(counter + index)))
                end_file = file(p, 'w+b')
            return_paths.append(p)

            output.write(end_file)

        # Delete the full spread pdf, it's no longer necessary.
        os.remove(os.path.join(folder_path, "temp_pdfs", project_id + "_" + str(n) + ".pdf"))

    print "finished splitting spreads in to single pages for project", project_id
    return return_paths


def create_thumbnail(path, sheets):
    # Uncomment for debugging, along with the "with" below, this will save full sized PNGs locally.
    # file_path = os.path.abspath(__file__)
    # folder_path = file_path.rsplit("/", 1)[0]
    print "attempting to make thumbnails"
    # shift = 0
    # if sheets[0].type == "COVER":
    #     shift = 1
    return_thumbnails = []
    with Img(filename=path) as img:
        for n, i in enumerate(img.sequence):
            with Img(i) as sub_image:
                # n += shift
                sub_image.background_color = Color("white")

                t_path = current_app.config["THUMBNAIL_PATH"]
                new_path = t_path + sheets[n].book_id + "/" + sheets[n].id + "_" + str(sheets[n].version) + ".png"

            # with open(os.path.join(folder_path, "thumbnails", sheets[n].id + "_" + str(sheets[n].version) + ".png"),
            #           "wb") as f:
            #     f.write(sub_image.make_blob(format="png"))

                sub_image.resize(img.width / 12, img.height / 12)

                print "uploading ", n
                upload(project_id=sheets[n].book_id, sheet_id=sheets[n].id,
                       img_string=sub_image.make_blob(format="png"), i_type="png", version=sheets[n].version)
                if new_path != sheets[n].thumbnail_url and sheets[n].thumbnail_url is not None:
                    # Make sure we don't delete the global thumbnails for new books
                    if "sheet_thumb" not in sheets[n].thumbnail_url:
                        delete(url=sheets[n].thumbnail_url)
                print n, "uploaded"
                s = db.session.query(Sheet).filter_by(id_=sheets[n].id).first()
                s.thumbnail_url = new_path
                db.session.commit()

                return_thumbnails.append(new_path)
    print "done making thumbnails"
    return return_thumbnails

register_fonts()
