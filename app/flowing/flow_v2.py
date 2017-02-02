from app.common.utils import log_request_error
from app.models import db, Book, Sheet, Tag

from flask import current_app, request, jsonify
from flask.ext.restful import Resource
from lxml import etree
from sqlalchemy.exc import DatabaseError

import requests


class Flow(Resource):

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
                if all(x in request.json for x in ["token", "userID", "groups"]):
                    token = request.json["token"]
                    user_id = request.json["userID"]
                    groups = request.json["groups"]
                    group_meta_list = request.json["extra"]
                else:
                    data = {"Error": "Missing Fields: " + ", ".join([x for x in ["token", "userID", "groups"]
                                                                     if x not in request.json])}
                    resp = jsonify(data)
                    resp.status_code = 200
                    log_request_error(str(data), request)
                    return resp
            # Project Object
            book = db.session.query(Book).filter_by(number=project_number).first()
            if book is None:
                data = {"Error": "Book " + project_number + " does not exist."}
                resp = jsonify(data)
                resp.status_code = 200
                log_request_error(str(data), request)
                return resp
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
                resp.status_code = 200
                log_request_error(str(data), request)
                return resp
            # List of Tag ids
            tag_ids = [x.galleryID for x in tags]
            # Find the sheets you need to edit and preserve the group numbering if found
            pages_to_edit = []
            gallery_tag_numbers = {}
            for sheet in sheets:
                sheet_id = sheet.id
                svg = etree.fromstring(sheet.svg)
                for rect in svg.iterfind(".//{http://www.w3.org/2000/svg}rect"):
                    rect_gallery = rect.get("{http://svg-edit.googlecode.com}gallery_group")
                    if rect_gallery is not None and rect_gallery in tag_ids:
                        if gallery_tag_numbers.get(rect_gallery) is None:
                            gallery_tag_numbers[rect_gallery] = {"students": [], "staff": []}
                        if sheet_id not in pages_to_edit:
                            pages_to_edit.append(sheet_id)
                        rect_g_tag = rect.getparent()
                        rect_sibling_text = next((x for x in list(rect_g_tag) if "text" in x.tag), None)
                        if rect_sibling_text is not None:
                            teacher_flag = False
                            for rect_sub_text in list(rect_sibling_text):
                                if rect_sub_text.text == "Teacher":
                                    teacher_flag = True
                            if teacher_flag is True:
                                gallery_tag_numbers[rect_gallery]["staff"].append(
                                    int(rect.get("{http://svg-edit.googlecode.com}gallery_number"))
                                )
                            else:
                                gallery_tag_numbers[rect_gallery]["students"].append(
                                    int(rect.get("{http://svg-edit.googlecode.com}gallery_number"))
                                )
            # Sort the tagged boxes numerically
            # Yes the variable names here are in bad form, but I'm running out of ways to say gallery/tag
            for each in gallery_tag_numbers:
                for each2 in gallery_tag_numbers[each]:
                    gallery_tag_numbers[each][each2] = sorted(gallery_tag_numbers[each][each2])
            # Call image-repo and get the images for each gallery needing to be flown
            gallery_lists = {}
            headers = {"Content-Type": "application/json", "project-id": book.id,
                       "user-id": user_id, "x-subject-token": token}
            for x in tag_ids:
                term_type, term_name = x.split("/")
                new_resp = requests.get(current_app.config.get("STUDENT_MANAGER") + "/students/flow/" + term_type + "/" +
                                        term_name, headers=headers, verify=False)
                if new_resp.status_code != 200:
                    data = {"Error": new_resp.json()["messages"]}
                    resp = jsonify(data)
                    resp.status_code = 200
                    log_request_error(str(data), request)
                    return resp
                temp = new_resp.json()["students"]
                # Alphabetize the people in the lists in the format LastName, FirstName
                staff_list = sorted([y for y in temp if y['staff'] == 1], key=lambda g: (g['last_name'],
                                                                                         g['first_name']))
                student_list = sorted([z for z in temp if z['staff'] == 0], key=lambda g: (g['last_name'],
                                                                                           g['first_name']))
                # If we're flowing the Staff only, then make them the main priority
                if len(student_list) == 0:
                    student_list = staff_list
                gallery_lists[x] = {"students": student_list, "staff": staff_list}
            # Match alphabetized people with their tagged box
            for gallery_id, person_list in gallery_lists.iteritems():
                # Make sure there are enough tagged drop targets before trying to build our map
                if len(person_list["students"]) > len(gallery_tag_numbers[gallery_id]["students"]):
                    data = {"Error": "Not enough tagged boxes for gallery " + gallery_id}
                    resp = jsonify(data)
                    resp.status_code = 200
                    log_request_error(str(data), request)
                    return resp
                # Assign students/staff their tspan numbers
                for x, person in enumerate(person_list["students"]):
                    person["tag_num"] = gallery_tag_numbers[gallery_id]["students"][x]
                # Let flowing teachers be all or nothing per gallery, they will be alphabetical
                if len(gallery_tag_numbers[gallery_id]["staff"]) > 0:
                    max_index = len(gallery_tag_numbers[gallery_id]["staff"]) - 1
                    for x, person in enumerate(person_list["staff"]):
                        if x <= max_index:
                            person["tag_num"] = gallery_tag_numbers[gallery_id]["staff"][x]
                        else:
                            data = {"Error": "Not enough tagged boxes for teachers of gallery " + gallery_id}
                            resp = jsonify(data)
                            resp.status_code = 200
                            log_request_error(str(data), request)
                            return resp
            # Begin Flowing
            final_edits = {}
            for sheet_id in pages_to_edit:
                sheet = db.session.query(Sheet).filter_by(id_=sheet_id).first()
                svg = etree.fromstring(sheet.svg)
                # Determine the next available svg_# style ID
                element_numbers = []
                for x in svg.iter():
                    element_id = x.get("id")
                    if element_id is not None and any(y in element_id for y in ["svg_", "img_"]):
                        element_numbers.append(int(element_id.split("_")[-1]))
                element_numbers.sort()
                next_element = element_numbers[-1] + 1
                # Collect the needed layers present in the svg document
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
                # Fill in potentially missing layers
                if layers.get("defs") is None:
                    layers["defs"] = etree.SubElement(svg, "defs")
                # Build or empty flowing layer
                pre_flown = []
                if layers.get("flowing_layer") is None:
                    layers["flowing_layer"] = etree.SubElement(svg, "g", id="flowing_layer")
                else:
                    layers["flowing_layer"] = next((x for x in list(svg) if x.get("id") == "flowing_layer"), None)
                    for child in list(layers.get("flowing_layer")):
                        pre_flown.append(child.get("id"))
                        layers["layer_1"].append(child)
                # Remove titles for data integrity issues
                for child in layers["layer_1"]:
                    if "title" in child.tag:
                        layers["layer_1"].remove(child)
                for child in layers["flowing_layer"]:
                    if "title" in child.tag:
                        layers["flowing_layer"].remove(child)
                # Connect images to drop targets
                tspans_to_edit = []
                edited_drop_target_ids = []
                for rect in svg.iterfind(".//{http://www.w3.org/2000/svg}rect"):
                    rect_gallery = str(rect.get("{http://svg-edit.googlecode.com}gallery_group"))
                    if rect_gallery in tag_ids:
                        rect_number = int(rect.get("{http://svg-edit.googlecode.com}gallery_number"))
                        # Determine teacher status
                        rect_g_tag = rect.getparent()
                        rect_sibling_text = next((x for x in list(rect_g_tag) if "text" in x.tag), None)
                        teacher_flag = False
                        for rect_sub_text in list(rect_sibling_text):
                            if rect_sub_text.text == "Teacher":
                                teacher_flag = True
                        if teacher_flag is True:
                            person = next((x for x in gallery_lists[rect_gallery]["staff"]
                                           if x["tag_num"] == rect_number), None)
                        else:
                            person = next((x for x in gallery_lists[rect_gallery]["students"]
                                           if x["tag_num"] == rect_number), None)
                        rect_parent = rect.getparent()
                        if person is not None:
                            # Create clipPath opjects
                            clippath_tag = etree.SubElement(layers["defs"], "clipPath", id="clipPath_%s" % next_element)
                            use_tag = etree.SubElement(clippath_tag, "use", id="use_%s" % next_element)
                            use_tag.set("{http://www.w3.org/1999/xlink}href", "#border_%s" % next_element)
                            # Add the clip-path to the element grouping
                            rect_parent.set("clip-path", "url(#clipPath_%s)" % next_element)
                            # Create the image tag
                            img = etree.SubElement(rect_parent, "image", id="img_%s" % next_element)
                            img.set("preserveAspectRatio", "none")
                            img.set("{http://www.myyear.com}srcId", str(person["image_id"]))
                            img.set("{http://www.myyear.com}dropTarget", "droppedOnce")
                            img.set("{http://www.myyear.com}dropTargetClipPath", "id_%s" % next_element)
                            img.set("{http://www.w3.org/1999/xlink}href", person["thumbnail_URL"])
                            img.set("opacity", "1")
                            rect_height = float(rect.get("height"))
                            rect_width = float(rect.get("width"))
                            # Assumption has always been that images are a 4:5 h:w ratio.
                            if rect_height >= rect_width:
                                img_width = rect_height / 5 * 4
                                tmp = (img_width - rect_width) / 2
                                img.set("x", str(float(rect.get("x")) - tmp))
                                img.set("y", rect.get("y"))
                                img.set("height", rect.get("height"))
                                img.set("width", str(img_width))
                            else:
                                img_height = rect_width / 4 * 5
                                tmp = (img_height - rect_height) / 4
                                img.set("x", rect.get("x"))
                                img.set("y", str(float(rect.get("y")) - tmp))
                                img.set("height", str(img_height))
                                img.set("width", rect.get("width"))
                            # Edit rectangle tag to show no border
                            rect.set("id", "border_%s" % next_element)
                            rect.set("{http://www.myyear.com}dropTargetImg", "img_%s" % next_element)
                            rect.set("{http://www.myyear.com}dropTarget", "border")
                            next_element += 1
                            # Build list of tspans to edit in the next portion
                            for tag in iter(rect_parent):
                                if "text" in tag.tag:
                                    tag_name = []
                                    for tspan in tag:
                                        if tspan.text == "Teacher":
                                            tag_name.append(tspan.text.lower())
                                        else:
                                            tag_name.append(tspan.text)
                                    if "teacher" in tag_name:
                                        tag_name = tag_name[:-1]
                                    tspans_to_edit.append("_".join(tag_name))
                        else:
                            # Opaque out everything not used in flowing that was tagged
                            rect.set("opacity", "0")
                            for tag in iter(rect_parent):
                                if "text" in tag.tag:
                                    for tspan in tag:
                                        tspan.set("opacity", "0")
                        edited_drop_target_ids.append(rect_parent.get("id"))
                # Move all of the edited drop targes to the flowing layer
                for drop_target in edited_drop_target_ids:
                    dt_to_move = next((x for x in svg.iterfind(".//{http://www.w3.org/2000/svg}g")
                                       if x.get("id") == drop_target), None)
                    layers["flowing_layer"].append(dt_to_move)
                # Edit tspans and add names to the spread
                edited_text_box_ids = []
                first_last_name_check = []
                for tspan in svg.iterfind(".//{http://www.w3.org/2000/svg}tspan"):
                    # Ignore the final tspan in text object
                    if tspan.get("{http://svg-edit.googlecode.com}emptyline") == "true":
                        continue
                    # Ignore centering/right justification tspan
                    if tspan.get("{http://svg-edit.googlecode.com}leadingwhitespacecount") == "1":
                        continue
                    # Initialize necessary tspan values
                    if tspan.text is None:
                        continue
                    tspan_text = tspan.text.split("_")
                    tspan_number = tspan_text[0]
                    temp_tspan_text = tspan.text
                    tspan_parent = tspan.getparent()
                    # Only build a usable tspan_gallery variable if possible
                    if len(tspan_text) > 1:
                        tspan_gallery = next((x for x in group_meta_list if x["name"] == tspan_text[1]), None)
                        if tspan_gallery:
                            tspan_gallery = tspan_gallery["id"]
                    else:
                        tspan_gallery = None
                    # So long as it was a viable split and the tspan gallery appears in the list of galleries to flow
                    if len(tspan_text) > 1 and str(tspan_gallery) in tag_ids:
                        # Determine if this is a teacher/staff tag
                        teacher_flag = False
                        if len(tspan_text) > 2 and tspan_text[-1] == "teacher":
                            teacher_flag = True
                            tspan_text = tspan_text[:-1]
                        # Find the person object for the given tspan, or None if there's no match
                        if teacher_flag is False:
                            person = next((x for x in gallery_lists[str(tspan_gallery)]["students"]
                                           if x["tag_num"] == int(tspan_number)), None)
                        else:
                            person = next((x for x in gallery_lists[str(tspan_gallery)]["staff"]
                                           if x["tag_num"] == int(tspan_number)), None)
                        # If a person object was matched to the current tspan
                        if person is not None:
                            if len(tspan_text) == 3:
                                # Edit top tspan with first name
                                if tspan_text[2] == "first":
                                    tspan.text = person["first_name"]
                                    tspan.set("{http://svg-edit.googlecode.com}tag_text", temp_tspan_text)
                                    opposite = "last"
                                    first_last_name_check.append("_".join([tspan_text[0], tspan_text[1], "first"]))
                                # Edit bottom tspan with last name
                                elif tspan_text[2] == "last":
                                    tspan.text = person["last_name"]
                                    tspan.set("{http://svg-edit.googlecode.com}tag_text", temp_tspan_text)
                                    opposite = "first"
                                    first_last_name_check.append("_".join([tspan_text[0], tspan_text[1], "last"]))
                                # They physically edited their tspans...and broke their tagging.
                                else:
                                    data = {"Error": "'" + "_".join(tspan_text[2:]) +
                                                     "' should not be in your tags.  Please retag."}
                                    resp = jsonify(data)
                                    resp.status_code = 200
                                    return resp
                                # Temp holding to determine if everything has been flown correctly
                                if "_".join([tspan_text[0], tspan_text[1], opposite]) in first_last_name_check:
                                    # TODO
                                    temp_index = tspans_to_edit.index("_".join([tspan_text[0], tspan_text[1]]))
                                    if temp_index > -1:
                                        del tspans_to_edit[temp_index]
                                else:
                                    first_last_name_check.append("_".join([tspan_text[0], tspan_text[1], opposite]))
                            # Names are to be flown in the "John Smith" format.
                            else:
                                tspan.text = person["first_name"] + " " + person["last_name"]
                                tspan.set("{http://svg-edit.googlecode.com}tag_text", temp_tspan_text)
                                if "_".join([tspan_text[0], tspan_text[1]]) in tspans_to_edit:
                                    temp_index = tspans_to_edit.index("_".join([tspan_text[0], tspan_text[1]]))
                                else:
                                    temp_index = -1
                                if temp_index > -1:
                                    del tspans_to_edit[temp_index]
                        # If no person object was matched to the current tspan
                        else:
                            tspan.set("opacity", "0")
                        # Find the outer rectangle for the textbox and white it out
                        top_rect = next((x for x in list(tspan_parent.getparent()) if "rect" in x.tag), None)
                        # Hide the border around the text box
                        if top_rect is not None:
                            top_rect.set("opacity", "0")
                        # Store the id of the text box to move it to the flowing layer later (locked layer)
                        if tspan_parent.get("id") not in edited_text_box_ids:
                            edited_text_box_ids.append(tspan_parent.get("id"))
                # If we failed to edit one of the tspans linked to an edited drop target, fail out
                if len(tspans_to_edit) > 0:
                    data = {"Error": "Your tags were corrupted.  A required text object was missing.  Please retag."}
                    resp = jsonify(data)
                    resp.status_code = 200
                    log_request_error(str(data), request)
                    return resp
                # Move the edited text boxes from layer_1 to the locked flowing layer
                for tspan_g_tag in edited_text_box_ids:
                    tspan_to_move = next((x for x in svg.iterfind(".//{http://www.w3.org/2000/svg}text")
                                         if x.get("id") == tspan_g_tag), None)
                    tspan_parent = tspan_to_move.getparent()
                    layers["flowing_layer"].append(tspan_parent)
                # Move the boxes that had already been flown back to the flowing layer
                for pre_flown_id in pre_flown:
                    move_back = next((x for x in list(layers["layer_1"]) if x.get("id") == pre_flown_id), None)
                    if move_back:
                        layers["flowing_layer"].append(move_back)
                # Build new svg page to keep the layers in the correct order because lxml is fucking up the order.
                new_svg = etree.Element("svg", nsmap={None: 'http://www.w3.org/2000/svg',
                                        'se': 'http://svg-edit.googlecode.com',
                                        'lyb': 'http://www.myyear.com',
                                        'xlink': "http://www.w3.org/1999/xlink"})
                # Re-add titles back in to layers
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
                    data = {"Error": "Cannot flow as one or more sheets is marked 'Complete'."}
                    resp = jsonify(data)
                    resp.status_code = 200
                    log_request_error(str(data), request)
                    return resp
                if sheet.locked is True:
                    if sheet.user_id != user_id:
                        data = {"Error": "One sheet you are attempting to flow is currently in use."}
                        resp = jsonify(data)
                        resp.status_code = 200
                        log_request_error(str(data), request)
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
                    tag.flow = True
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
            resp.status_code = 200
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
