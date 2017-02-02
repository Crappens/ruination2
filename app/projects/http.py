from app import mysocket
from app.base import authorize_request
from app.common.utils import (json_response_factory, not_found_response, bad_request, log_request_error,
    pagesize_map, server_exception, fix_clippaths, remove_broken_filters)
from app.common.exceptions import LockingError
from app.json_model.utils import generate_empty_model
from app.models import db, Book, Sheet, User, Image, Project, ProjectStatus, ProjectMeta
# from new_svg import new_first_svg, new_last_svg, new_full_svg, templated, templated2
from serializers import ProjectSchema
from app.projects.project_api import decode_trim_size, get_svg

# from app.projects.project_api import get_svg, decode_trim_size

import base64
import datetime
import json
# import os
from operator import attrgetter
import requests
from StringIO import StringIO
import zlib

# from boto.s3.key import Key
from flask import request, Blueprint, current_app, jsonify, send_file, Response
from flask.ext.restful import Resource, Api
from flask_restful_swagger import swagger
from lxml import etree, html


def sanitize_clippaths(svg):
    if '"url("' in svg:
        svg = svg.replace('")"', ')"').replace('"url("', '"url(')
    return svg


def compress_string(sheet):
    sheet["compressed"] = base64.b64encode(zlib.compress(sanitize_clippaths(sheet["lowSVG"].encode("utf-8",
                                                                                                   errors="ignore"))))
    del sheet["lowSVG"]
    # For BalfourPages once the json_model column is added to the db.
    if sheet.get("json_model"):
        sheet["compressed_json"] = base64.b64encode(zlib.compress(sheet["json_model"].encode("utf-8", errors="ignore")))
        del sheet["json_model"]


def load_user_from_header():
    user_uuid = request.headers.get('user-id')
    if not user_uuid:
        return

    user = db.session.query(User).filter_by(user_uuid=user_uuid).first()
    if not user:
        return

    return user_uuid


class ProjectResource(Resource):
    """HTTP API for MyYear project resources."""

    serializer = ProjectSchema()
    is_collection = False
    patch_fields = [
        "version", "cover_options", "endsheet_options", "page_count", "preferences"
    ]

    @staticmethod
    def populate_extra_sheet_data(project_data):
        temp_sheets = sorted(project_data['sheets'], key=lambda x: x["sort_order"])
        project_data['sheets'] = temp_sheets
        for sheet in project_data['sheets']:
            sheet['sheetType'] = sheet['type']
            left = (sheet["sort_order"] - 1) * 2
            sheet["page"] = left
            sheet["active"] = False
            compress_string(sheet)

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='getBook',
        responseMessages=[{"message": "Created. The URL of the created blueprint should be in the Location header",
                           "code": 201},
                          {"code": 405, "message": "Invalid input"}]
    )
    def get(self, project_id):
        """
        Get the full book object, including book metadata and a list of all sheet objects with compressed SVG
        """
        book = db.session.query(Book).filter_by(id_=str(project_id)).first()

        if book is None:
            return not_found_response("project", project_id)

        sdata = serialize_book(book)

        self.populate_extra_sheet_data(sdata)

        page_sizes = pagesize_map[sdata["trim_size"]]
        sdata["width"] = page_sizes.width
        sdata["height"] = page_sizes.height

        # print sdata
        return json_response_factory(status_code=200, data={'book': sdata})

    def validate_patch_input(self, patch_dict):
        errors = []
        disallowed = [dif for dif in set(patch_dict.keys()).difference(self.patch_fields)]

        if disallowed:
            errors.append({"unknown field(s)": disallowed})

        if errors:
            log_request_error(str(errors), request)
            return bad_request(data={"errors(s)": errors})
        else:
            return None

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='updateBook',
        parameters=[{"name": "version", "description": "Book version number", "dataType": "number",
                     "required": False, "paramType": "body"},
                    {"name": "cover_options", "description": "Book cover options", "dataType": "string",
                     "required": False, "paramType": "body"},
                    {"name": "endsheet_options", "description": "Book endsheet options", "dataType": "string",
                     "required": False, "paramType": "body"},
                    {"name": "page_count", "description": "Book page count", "dataType": "number",
                     "required": False, "paramType": "body"},
                    {"name": "preferences", "description": "Book preferences. IE grids/guides/snap-to/etc.",
                     "dataType": "string", "required": False, "paramType": "body"}],
        responseMessages=[{"code": 200, "message": "Project/Book payload including all Sheets"},
                          {"code": 400, "message": "Invalid input"}]
    )
    def patch(self, project_id):
        """
        Rarely used, but update certain features of the book/project
        """
        book = db.session.query(Book).filter_by(id_=str(project_id)).first()
        if book is None:
            return not_found_response("project", project_id)

        req_data = request.get_json()
        input_errors = self.validate_patch_input(req_data)

        if input_errors:
            log_request_error(str(input_errors), request)
            return input_errors

        for key, val in req_data.items():
            setattr(book, key, val)

        sdata = serialize_book(book)

        db.session.commit()

        page_sizes = pagesize_map[sdata["trim_size"]]
        sdata["width"] = page_sizes.width
        sdata["height"] = page_sizes.height

        return json_response_factory(status_code=200, data={"project": sdata})

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='upload',
        responseMessages=[{"code": 405, "message": "Deleting is not active for Projects"}]
    )
    def delete(self, project_id):
        """
        Not supported right now
        """
        return json_response_factory(
            status_code=405, data={"error": "Delete not supported on projects"}
        )


class BookResource(Resource):
    """HTTP API for MyYear project resources.
        THIS WILL NOT SAVE PAGES.  THIS IS STRICTLY FOR UPDATING BOOK METADATA.
    """

    is_collection = False

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='updateBook',
        parameters=[{"name": "version", "description": "Book version number", "dataType": "number",
                     "required": False, "paramType": "body"},
                    {"name": "cover_options", "description": "Book cover options", "dataType": "string",
                     "required": False, "paramType": "body"},
                    {"name": "endsheet_options", "description": "Book endsheet options", "dataType": "string",
                     "required": False, "paramType": "body"},
                    {"name": "page_count", "description": "Book page count", "dataType": "number",
                     "required": False, "paramType": "body"},
                    {"name": "preferences", "description": "Book preferences. IE grids/guides/snap-to/etc.",
                     "dataType": "string", "required": False, "paramType": "body"}],
        responseMessages=[{"code": 200, "message": "Project/Book payload including all Sheets"},
                          {"code": 400, "message": "Invalid input"}]
    )
    def put(self):
        """
        Rarely used, but update certain features of the book/project
        """
        req_data = request.get_json()
        book = db.session.query(Book).filter_by(id_=req_data["id"]).first()

        if book is None:
            log_request_error('Project not found: ' + req_data['id'], request)
            return not_found_response("project", req_data["id"])

        del req_data["sheets"]

        for key, val in req_data.items():
            setattr(book, key, val)

        sdata = serialize_book(book)

        db.session.commit()

        page_sizes = pagesize_map[sdata["trim_size"]]
        sdata["width"] = page_sizes.width
        sdata["height"] = page_sizes.height

        for sheet in sdata["sheets"]:
            compress_string(sheet)

        return json_response_factory(status_code=200, data={"project": sdata})


class BookPreferenceResource(Resource):
    """HTTP API for MyYear project resources.
        THIS WILL NOT SAVE PAGES.  THIS IS STRICTLY FOR UPDATING BOOK METADATA.
    """

    is_collection = False

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='updateBook',
        parameters=[{"name": "version", "description": "Book version number", "dataType": "number",
                     "required": False, "paramType": "body"},
                    {"name": "cover_options", "description": "Book cover options", "dataType": "string",
                     "required": False, "paramType": "body"},
                    {"name": "endsheet_options", "description": "Book endsheet options", "dataType": "string",
                     "required": False, "paramType": "body"},
                    {"name": "page_count", "description": "Book page count", "dataType": "number",
                     "required": False, "paramType": "body"},
                    {"name": "preferences", "description": "Book preferences. IE grids/guides/snap-to/etc.",
                     "dataType": "string", "required": False, "paramType": "body"}],
        responseMessages=[{"code": 200, "message": "Project/Book payload including all Sheets"}]
    )
    def put(self, book_id):
        """
        Resource used to update book preferences (grid/guides/etc)
        """
        req_data = request.get_json()

        book = db.session.query(Book).filter_by(id_=book_id).first()

        if book is None:
            log_request_error("not found:" + book_id, request)
            return not_found_response("project", book_id)

        for key, val in req_data.items():
            setattr(book, key, val)

        if book.version:
            book.version += 1
        else:
            book.version = 1
        db.session.commit()

        return json_response_factory(status_code=200, data={"message": True})


class SheetResource(Resource):

    patch_fields = [
        "hidden", "version", "status", "type", "page", "svg", "user_id", "completed", "locked",
        "json_model", "spread_name", "due_date", "approval_status"
    ]
    is_collection = False

    def validate_patch_input(self, patch_data):
        errors = []
        disallowed = [dif for dif in set(patch_data.keys()).difference(self.patch_fields)]

        if disallowed:
            errors.append({"unknown field(s)": disallowed})

        if errors:
            log_request_error(str(errors), request)
            return bad_request(data={"errors(s)": errors})
        else:
            return None

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='getSheet',
        responseMessages=[{"code": 200, "message": "Full sheet object"},
                          {"code": 404, "message": "Sheet not found"}]
    )
    def get(self, sheet_id):
        """
        Returns the sheet object in full with compressed SVG.
        """
        # Pull object from db
        instance = db.session.query(Sheet).filter_by(id_=sheet_id).first()
        if not instance:
            log_request_error("Sheet not found", request)
            return not_found_response("sheet", sheet_id)
        # Serialize to json-returnable object
        sdata = serialize_sheet(instance)
        # Rename/reformat a few variables
        sdata['sheetType'] = sdata["type"]
        left = (sdata["sort_order"] - 1) * 2
        sdata["page"] = left
        compress_string(sdata)
        return json_response_factory(status_code=200, data={"sheet": sdata})

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='updateSheet',
        parameters=[{"name": "hidden", "description": "Sheet hidden status", "dataType": "boolean",
                     "required": False, "paramType": "body"},
                    {"name": "version", "description": "Sheet version number", "dataType": "number",
                     "required": False, "paramType": "body"},
                    {"name": "status", "description": "Sheet active status", "dataType": "boolean",
                     "required": False, "paramType": "body"},
                    {"name": "type", "description": "Sheet type (SHEET, FIRST_SHEET, LAST_SHEET, COVER, MASTER_SHEET)",
                     "dataType": "string", "required": False, "paramType": "body"},
                    {"name": "page", "description": "Sheet left-most page number.  IE 4 if the spread is 4-5.",
                     "dataType": "number", "required": False, "paramType": "body"},
                    {"name": "svg", "description": "Sheet svg content", "dataType": "string",
                     "required": False, "paramType": "body"},
                    {"name": "user_id", "description": "UUID for the user who has locked the sheet",
                     "dataType": "string", "required": False, "paramType": "body"},
                    {"name": "completed", "description": "Sheet completion status", "dataType": "boolean",
                     "required": False, "paramType": "body"},
                    {"name": "locked", "description": "Sheet locked status", "dataType": "boolean",
                     "required": False, "paramType": "body"},
                    {"name": "json_model", "description": "BP json model", "dataType": "string",
                     "required": False, "paramType": "body"},
                    {"name": "spread_name", "description": "Spread name", "dataType": "string",
                     "required": False, "paramType": "body"},
                    {"name": "due_date", "description": "Spread due date", "dataType": "datetime",
                     "required": False, "paramType": "body"},
                    {"name": "approval_status", "description": "Approval status", "dataType": "string",
                     "required": False, "paramType": "body"}],
        responseMessages=[{"code": 200, "message": "JSON blob containing the sheet's new version number"},
                          {"code": 400, "message": "Invalid input"},
                          {"code": 404, "message": "Sheet not found"}]
    )
    def put(self, sheet_id):
        """
        Update a sheet object with a variety of non-required items.
        """
        # Get the sheet from the DB
        instance = db.session.query(Sheet).filter_by(id_=sheet_id).first()

        req_data = request.get_json()

        if instance is None:
            log_request_error("Sheet not found", request)
            return not_found_response("sheet", sheet_id)
        elif instance.locked and instance.user_id == "1":
            # This is a catch of old/bad data
            setattr(instance, "user_id", req_data.get("user_id"))
        elif instance.locked and instance.user_id != req_data.get("user_id"):
            if len(req_data) == 2 and all(x is not None for x in [req_data.get("user_id"), req_data.get("locked")]):
                # Lock the spread, not sure why this is in the update resource
                setattr(instance, "locked", req_data.get("locked"))
                setattr(instance, "user_id", req_data.get("user_id"))
                setattr(instance, "version", instance.version + 1)
                db.session.commit()
                return json_response_factory(status_code=200, data={"version": instance.version})
            else:
                # Return an error if the spread is locked to another user
                log_request_error("Unable to modify locked resource.", request)
                return bad_request({"Error": "Unable to modify locked resource."})

        input_errors = self.validate_patch_input(req_data)
        # Look for and return any invalid input
        if input_errors:
            log_request_error(str(input_errors), request)
            return input_errors
        # Update the object
        bad_completions = []
        for key, val in req_data.items():
            if key == "svg":
                decoded_svg = base64.b64decode(val)
                # Fix the bug where clippaths look like: clippath="url("<pathid>")"
                decompressed = sanitize_clippaths(zlib.decompress(decoded_svg))
                # Sanitize out the random myyear bug that capitalizes a TON of xml attributes,
                # causing the BLACK SPREAD BUG
                # This fixes a bug I introduced...
                decompressed = fix_clippaths(decompressed)
                decompressed = remove_broken_filters(decompressed)
                # This gets rid of the CAPSLOCKED variables
                decompressed = decompressed.replace("STROKE-WIDTH", "stroke-width")
                decompressed = decompressed.replace("STROKE-OPACITY", "stroke-opacity")
                decompressed = decompressed.replace("STROKE-DASHARRAY", "stroke-dasharray")
                decompressed = decompressed.replace("STROKE-LINEJOIN", "stroke-linejoin")
                decompressed = decompressed.replace("STROKE-LINECAP", "stroke-linecap")
                decompressed = decompressed.replace("STROKE", "stroke")
                decompressed = decompressed.replace("FILL-OPACITY", "fill-opacity")
                decompressed = decompressed.replace("FILL", "fill")
                decompressed = decompressed.replace("OPACITY", "opacity")
                decompressed = decompressed.replace("FONT-SIZE", "font-size")
                decompressed = decompressed.replace("FONT-FAMILY", "font-family")
                decompressed = decompressed.replace("TEXT-ANCHOR", "text-anchor")
                decompressed = decompressed.replace("CLIP-PATH", "clip-path")
                # ---- Sanitizing complete
                setattr(instance, key, decompressed)
                setattr(instance, "proofed", 0)
            elif key == "json_model":
                decoded_json = base64.b64decode(val)
                decompressed = sanitize_clippaths(zlib.decompress(decoded_json))
                setattr(instance, key, decompressed)
                setattr(instance, "proofed", 0)
            elif key == 'approval_status':
                # get approval status from DB and set proper id
                status = db.session.query(ProjectStatus).filter_by(project_status_name=val).first()

                if not status:
                    return bad_request({'Error': "Unknown status '%s'" % val})

                instance.approval_status = status
            elif key == 'due_date':
                # validate date
                try:
                    parsed_due_date = datetime.datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
                except (TypeError, ValueError):
                    return bad_request({'Error': "Invalid format of due_date: '%s'" % val})

                instance.due_date = parsed_due_date
            elif key == "completed" and val is True:
                if instance.proofed:
                    setattr(instance, key, val)
                else:
                    bad_completions.append(instance)
            else:
                setattr(instance, key, val)

        # set last_editor field --> using user-id header
        instance.last_editor_uuid = load_user_from_header()

        if "locked" in req_data.keys() and req_data["locked"] is False:
            setattr(instance, "user_id", "")
        # Bump the version and commit
        setattr(instance, "version", instance.version + 1)
        db.session.commit()

        data = {"version": instance.version}
        if req_data.get("completed") is not None:
            data["completed"] = instance.completed

        return json_response_factory(status_code=200, data=data)

    def delete(self, sheet_id):
        """
        Not supported right now
        """
        # TODO: Determine how deletes should be handled for sheets.
        log_request_error("Resource Incomplete", request)
        return json_response_factory(
            status_code=405, data={"error": "Delete not supported on sheets."}
        )


class SheetCheck(Resource):

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='checkSheetVersions',
        parameters=[{"name": "sheets", "description": "List of <sheet_id>_<version>", "dataType": "list",
                     "required": False, "paramType": "body"},
                    {"name": "book_id", "description": "Project uuid as found in Enfold", "dataType": "list",
                     "required": False, "paramType": "body"}],
        responseMessages=[{"code": 200, "message": "JSON blob all changed sheets {svg, version, id, locked}"},
                          {"code": 404, "message": "Sheet not found + <sheet_id>"}]
    )
    def post(self):
        """
        Pass in a list of string is the format sheet.id_sheet.version and check their lock status
        """
        req_data = json.loads(request.data)
        data = []
        if req_data.get("book_id"):
            book = db.session.query(Book).filter_by(id_=req_data["book_id"]).first()
            open_status = 0 if req_data.get("open") is not None else -1
            if len(req_data["sheets"]) + open_status != book.page_count / 2 + 1:
                return json_response_factory(status_code=200, data={"error": "reload project", "save": True})
            if int(req_data["trim_size"]) != int(book.trim_size):
                return json_response_factory(status_code=200, data={"error": "reload project", "save": False})
        else:
            return json_response_factory(status_code=400, data={"Error": "Missing 'book_id' parameter"})
        for sheetTag in req_data["sheets"]:
            sheet_id, version = sheetTag.split("_")
            instance = db.session.query(Sheet).filter_by(id_=sheet_id).first()

            if instance is None:
                log_request_error('SVG not found:' + req_data['id'], request)
                return not_found_response("svg", req_data["id"])

            if int(instance.version) != int(version):
                tmp = sanitize_clippaths(base64.b64encode(zlib.compress(instance.svg.encode("utf-8", errors="ignore"))))
                data.append({"compressed": tmp, "version": instance.version, "id": instance.id,
                             "locked": instance.locked, "completed": instance.completed, "proofed": instance.proofed})
        return json_response_factory(status_code=200, data={"sheets": data})


class CheckLockStatus(Resource):

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='checkLockStatus',
        parameters=[{"name": "sheets", "description": "List of <sheet_id>_<version>", "dataType": "list",
                     "required": False, "paramType": "body"}],
        responseMessages=[{"code": 200, "message": "JSON blob with {locked, user_name, user_id, last_updated}"},
                          {"code": 404, "message": "Sheet not found + <sheet_id>"}]
    )
    def get(self, sheet_id):
        """
        Get full lock info for a single sheet
        """
        instance = db.session.query(Sheet).filter_by(id_=sheet_id).first()
        if instance.user_id is not None and len(instance.user_id) == 32:
            resp = requests.get(url=current_app.config["ENFOLD_URL"] + "/users/" + instance.user_id,
                                headers={"Content-Type": "application/json",
                                         "X-Auth-Token": current_app.config["ENFOLD_ADMIN_TOKEN"]})
            user_name = resp.json()["user"]["name"]
        else:
            user_name = None
        return json_response_factory(status_code=200, data={"locked": instance.locked, "user_id": instance.user_id,
                                                            "user_name": user_name, "updated": instance.updated})

    @staticmethod
    def populate_user_names(sheets):
        """add the user names instead of just the user_ids"""
        # !! This is a kludge and ought to be handled by sqlAlchemy directly.
        #    I'm basically manually doing a join here to get the user name. :/
        #    (I'm just not sure how to cram it into the BookService API)
        user_names = {}
        for x in set(sheet.get('user_id') for sheet in sheets):
            if x == '' or x is None:
                user_names[x] = ''
            else:
                user_names[x] = db.session.query(User).filter_by(user_uuid=x).first().user_name
        for sheet in sheets:
            sheet['user_name'] = user_names[sheet['user_id']]

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='checkLockStatus',
        parameters=[{"name": "sheets", "description": "List of sheet.id", "dataType": "list",
                     "required": True, "paramType": "body"}],
        responseMessages=[{"code": 200, "message": "JSON blob {sheets: list}"},
                          {"code": 404, "message": "Sheet not found + <sheet_id>"}]
    )
    def post(self):
        """
        Returns full lock status for a list of sheet.id
        """
        req_data = json.loads(request.data)
        sheet_ids = req_data["sheets"]
        result = []
        for sheet_id in sheet_ids:
            instance = db.session.query(Sheet).filter_by(id_=sheet_id).first()
            if instance is None:
                log_request_error("Sheet not found", request)
                return not_found_response("sheet", sheet_id)
            result.append({
                'status': instance.status,
                'sheetType': instance.type,
                'active': req_data['current'] == sheet_id,
                'completed': instance.completed,
                'locked': bool(instance.locked),
                'id': sheet_id,
                'user_id': instance.user_id,
                'proofed': instance.proofed
            })
        self.populate_user_names(result)
        return json_response_factory(status_code=200, data={"sheets": result})


class CheckVersionNumber(Resource):

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='checkLockStatus',
        responseMessages=[{"code": 200, "message": "JSON blob {version}"},
                          {"code": 404, "message": "Sheet not found + <sheet_id>"}]
    )
    def get(self, sheet_id):
        """
        Get the version number for a sheet
        """
        instance = db.session.query(Sheet).filter_by(id_=sheet_id).first()
        if instance is None:
            log_request_error("Sheet not found", request)
            return not_found_response("sheet", sheet_id)
        return json_response_factory(200, data={"version": instance.version})


class BookPreferences(Resource):

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='bookPreferences',
        notes='Thanks to MyYear catching and hiding error messages, this one returns a 200 on error.',
        responseMessages=[{"code": 200, "message": "JSON blob {preferences}"},
                          {"code": 200, "message": "Book not found: + book.id"}]
    )
    def get(self, book_id):
        """
        Get a book's preferences which atm is a comma separated string
        """
        instance = db.session.query(Book).filter_by(id_=book_id).first()

        if instance is None:
            log_request_error('Book not found:' + book_id, request)
            return json_response_factory(200, {'error': "No book by id " + book_id})
        else:
            return json_response_factory(200, {'preferences': instance.preferences})


class Token(Resource):

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='checkTokenValidity',
        responseMessages=[{"code": 200, "message": "JSON blob {valid: true or false}"}]
    )
    def get(self, token_uuid):
        """
        Unused as far as I'm aware, but check the validity of a X-Auth-Token
        """
        print "---------Token resource being used"
        resp = requests.get(current_app.config["ENFOLD_URL"] + "/token/" + token_uuid,
                            headers={"X-Auth-Token": current_app.config["ENFOLD_ADMIN_TOKEN"]})
        data = {"valid": resp.json()["Token"]}
        resp2 = jsonify(data)
        resp2.status_code = 200
        return resp2


class ApplyTemplate(Resource):

    def post(self):
        req_data = json.loads(request.data)
        start = int(req_data["start"])
        end = int(req_data["end"])
        template_id = int(req_data["templateId"])
        book_id = req_data["bookId"]
        current_sheet = req_data["currentSheetId"]
        user_id = req_data["userId"]

        sheets = db.session.query(Sheet).filter_by(book_id=book_id).order_by(Sheet.sort_order).all()

        sheets.pop(0)  # Cover sheet
        sheets.pop(0)  # First sheet
        sheets.pop(-1)  # Last sheet

        template = db.session.query(Image).filter_by(image_id=template_id).first()
        tmp = requests.get(current_app.config["BUCKET"] + template.image_url)
        template_svg = etree.fromstring(tmp.content)
        layer_1 =  next((x for x in list(template_svg) if x.get("id") == "layer_1"), None)
        defs =  next((x for x in list(template_svg) if "defs" in x.tag), None)

        sheets_to_edit = []
        for num, sheet in enumerate(sheets):
            left = (num + 1) * 2
            right = (num + 1) * 2 + 1

            if left >= start and right <= end:
                sheets_to_edit.append(sheet)

        for sheet in sheets_to_edit:
            if sheet.id == current_sheet:
                continue
            if sheet.locked or sheet.completed:
                data = {"Error": "One or more of your spreads is locked or completed."}
                resp = jsonify(data)
                resp.status_code = 200
                return resp

        for sheet in sheets_to_edit:
            if sheet.id == current_sheet:
                continue
            sheet.locked = True
            sheet.user_id = user_id
        db.session.commit()

        for sheet in sheets_to_edit:
            if sheet.id == current_sheet:
                continue
            sheet_svg = etree.fromstring(sheet.svg)
            t_layer_1 =  next((x for x in list(sheet_svg) if x.get("id") == "layer_1"), None)
            t_defs =  next((x for x in list(sheet_svg) if "defs" in x.tag), None)
            sheet_svg.remove(t_layer_1)
            if t_defs is not None:
                sheet_svg.remove(t_defs)
            if defs is not None:
                sheet_svg.insert(1, defs)
                sheet_svg.insert(2, layer_1)
            else:
                sheet_svg.insert(1, layer_1)
            sheet.svg = stringify(etree.tostring(sheet_svg, pretty_print=True))
            sheet.locked = False
            sheet.user_id = None
            sheet.version += 1
        db.session.commit()

        data = {"Success": [sheet.id for sheet in sheets_to_edit]}
        resp = jsonify(data)
        resp.status_code = 200
        return resp


# UPDATE ALL TEMPLATES AT ONCE
# class UpdateTemplates(Resource):
#
#     def get(self):
#         if not request.headers["ADMIN"] and request.headers["ADMIN"] != "MagicTheGathering":
#             data = {"Error": "You don't have permission to do this action."}
#             resp = jsonify(data)
#             resp.status_code = 403
#             return resp
#
#         for _file in os.listdir(os.path.join("home", "crappens", "DEV", "ruination", "app", "flowing",
#                                              "template_generator", "tmp")):
#
#             instance = db.session.query(Image).filter_by(image_original_file_name=_file).first()
#             if instance is None:
#                 print _file
#                 continue
#
#             s3_path = instance.image_url.split(".")[0]
#             print s3_path
#             item = open(os.path.join("home", "crappens", "DEV", "ruination", "app", "flowing", "template_generator",
#                                      "tmp", _file), "rb")
#
#             try:
#                 bucket = current_app.s3_conn.get_bucket(current_app.config['S3_IMAGE_REPO_BUCKET'])
#                 key = Key(bucket, s3_path)
#                 bucket.delete_key(key)
#             except Exception as Ex:
#                 print Ex
#
#             try:
#                 content_type = "image/svg"
#                 bucket = current_app.s3_conn.get_bucket(current_app.config['S3_IMAGE_REPO_BUCKET'])
#                 key = Key(bucket, s3_path + ".svg")
#                 key.set_metadata('Content-Type', content_type)
#                 key.set_contents_from_string(item.read())
#             except Exception as Ex:
#                 print Ex
#
#         return json_response_factory(200, data={"Status": "Found it"})

# Coming to a Yearbook near you, Summer 2016
# class UpdateSheetSizes(Resource):
#
#     def get(self, book_id):
#         exclude = ["Y50208", "Y50114", "Y50115", "Y50116", "Y50093"]
#
#         if request.headers.get("Auth-Check") != "Stone Brewing":
#             data = {"Status": "You aren't allowed to do this"}
#             resp2 = jsonify(data)
#             resp2.status_code = 403
#             return resp2
#
#         book = db.session.query(Book).filter_by(id_=book_id).first()
#
#         match = {"SHEET": get_svg(decode_trim_size(book.trim_size), "SHEET"),
#                  "LAST_SHEET": get_svg(decode_trim_size(book.trim_size), "LAST_SHEET"),
#                  "FIRST_SHEET": get_svg(decode_trim_size(book.trim_size), "FIRST_SHEET")}
#
#         # sheets = db.session.query(Book).filter_by(id_=book_id).first().sheets
#
#         print "Starting update process"
#         for book in db.session.query(Book).all():
#             if book.number not in exclude:
#                 if any(x in book.number for x in ["Y", "M"]):
#                     print book.number
#                     if len(book.sheets) == 0:
#                         continue
#                     for sheet in book.sheets:
#                         if sheet.type == "COVER":
#                             continue
#                         sheet.svg = match[sheet.type]
#                         sheet.version += 1
#                         db.session.commit()
#                 else:
#                     print "Skipping:", book.number
#             else:
#                 print "Skipping:", book.number
#
#
#             # print book.number if book.number not in exclude else "Skipping: " + book.number
#
#         # for sheet in sheets:
#         #     if sheet.type == "COVER":
#         #         continue
#         #     sheet.svg = match[sheet.type]
#         #     sheet.version += 1
#         #     db.session.commit()
#
#         data = {"Status": "Resized"}
#         resp = jsonify(data)
#         resp.status_code = 200
#         return resp
#
#         # width = 1296
#         # height = 828
#
#             # svg = etree.fromstring(sheet.svg)
#             #
#             # layer_1 = next((x for x in list(svg) if x.get("id") == "layer_1"), None)
#             # defs = next((x for x in list(svg) if "defs" in x.tag), None)
#             # backgrounds = next((x for x in list(svg) if x.get("id") == "background_layer"), None)
#             # flowing = next((x for x in list(svg) if x.get("id") == "flowing_layer"), None)
#             #
#             # new_svg = etree.fromstring(match[sheet.type])
#             # new_layer_1 = next((x for x in list(new_svg) if x.get("id") == "layer_1"), None)
#             # new_backgrounds = next((x for x in list(new_svg) if x.get("id") == "background_layer"), None)
#             #
#             # for obj in backgrounds.getiterator():
#             #     if "rect" in obj.tag:
#             #         if obj.get("{http://www.myyear.com}background") == "F":
#             #             img_width = width
#             #             img_x = 0
#             #         elif obj.get("{http://www.myyear.com}background") == "R":
#             #             img_width = width / 2
#             #             img_x = width / 2
#             #         elif obj.get("{http://www.myyear.com}background") == "L":
#             #             img_width = width / 2
#             #             img_x = 0
#             #         else:
#             #             continue
#             #
#             #         obj.set("x", str(img_x))
#             #         obj.set("width", str(img_width))
#             #         obj.set("height", str(height))
#             #         obj.set("y", str(0))
#             #
#             #         parent = obj.getparent()
#             #
#             #         if len(list(parent)) > 1:
#             #             sibling = next(x for x in parent if x.get("clip-path") is not None)
#             #             img_tag = list(sibling)[0]
#             #
#             #             img_tag.set("x", str(img_x))
#             #             img_tag.set("width", str(img_width))
#             #             img_tag.set("height", str(height))
#             #             img_tag.set("y", str(0))
#             #
#             # new_svg.remove(new_backgrounds)
#             # new_svg.insert(0, backgrounds)
#             # if new_layer_1 is not None:
#             #     new_svg.remove(new_layer_1)
#             # new_svg.insert(1, layer_1)
#             # if flowing is not None:
#             #     new_svg.insert(1, flowing)
#             # if defs is not None:
#             #     new_svg.insert(1, defs)
#
#             # sheet.svg = stringify(etree.tostring(new_svg, pretty_print=True))
#         #     sheet.svg = match[sheet.type]
#         #     sheet.version += 1
#         #     db.session.commit()
#         # data = {"Status": "Resized"}
#         # resp = jsonify(data)
#         # resp.status_code = 200
#         # return resp

# class WipeBooks(Resource):
#
#     def get(self):
#         books = ["917701", "922803", "923301", "900901", "924701", "924712", "935106", "935202", "901201", "934601", "928803", "935201", "901701", "911303", "962501", "903301", "922820", "936803", "935701", "923901", "935101", "903401", "916501", "967005", "903403", "925802", "907801", "974003", "974002", "921701", "935601", "962301", "970001", "936801", "936802", "922901", "904601", "929401", "908002", "932601", "911302", "938901", "930107", "933401", "930302", "914501", "925812", "936902", "913203", "915301", "938201", "933202", "933201", "922818", "908008", "939001", "929804", "903309", "936804", "932401", "963701", "925801", "937801", "930401", "935108", "924709", "938701", "923401", "922823", "909601", "910401", "938401", "930101", "920005", "920001", "911304", "928806", "932101", "930304", "932801", "928801", "908801", "912401", "930106", "965701", "922804", "916310", "924703", "900905", "900904", "905201", "908009", "922822", "924713", "922816", "969501", "901601", "921401", "937902", "936901", "914701", "938301", "911301", "903308", "923403", "930301", "924707", "908001", "977002", "916301", "918901", "933901", "937701", "910701", "924301", "921601", "935801", "936701", "921801", "921201", "928808", "928809", "936904", "923101", "922808", "914610", "922821", "922802", "937601", "913201", "903202", "938501", "931901", "935001", "935702", "935501", "925817", "976003", "923201", "929801", "924401", "937901", "900906", "922801", "938101", "938802", "938801", "938001", "908004", "931905", "922815", "915302", "936201", "903201", "968401", "931908"]
#         # books = ["950105"]
#         for book in books:
#             f_book = "Y" + book[1:]
#             print f_book
#             book = db.session.query(Book).filter_by(number=f_book).first()
#             if book:
#                 db.session.query(Sheet).filter_by(book_id=book.id).delete()
#                 db.session.delete(book)
#                 db.session.commit()

#
# class PullBryndasBook(Resource):
#
#     def get(self):
#         book = db.session.query(Book).filter_by(number='Y50119').first()
#         if book:
#             sheets = db.session.query(Sheet).filter_by(book_id=book.id).order_by(Sheet.sort_order).all()
#             for sheet in sheets:
#                 print sheet.id, sheet.sort_order
#
#                 folder = os.path.join("home", "crappens", "Desktop", "bryndas_book_svg")
#
#                 with open(os.path.join(folder, str(sheet.sort_order) + ".svg"), 'wb') as f:
#                     f.write(sheet.svg)
#
#
# class PushBryndasBook(Resource):
#
#     def get(self):
#         book = db.session.query(Book).filter_by(number='Y50119').first()
#         if book:
#             sheets = db.session.query(Sheet).filter_by(book_id=book.id).order_by(Sheet.sort_order).all()
#             count = 0
#             for sheet in sheets:
#                 print sheet.id, sheet.sort_order
#
#                 folder = os.path.join("home", "crappens", "Desktop", "bryndas_book_svg")
#                 print sheet.sort_order, count
#
#                 with open(os.path.join(folder, str(sheet.sort_order) + ".svg"), 'r') as f:
#                     sheet.svg = f.read()
#                     sheet.version += 1
#                     db.session.commit()
#                     count += 1


class ReorderSheets(Resource):

    @swagger.operation(
        # responseClass=ModelClass.__name__,
        nickname='reorderSheets',
        responseMessages=[{"code": 200, "message": "{result: ok}"}]
    )
    @authorize_request
    def post(self, book_id, old_pos, new_pos):
        """Reorder sheets based on position/sort-order.

        :param book_id:
        :param old_pos:
        :param new_pos:
        :return:
        """
        book = db.session.query(Book).filter_by(id_=book_id).first()

        sheets = sorted(book.sheets, key=lambda sheet: sheet.sort_order)
        by_id = dict((sheet.id, sheet) for sheet in sheets)
        if any(sheet.locked for sheet in sheets):
            raise LockingError("Cannot reorder when sheets are open.")

        # prevent moving the cover, first sheet, or last sheet:
        if sheets[old_pos].type != 'SHEET':
            raise ValueError("Only normal sheets can be moved.")
        if new_pos in [0, 1, len(sheets)]:
            raise ValueError("Invalid destination.")

        # move it:
        sheets.insert(new_pos, sheets.pop(old_pos))

        # update the sort_order column
        # ... and rebuild the linked list        (!! Do we even need this?)
        parent = None
        for i, target in enumerate(sheets):
            if i == 0:
                parent = target.id
            else:
                sheet = by_id[target.id]
                changed = (sheet.parent_sheet != parent) or (sheet.sort_order != i)
                sheet.parent_sheet = parent
                sheet.sort_order = i
                if changed:
                    sheet.version += 1
                parent = sheet.id

        db.session.commit()

        # tell all clients to update their sheet ladder
        # pass the user id so it doesn't bother doing it twice.
        mysocket.MyYearCommander.broadcast(request.headers['ProjectId'],
                                           ['evt-reorder', request.headers['UserId'], old_pos, new_pos])

        # MyYear already renumbers it on the client side, so there's not much else to report.
        return json_response_factory(200, {'result': "ok"})


class ClearSheet(Resource):

    @swagger.operation(
        nickname='clearSheets',
        parameters=[{"name": "sheets_ids", "description": "Ids of sheets to be cleared", "dataType": "list",
                     "required": False, "paramType": "body"}],
        responseMessages=[{"code": 200, "message": "{result: ok}"}]
    )
    def post(self):
        # get user from header
        user_id = load_user_from_header()
        if not user_id:
            return bad_request({'Error': 'Missing or bad user-id'})

        # get sheet(s) id(s)
        req_data = request.get_json()
        sheets_ids = req_data.get('sheets_ids')
        if not sheets_ids:
            return bad_request({'Error': 'Missing sheet(s) id(s)'})

        # Load sheet(s) from DB
        sheets = db.session.query(Sheet).filter(Sheet.id_.in_(sheets_ids)).all()
        if len(sheets) != len(sheets_ids):
            loaded_ids = map(attrgetter('id'), sheets)
            diff = list(set(sheets_ids) - set(loaded_ids))
            return bad_request({'Error': 'Some sheets not found %s' % diff})

        # get book for sheets
        book_id = set(map(attrgetter('book_id'), sheets))
        if len(book_id) != 1:
            return bad_request({'Error': 'Cannot clear sheets from different boook.'})

        book_id = book_id.pop()
        book = db.session.query(Book.trim_size).filter_by(id_=book_id).first()
        if not book:
            return bad_request({'Error': 'Book %s not found' % book_id})

        # cutback
        project_meta = db.session.query(ProjectMeta.project_meta_value).join(
            Project, Project.project_id == ProjectMeta.project_id
        ).filter(
            Project.project_uuid == book_id,
            ProjectMeta.project_meta_name == 'bind_type',
        ).first()

        bind_type = project_meta.project_meta_value if project_meta else 3
        cutback = bind_type in [3, 'Smythe']

        decoded_trim_size = decode_trim_size(book.trim_size)
        empty_model_str = json.dumps(generate_empty_model())

        # clear spreads
        rollback = None
        for sheet in sheets:
            if sheet.completed == 1 or sheet.status == 'PUBLISHED':
                # cannot be cleared
                rollback = sheet.id_
                break

            if sheet.locked == 1:
                now = datetime.datetime.now()
                if sheet.user_id != user_id and sheet.locked_until > now:
                    # cannot be cleared -> locked by other user
                    rollback = sheet.id_
                    break

            # clear sheet svg and json_model
            sheet.svg = get_svg(decoded_trim_size, sheet.type_, cutback)
            # empty json_model
            sheet.json_model = empty_model_str

            # set last_editor
            sheet.last_editor_uuid = user_id

            # reset sheet thumbnail to default for given sheet type
            if sheet.type == 'FIRST_SHEET':
                sheet.thumbnail_url = current_app.config['FIRST_SHEET_THUMB']
            elif sheet.type == 'LAST_SHEET':
                sheet.thumbnail_url = current_app.config['LAST_SHEET_THUMB']
            else:
                # for COVER + SHEET
                sheet.thumbnail_url = current_app.config['NORMAL_SHEET_THUMB']

            # bump sheet version
            sheet.version += 1

        if rollback:
            db.session.rollback()
            return bad_request({'Error': 'Unable to clear spread %s' % rollback})

        try:
            db.session.commit()
        except Exception, e:
            db.session.rollback()
            return server_exception(e)

        return json_response_factory(200, {'result': 'Cleared %s spreads' % len(sheets_ids)})


class MultiUpdateSheetResource(Resource):
    @swagger.operation(
        nickname='updateSheets',
        parameters=[{"name": "sheets_ids", "description": "Ids of sheets to be approved", "dataType": "list",
                     "required": True, "paramType": "body"},
                    {"name": "approval_status", "description": "Approval status", "dataType": "list",
                     "required": False, "paramType": "body"},],
        responseMessages=[{"code": 200, "message": "{result: ok}"}]
    )
    def post(self):
        # get user from header
        user_id = load_user_from_header()
        if not user_id:
            return bad_request({'Error': 'Missing or bad user-id'})

        req_data = request.get_json()
        sheets_ids = req_data.get('sheets_ids')
        if not sheets_ids:
            return bad_request({'Error': 'Missing sheets_ids'})

        sheets = db.session.query(Sheet).filter(Sheet.id_.in_(sheets_ids)).all()
        if len(sheets) != len(sheets_ids):
            loaded_ids = map(attrgetter('id'), sheets)
            diff = list(set(sheets_ids) - set(loaded_ids))
            return bad_request({'Error': 'Some sheets not found %s' % diff})

        approval_status = req_data.get('approval_status')
        if not approval_status:
            return bad_request({'Error': 'Missing approval_status'})

        status = db.session.query(ProjectStatus).filter_by(project_status_name=approval_status).first()
        if not status:
            return bad_request({'Error': "Unknown status '%s'" % approval_status})

        for sheet in sheets:
            if sheet.locked == 1:
                now = datetime.datetime.now()
                if sheet.user_id != user_id and sheet.locked_until > now:
                    # cannot be updated -> locked by other user
                    err_message = 'Unable to update spread %s' % sheet.id_
                    db.session.rollback()
                    return bad_request({'Error': err_message})

            sheet.approval_status = status

            # update version and set last_editor
            sheet.last_editor_uuid = user_id
            sheet.version += 1

        try:
            db.session.commit()
        except Exception, e:
            db.session.rollback()
            return server_exception(e)

        return json_response_factory(200, {'result': 'Updated %s spreads' % len(sheets_ids)})


class RawSVG(Resource):
    def get(self, sheet_id):
        sheet_id = sheet_id
        sheet = db.session.query(Sheet).filter_by(id_=sheet_id).first()
        svg_io = StringIO()
        svg_io.write(sheet.svg)
        svg_io.seek(0)
        return Response(svg_io, mimetype='image/svg+xml')


def serialize_book(book):
    response = {}
    response['bingingEdge'] = 'side',
    response['bleedMargin'] = book.bleed_margin
    response['bookConfig'] = None
    response['bookName'] = book.name
    response['coverHidden'] = False
    response['cover_options'] = book.cover_options
    response['deletedTimeStamp'] = None
    response['endsheet_options'] = book.endsheet_options
    response['height'] = book.height
    response['id'] = book.id
    response['insertByUserId'] = None
    response['insertDate'] = book.created
    response['number'] = book.number
    response['pageCount'] = book.page_count
    response['preferences'] = book.preferences
    response['trim_size'] = book.trim_size
    response['updateByUserId'] = None
    response['updateDate'] = book.updated
    response['userId'] = book.user_id
    response['version'] = book.version
    response['versionSource'] = None
    response['width'] = book.width

    response['sheets'] = []

    for sheet in db.session.query(Sheet).filter_by(book_id=book.id).all():
        response['sheets'].append(serialize_sheet(sheet))

    return response


def serialize_sheet(sheet):
    response = {}
    response['active'] = sheet.active
    response['bleed_margin'] = sheet.bleed_margin
    response['bookId'] = sheet.book_id
    response['completed'] = sheet.completed
    response['lowSVG'] = sheet.svg
    response['height'] = sheet.height
    response['hidden'] = sheet.hidden
    response['id'] = sheet.id
    response['locked'] = sheet.locked
    response['parent_sheet'] = sheet.parent_sheet
    response['project_id'] = ""
    response['sort_order'] = sheet.sort_order
    response['status'] = sheet.status
    response['thumbnail_url'] = sheet.thumbnail_url
    response['type'] = sheet.type
    response['user_id'] = sheet.user_id
    response['version'] = sheet.version
    response['width'] = sheet.width
    response['json_model'] = sheet.json_model
    response['due_date'] = sheet.due_date
    response['spread_name'] = sheet.spread_name
    response['approval_status'] = sheet.approval_status.project_status_name
    response['last_editor'] = sheet.last_editor.user_name if sheet.last_editor else None
    response['proofed'] = sheet.proofed

    return response


# Strips newlines, tabs and all extra spacing out of the prettified lxml etree
def stringify(prettified):
    finalized = prettified.replace('\n', '').replace('\t', '')
    while ' <' in finalized or '> ' in finalized:
        finalized = finalized.replace(' <', '<')
        finalized = finalized.replace('> ', '>')
    return finalized


blueprint = Blueprint(name="projects", import_name=__name__)
api = swagger.docs(Api(app=blueprint),
                   api_spec_url="/docs",
                   produces=["application/json", "text/html"])

api.add_resource(ProjectResource,
                 '/projects/<string:project_id>',
                 '/projects/<string:project_id>.json',
                 '/projects/<string:project_id>/book.json')
api.add_resource(CheckLockStatus, '/sheet/status/<string:sheet_id>',
                                  '/sheet/status')
api.add_resource(SheetResource,
                 '/sheet/view/<string:sheet_id>.json',
                 '/sheet/view/<string:sheet_id>')
api.add_resource(CheckVersionNumber, '/sheet/checkversion/<string:sheet_id>')
api.add_resource(BookResource,
                 '/books/update.json',
                 '/books/update')
api.add_resource(BookPreferenceResource, '/books/preferences/<string:book_id>.json')
api.add_resource(SheetCheck, '/sheet/check.json')
api.add_resource(Token, '/token/<string:token_uuid>')
api.add_resource(BookPreferences, '/book/preferences/<string:book_id>')
# api.add_resource(UpdateSheetSizes, '/resizePages/<string:book_id>')
api.add_resource(ReorderSheets, "/reorder/<string:book_id>/<int:old_pos>/<int:new_pos>")
api.add_resource(ApplyTemplate, "/applyTemplate")
# api.add_resource(UpdateTemplates, "/updateTemplates")
api.add_resource(ClearSheet, '/sheet/clear')
api.add_resource(MultiUpdateSheetResource, '/sheet/update')
# api.add_resource(WipeBooks, '/destroyEverything')
# api.add_resource(PullBryndasBook, '/brynda')
# api.add_resource(PushBryndasBook, '/brynda2')
api.add_resource(RawSVG, '/puresvg/<string:sheet_id>')
