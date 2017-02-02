from app.common.utils import log_request_error
from app.models import db, Book, Sheet, Tag

from flask import request, jsonify
from flask.ext.restful import Resource
from lxml import etree
from sqlalchemy.exc import DatabaseError


class UnFlow(Resource):

    def post(self, **kwargs):
        try:
            # Project Number passed from MyYear
            if request.json is None:
                data = {"Error": "No JSON payload detected."}
                resp = jsonify(data)
                resp.status_code = 200
                log_request_error("No JSON payload detected.", request)
                return resp
            else:
                project_number = kwargs.get("projectID")
                if all(x in request.json for x in ["userID", "groups"]):
                    user_id = request.json["userID"]
                    groups = request.json["groups"]
                    group_meta_list = request.json["extra"]
                else:
                    data = {"Error": "Missing Fields: " + ", ".join([x for x in ["userID", "groups"]
                                                                     if x not in request.json])}
                    resp = jsonify(data)
                    resp.status_code = 200
                    log_request_error(str(data), request)
                    return resp
            # Project Object/Book Object
            book = db.session.query(Book).filter_by(number=project_number).first()
            # List of Sheet Objects
            sheets = []
            for sheet in db.session.query(Sheet).filter_by(book_id=book.id).all():
                if not sheet.hidden:
                    sheets.append(sheet)
            # List of Tag Objects to be flowed.
            tags = []
            non_existant = []
            for each in groups:
                temp_tag = db.session.query(Tag).filter_by(galleryID=each, book_id=book.id).first()
                if temp_tag is None:
                    non_existant.append(str(each))
                else:
                    tags.append(temp_tag)
            if len(non_existant) > 0:
                data = {"Error": "Tag(s) [" + ", ".join(non_existant) + "] does(do) not exist."}
                resp = jsonify(data)
                resp.status_code = 400
                log_request_error(str(data), request)
                return resp
            # List of Tag ids
            tag_ids = [x.galleryID for x in tags]
            # Find the sheets you need to edit
            sheets_to_edit = []
            for sheet in sheets:
                svg = etree.fromstring(sheet.svg)
                for rect in svg.iterfind(".//{http://www.w3.org/2000/svg}rect"):
                    rect_gallery = rect.get("{http://svg-edit.googlecode.com}gallery_group")
                    if rect_gallery is not None and rect_gallery in tag_ids:
                        sheets_to_edit.append(sheet)
                        continue
            final_edits = {}
            flown_item_ids = []
            for sheet in sheets_to_edit:
                svg = etree.fromstring(sheet.svg)
                layers = {}
                for child in svg:
                    temp_id = child.get("id")
                    if temp_id == 'background_layer':
                        layers['background_layer'] = child
                    elif temp_id == 'guide_LEFT':
                        layers['guide_left'] = child
                    elif temp_id == 'guide_RIGHT':
                        layers['guide_right'] = child
                    elif temp_id == "flowing_layer":
                        layers['flowing_layer'] = child
                    elif temp_id == "gg_layer":
                        layers['gg_layer'] = child
                    elif temp_id == "folio_layer":
                        layers['folio_layer'] = child
                    elif temp_id == "layer_1":
                        layers['layer_1'] = child
                    elif "defs" in str(child.tag):
                        layers['defs'] = child
                # So long as there's a flowing layer, begin the unflowing process
                if layers.get("flowing_layer") is not None:
                    if layers.get("defs") is None:
                        layers["defs"] = etree.Element("defs")
                    for child in list(layers["flowing_layer"]):
                        flown_item_ids.append(child.get("id"))
                        layers["layer_1"].append(child)
                    # Remove titles for data integrity reasons
                    for child in layers["layer_1"]:
                        if "title" in child.tag:
                            layers["layer_1"].remove(child)
                    for child in layers["flowing_layer"]:
                        if "title" in child.tag:
                            layers["flowing_layer"].remove(child)
                    # Remove <img> tags from all matching <rects>
                    for rect in svg.iterfind(".//{http://www.w3.org/2000/svg}rect"):
                        rect_gallery = str(rect.get("{http://svg-edit.googlecode.com}gallery_group"))
                        if rect_gallery is not None and rect_gallery in tag_ids:
                            rect_parent = rect.getparent()
                            img_sibling = next((x for x in list(rect_parent) if "image" in x.tag), None)
                            if img_sibling is not None:
                                rect_parent.remove(img_sibling)
                                temp_rect_id = "#" + rect.get("id")
                                rect.set("id", temp_rect_id.replace("#border_", "svg_"))
                                del rect.attrib["{http://www.myyear.com}dropTargetImg"]
                                rect.set("{http://www.myyear.com}dropTarget", "undropped")
                                img_use = next((x for x in svg.iterfind(".//{http://www.w3.org/2000/svg}use")
                                                if x.get("{http://www.w3.org/1999/xlink}href") == temp_rect_id), None)
                                defs = img_use.getparent().getparent()
                                defs.remove(img_use.getparent())
                            else:
                                rect.set("opacity", "1")
                                for tag in iter(rect_parent):
                                    if "text" in tag.tag:
                                        for tspan in tag:
                                            tspan.set("opacity", "1")
                        # Re-add all of the drop targets to the flowing layer that were not unflowed
                        elif rect_gallery is not None and rect.getparent().get("id") in flown_item_ids:
                            layers["flowing_layer"].append(rect.getparent())
                    # Reset flowed names back to tag identifiers
                    tspan_still_flown = []
                    tspan_now_unflown = []
                    for tspan in svg.iterfind(".//{http://www.w3.org/2000/svg}tspan"):
                        tspan_gallery = None
                        tspan_text = tspan.text
                        # If the tspan has been edited
                        tspan_parent = tspan.getparent()
                        if tspan_text != "Text Box...":
                            replacement_text = tspan.get("{http://svg-edit.googlecode.com}tag_text")
                            if replacement_text:
                                temp_tag_text = replacement_text.split("_")
                                tspan_gallery = next((x for x in group_meta_list if x["name"] == temp_tag_text[1]),
                                                     None)["id"]
                            else:
                                if tspan_text:
                                    a = tspan_text.split("_")
                                    if len(a) > 1:
                                        tspan_gallery = next((x for x in group_meta_list if x["name"] == a[1]),
                                                             None)["id"]
                                    else:
                                        continue
                            # If it's been tagged to the gallery we're unflowing
                            if tspan_gallery is not None and str(tspan_gallery) in tag_ids:
                                # Make sure certain metadata has been added
                                if replacement_text:
                                    # Assuming that metadata is "delete", remove it completely
                                    tspan.text = replacement_text
                                    del tspan.attrib["{http://svg-edit.googlecode.com}tag_text"]
                                    top_rect = next((x for x in list(tspan_parent.getparent()) if "rect" in x.tag),
                                                    None)
                                    top_rect.set("opacity", "1")
                                    tspan_now_unflown.append(tspan_parent.getparent().get("id"))
                                # If the metadata isn't there, it's a different type of tagged box, deal with it
                                else:
                                    tspan.set("opacity", "1")
                                    top_rect = next((x for x in list(tspan_parent.getparent()) if "rect" in x.tag),
                                                    None)
                                    top_rect.set("opacity", "1")
                                    tspan_now_unflown.append(tspan_parent.getparent().get("id"))
                            # If it's flown but not in our list of gallery ids to unflow, back to the flowing layer!
                            elif tspan_gallery is not None and tspan_parent.getparent().get("id") in flown_item_ids:
                                tspan_still_flown.append(tspan_parent.getparent().get("id"))
                        else:
                            tspan_now_unflown.append(tspan_parent.getparent().get("id"))
                    # Move unflown text objects back to layer_1
                    for tspan_group in set(tspan_now_unflown):
                        layers["layer_1"].append(next((x for x in svg.iterfind(".//{http://www.w3.org/2000/svg}g")
                                                       if tspan_group == x.get("id")), None))
                    # Re-add all of the text objects that were not unflowed to the flowing layer
                    for tspan_group in set(tspan_still_flown):
                        layers["flowing_layer"].append(next((x for x in svg.iterfind(".//{http://www.w3.org/2000/svg}g")
                                                             if tspan_group == x.get("id")), None))
                    # Save the sheet
                    new_svg = etree.Element("svg", nsmap={None: 'http://www.w3.org/2000/svg',
                                                          'se': 'http://svg-edit.googlecode.com',
                                                          'lyb': 'http://www.myyear.com',
                                                          'xlink': "http://www.w3.org/1999/xlink"})
                    # Re-add titles to layers
                    flowing_title = etree.Element("title")
                    flowing_title.text = "Flowing Layer"
                    layers["flowing_layer"].insert(0, flowing_title)

                    layer_1_title = etree.Element("title")
                    layer_1_title.text = "Layer 1"
                    layers["layer_1"].insert(0, layer_1_title)
                    # Build new svg canvas
                    new_svg.set("height", svg.get("height"))
                    new_svg.set("width", svg.get("width"))
                    new_svg.append(layers["background_layer"])
                    new_svg.append(layers["defs"])
                    new_svg.append(layers["flowing_layer"])
                    new_svg.append(layers["layer_1"])
                    new_svg.append(layers["guide_left"])
                    new_svg.append(layers["guide_right"])
                    if layers.get("gg_layer") is not None:
                        new_svg.append(layers["gg_layer"])
                    new_svg.append(layers["folio_layer"])

                    final_edits[sheet] = self.stringify(etree.tostring(new_svg, pretty_print=True))
            # Make sure none of the sheets is marked 'complete'
            current_sheet = None
            for sheet, svg in final_edits.iteritems():
                if sheet.completed is True:
                    data = {"Error": "Cannot unflow as one or more sheets is marked 'Complete'."}
                    resp = jsonify(data)
                    log_request_error("Cannot unflow as one or more sheets is marked 'Complete'.", request)
                    resp.status_code = 400
                    return resp
                if sheet.locked is True:
                    if sheet.user_id != user_id:
                        data = {"Error": "One sheet you are attempting to unflow is currently in use."}
                        resp = jsonify(data)
                        resp.status_code = 400
                        log_request_error("One sheet you are attempting to unflow is currently in use.", request)
                        return resp
                    else:
                        current_sheet = sheet.id
            # Lock Sheets
            # Skip updating the version if it's the current spread as locking thinks another user updated the spread
            try:
                for sheet, svg in final_edits.iteritems():
                    sheet.user_id = user_id
                    sheet.active = True
                    sheet.checkedOut = True
                    if not(current_sheet is not None and sheet.id == current_sheet):
                        sheet.version += 1
                    sheet.locked = True
                db.session.commit()
            except DatabaseError:
                db.session.rollback()
            # Save the sheets back to the DB
            try:
                for sheet, svg in final_edits.iteritems():
                    sheet.svg = svg
                    if not(current_sheet is not None and sheet.id == current_sheet):
                        sheet.version += 1
                db.session.commit()
            except DatabaseError:
                db.session.rollback()
            # Unlock all of the flown sheets
            try:
                for sheet, svg in final_edits.iteritems():
                    sheet.user_id = user_id
                    sheet.active = False
                    sheet.checkedOut = False
                    if not(current_sheet is not None and sheet.id == current_sheet):
                        sheet.version += 1
                    sheet.locked = False
                db.session.commit()
            except DatabaseError:
                db.session.rollback()
            # Update tags as "flown"
            try:
                for tag in tags:
                    tag.flow = False
                db.session.commit()
            except DatabaseError:
                db.session.rollback()
            # Return success message if nothing above failed
            data = {"Message": [sheet.id for sheet in final_edits.iterkeys()]}
            resp = jsonify(data)
            resp.status_code = 200
            return resp
        except Exception as Ex:
            data = {"Error": str(Ex)}
            resp = jsonify(data)
            resp.status_code = 400
            log_request_error(str(Ex), request)
            return resp

    # Strips newlines, tabs and all extra spacing out of the prettified lxml etree
    @staticmethod
    def stringify(prettified):
        finalized = prettified.replace('\n', '').replace('\t', '')
        while ' <' in finalized or '> ' in finalized:
            finalized = finalized.replace(' <', '<')
            finalized = finalized.replace('> ', '>')
        return finalized
