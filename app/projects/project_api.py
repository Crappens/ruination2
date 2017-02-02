from flask import current_app
from lxml import etree
import requests

from app.common.exceptions import InvalidParameterException
from app.models import db, Book, Sheet, Project, ProjectMeta
from app.common.utils import set_model_uuid_and_dates, log_request_error, pagesize_map, pixelconversion_map, \
    scale_spread
from app.projects.svg_api import SheetSVG
from app.ripper.ripper import rip_book

MYYEAR_SCHEMA_NSMAP = {
    # XML Namespace Map for lxml etree namespace mapping.
    'se': "http://svg-edit.googlecode.com",
    'svg': "http://www.w3.org/2000/svg",
    'lyb': "http://www.myyear.com"
}


def decode_trim_size(trim_size):
    try:
        return pagesize_map[trim_size]
    except KeyError:
        log_request_error("Trim size for project is not defined correctly")
        raise InvalidParameterException("Trim size for project is not defined correctly")


def find_trim_measurements(width):
    try:
        return pixelconversion_map[int(width)]
    except KeyError:
        log_request_error("Width for project is not defined correctly")
        raise InvalidParameterException("Width for project is not defined correctly")


def get_svg(page_size, sheet_type, cutback):
    """
    Return the full SVG for this spread.
    :param page_size: PageSize
    :param sheet_type: string
    :return:
    """
    svg = SheetSVG(width=page_size.width, height=page_size.height, cutback=cutback)
    if sheet_type == "COVER":
        return svg.fullSVG
    # TODO: consider adding in the actual page numbers from the start?
    elif sheet_type == "FIRST_SHEET":
        return svg.rightPageSVG.replace("LEFT_FOLIO", "")
    elif sheet_type == "LAST_SHEET":
        return svg.leftPageSVG.replace("RIGHT_FOLIO", "")
    else:
        return svg.fullSVG


def create_default_sheets(book, cutback):
    prev_sheet_id = None

    sheet_count = (book.page_count >> 1) + 2

    for x in xrange(sheet_count):
        page = x + 1
        if x == 0:
            sheet_type = "COVER"
            thumb_url = current_app.config["NORMAL_SHEET_THUMB"]
        elif x == 1:
            sheet_type = "FIRST_SHEET"
            thumb_url = current_app.config["FIRST_SHEET_THUMB"]
        elif x == sheet_count - 1:
            sheet_type = "LAST_SHEET"
            thumb_url = current_app.config["LAST_SHEET_THUMB"]
        else:
            sheet_type = "SHEET"
            thumb_url = current_app.config["NORMAL_SHEET_THUMB"]

        sheet = Sheet(
                book_id=book.id,
                user_id=book.user_id,
                parent_sheet=prev_sheet_id,
                page=page,
                sort_order=x,
                svg=get_svg(decode_trim_size(book.trim_size), sheet_type, cutback),
                width=book.width,
                height=book.height,
                locked=0,
                completed=0,
                active=1,
                hidden=0,
                version=0,
                type=sheet_type,
                thumbnail_url=thumb_url)

        set_model_uuid_and_dates(sheet)
        db.session.add(sheet)
        prev_sheet_id = sheet.id


def on_first_login(**kwargs):
    """Create or import a book on the first user login for said book.

    :param project_number: The Bann Book Number.
    :param user_id: The id of the user logging into the book.
    :param kwargs:
    :return:
    """
    book = db.session.query(Book).filter_by(number=kwargs.get("project_number")).first()

    resp = requests.get("%s/projectData/%s" % (current_app.config["ENFOLD_URL"], kwargs.get("project_number")),
                        headers={"X-Auth-Token": current_app.config["ENFOLD_ADMIN_TOKEN"]})

    project = db.session.query(Project).filter_by(project_number=kwargs.get("project_number")).first()
    project_meta = db.session.query(ProjectMeta).filter_by(project_id=project.project_id,
                                                           project_meta_name="bind_type").first()

    if project_meta:
        bind_type = project_meta.project_meta_value
    else:
        bind_type = 3

    cutback = bind_type in [3, "Smythe"]

    data = resp.json()['project']

    # data["trim_size"] = "7"
    # print data["trim_size"], type(data["trim_size"])
    # data["pages"] += 20
    # cutback = False

    if isinstance(book, Book):
        current_trim_size = int(book.trim_size)
        new_trim_size = int(data["trim_size"])
        if current_trim_size != new_trim_size:
            print "Updating trim-size for book id:", kwargs.get("project_number")
            current_height_width = pagesize_map[str(current_trim_size)]
            new_height_width = pagesize_map[str(new_trim_size)]

            new_svg = {"COVER": get_svg(new_height_width, "COVER", False),
                       "FIRST_SHEET": get_svg(new_height_width, "FIRST_SHEET", cutback),
                       "SHEET": get_svg(new_height_width, "SHEET", False),
                       "LAST_SHEET": get_svg(new_height_width, "LAST_SHEET", cutback)}
            height_ratio = new_height_width.height / float(current_height_width.height)
            width_ratio = new_height_width.width / float(current_height_width.width)
            for sheet in book.sheets:
                if sheet.type == "COVER":
                    sheet.svg = new_svg["COVER"]
                else:
                    sheet.svg = scale_spread(etree.fromstring(sheet.svg), height_ratio, width_ratio, new_height_width,
                                             etree.fromstring(new_svg[sheet.type]))
                sheet.completed = 0
                sheet.status = None
                db.session.commit()
            book.trim_size = data["trim_size"]
            db.session.commit()
            print "Finished updating trim-size for book id:", kwargs.get("project_number")

        old_page_count = book.page_count
        if book.page_count != data["pages"]:
            if book.page_count > data["pages"]:
                deleted_pages = (book.page_count - data["pages"]) / 2  # 2 pages per spread

                new_second_to_last_id = book.sheets[-(2 + deleted_pages)].id

                for sheet in book.sheets[-2 - deleted_pages:-2]:
                    db.session.delete(sheet)

                book.sheets[-1].parent_sheet = new_second_to_last_id
                book.page_count = data["pages"]
                db.session.commit()
                print "Number of sheets for project %s has been decreased from %s to %s." % (book.id, old_page_count,
                                                                                             data["pages"])
            elif book.page_count < data["pages"]:
                new_pages = (data["pages"] - book.page_count) / 2  # 2 pages per spread
                previous_sheet_id = book.sheets[-2].id
                previous_sheet_page = book.sheets[-2].page
                previous_sheet_sort_order = book.sheets[-2].sort_order
                for new_sheet in xrange(new_pages):
                    sheet = Sheet(
                        book_id=book.id,
                        user_id=book.user_id,
                        parent_sheet=previous_sheet_id,
                        page=str(int(previous_sheet_page) + 1),
                        sort_order=previous_sheet_sort_order + 1,
                        svg=get_svg(decode_trim_size(book.trim_size), "SHEET", False),
                        width=book.width,
                        height=book.height,
                        locked=0,
                        completed=0,
                        active=1,
                        hidden=0,
                        version=0,
                        type="SHEET",
                        thumbnail_url=current_app.config["NORMAL_SHEET_THUMB"])
                    set_model_uuid_and_dates(sheet)
                    db.session.add(sheet)
                    previous_sheet_id = sheet.id
                    previous_sheet_page = sheet.page
                    previous_sheet_sort_order = sheet.sort_order
                book.sheets[-1].parent_sheet = previous_sheet_id
                book.sheets[-1].page = str(int(book.sheets[-1].page) + new_pages)
                book.sheets[-1].sort_order += new_pages
                book.page_count = data["pages"]
                db.session.commit()
                print "Number of sheets for project %s has been increased from %s to %s." % (book.id, old_page_count,
                                                                                             data["pages"])
        return book
    else:
        trim_measurements = find_trim_measurements(decode_trim_size(data["trim_size"]).width)

        book = Book(
                id_=data["id"],
                number=data["number"],
                name=data["name"],
                trim_size=data["trim_size"],
                cover_options=None,
                endsheet_options=None,
                page_count=data["pages"],
                user_id=kwargs.get("user_id"),
                width=2 * trim_measurements["width"],
                height=trim_measurements["height"],
                preferences='PMActive:false,')

        set_model_uuid_and_dates(book)
        db.session.add(book)

        create_default_sheets(book, cutback)

        db.session.commit()

        return book
