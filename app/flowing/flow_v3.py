from collections import defaultdict
from flask import current_app, request, jsonify
from flask_restful import Resource
import json
from operator import itemgetter
import requests
from sqlalchemy.exc import DatabaseError

from app.common.utils import log_request_error
from app.models import db, Book, Sheet, Tag


class FlowV3(Resource):
    """Implement flowing on json_model (for BalfourPages)."""

    def get_obj_id(self, obj_type, existing_objs):
        num = len(existing_objs)
        new_id = '%s%s' % (obj_type, num)

        while new_id in existing_objs:
            # try to find next ID without collision
            num += 1
            new_id = '%s%s' % (new_id, num)

        return new_id

    def error_resp(self, err_msg):
        resp = jsonify({'Error': err_msg})
        resp.status_code = 200
        log_request_error(err_msg, request)
        return resp

    def post(self, project_number):
        if request.json is None:
            return self.error_resp('No JSON payload detected.')

        if not all(x in request.json for x in ['token', 'userID', 'groups']):
            return self.error_resp(
                'Missing Fields: %s' % ', '.join(
                    [x for x in ['token', 'userID', 'groups'] if x not in request.json]
                )
            )

        token = request.json['token']
        user_id = request.json['userID']
        groups = request.json['groups']
        # TODO: what is this for?
        # group_meta_list = request.json['extra']

        # load book object
        book = db.session.query(Book).filter_by(number=project_number).first()
        if book is None:
            return self.error_resp('Book %s does not exist.' % project_number)

        # get list of sheets
        sheets = [
            sheet
            for sheet in db.session.query(Sheet).filter_by(book_id=book.id_).all()
            if not sheet.hidden
        ]

        # list of tag objects to be flowed.
        tags = []
        non_existent = []
        for group in groups:
            temp_tag = db.session.query(Tag).filter_by(galleryID=group, book_id=book.id_).first()
            if temp_tag is None:
                non_existent.append(str(group))
            else:
                tags.append(temp_tag)

        if len(non_existent):
            return self.error_resp('Tag(s) [%s] does(do) not exist.' % ', '.join(non_existent))

        # Llst of tag ids
        tag_ids = [x.galleryID for x in tags]

        # information about sheets, their json_model and droptargets on the sheets
        sheets_to_edit = {}
        # all droptargets to be flowned (from all sheets)
        flow_objs = {}

        # find the sheets you need to edit and preserve the group numbering if found
        for sheet in sheets:
            if not sheet.json_model:
                # no json model --> nothing to do
                continue
            json_model = json.loads(sheet.json_model)

            # get flowing layer
            flowing_layer = [layer for layer in json_model['svgLayers'] if layer['id'] == 'flowing_layer']
            if flowing_layer:
                flowing_layer = flowing_layer[0]

            # need to iterate through all rectangles
            for obj in json_model['svgObjects'].itervalues():
                if obj['type'] != 'rect' or obj.get('tagForFlowGroupID') not in tag_ids:
                    continue

                if flowing_layer and obj['id'] in flowing_layer['svgObjects']:
                    # ignore already flowed objects
                    continue

                if sheet.id_ not in sheets_to_edit:
                    sheets_to_edit[sheet.id_] = {
                        # for save -> so we don't need to reload the sheet
                        'self': sheet,
                        # do string to json conversion only once
                        'json_model': json_model,
                        # rect' to be flowned
                        'flow_objs': [],
                        # flowing layer
                        'flowing_layer': flowing_layer,
                    }

                if obj['tagForFlowGroupID'] not in flow_objs:
                    flow_objs[obj['tagForFlowGroupID']] = {'students': [], 'staff': []}

                # students | staff
                flow_group_type = 'staff' if obj.get('tagForFlowTeacher') else 'students'

                flow_objs[obj['tagForFlowGroupID']][flow_group_type].append(
                    (obj['tagForFlowIndex'], obj['id'])
                )
                sheets_to_edit[sheet.id_]['flow_objs'].append(obj)

        if not flow_objs:
            return self.error_resp('No droptargets found for flowing')

        # sort flow objects according to their flow tag
        for key in flow_objs:
            flow_objs[key]['staff'] = sorted(flow_objs[key]['staff'], key=itemgetter(0))
            flow_objs[key]['students'] = sorted(flow_objs[key]['students'], key=itemgetter(0))

        # call student manager and get the images for each gallery needing to be flown
        headers = {
            'project-id': book.id_,
            'user-id': user_id,
            'x-subject-token': token,
        }
        base_sm_url = '%s/students/flow/%s' % (current_app.config['STUDENT_MANAGER'], '%s')

        person_mapping = defaultdict(dict)
        for tag_id in tag_ids:
            new_resp = requests.get(base_sm_url % tag_id, headers=headers, verify=False)
            if new_resp.status_code != 200:
                return self.error_resp(new_resp.json()['messages'])

            staff_list = []
            student_list = []

            for item in new_resp.json()['students']:
                if item['staff'] == 1:
                    staff_list.append(item)
                else:
                    student_list.append(item)

            # alphabetize the people in the lists in the format last_name, first_name
            staff_list = sorted(staff_list, key=lambda p: (p['last_name'], p['first_name']))
            student_list = sorted(student_list, key=lambda p: (p['last_name'], p['first_name']))

            # if we're flowing the staff only, then make them the main priority
            if not len(student_list):
                student_list = staff_list

            # make sure there are enough tagged drop targets before trying to build our map
            if len(student_list) > len(flow_objs[tag_id]['students']):
                return self.error_resp('Not enough tagged boxes for gallery %s' % tag_id)

            # assign students/staff their tspan numbers
            for num, person in enumerate(student_list):
                person_id = '%s/%s' % (flow_objs[tag_id]['students'][num][0], flow_objs[tag_id]['students'][num][1])
                person_mapping[tag_id][person_id] = person

            # let flowing teachers be all or nothing per gallery, they will be alphabetical
            if len(flow_objs[tag_id]['staff']) > 0:
                if len(staff_list) > len(flow_objs[tag_id]['staff']):
                    return self.error_resp('Not enough tagged boxes for teachers of gallery %s' % tag_id)

                for num, person in enumerate(staff_list):
                    person_id = '%s/%s' % (flow_objs[tag_id]['students'][num][0], flow_objs[tag_id]['students'][num][1])
                    person_mapping[tag_id][person_id] = person

        # begin flowing
        for sheet_dict in sheets_to_edit.itervalues():
            # create/update flowing layer
            if not sheet_dict['flowing_layer']:
                sheet_dict['flowing_layer'] = {
                    'id': 'flowing_layer',
                    'name': 'Flowing Layer',
                    'visible': True,
                    'system': True,
                    'lock': True,
                    'svgObjects': [],
                }

                sheet_dict['json_model']['svgLayers'].append(sheet_dict['flowing_layer'])
                sheet_dict['json_model']['layersFoldersTree']['folders'].append({
                    'id': 'flowing_layer',
                    'name': 'Flowing Layer',
                    'folderType': 'layer',
                })
            else:
                # set flowing layer to system + locked
                # just in case
                sheet_dict['flowing_layer']['system'] = True
                sheet_dict['flowing_layer']['lock'] = True

            # flowned objects -> to be moved to flowing layer
            flowned_objects = []
            # text boxes to be updated
            text_boxes = {}
            # unused text boxes
            unused_text_boxes = []

            for obj in sheet_dict['flow_objs']:
                # find right person for the tag
                person_id = '%s/%s' % (obj['tagForFlowIndex'], obj['id'])
                person = person_mapping[obj['tagForFlowGroupID']].get(person_id)

                if person is None:
                    # FIXME: hiddenObj not implemented on FE
                    obj['hiddenObj'] = True

                    flowned_objects.append(obj['id'])
                    for key, value in sheet_dict['json_model']['svgObjectsLinks'][obj['id']].iteritems():
                        if 'textLink' in value or 'tagForFlowLink' in value:
                            sheet_dict['json_model']['svgObjects'][key]['hiddenObj'] = True
                            flowned_objects.append(key)

                        if 'tagForFlowLink' in value:
                            unused_text_boxes.append(key)

                            text_box_rect = [
                                key for key, value in sheet_dict['json_model']['svgObjectsLinks'][key].iteritems()
                                if 'textLink' in value
                            ][0]

                            flowned_objects.append(text_box_rect)
                            sheet_dict['json_model']['svgObjects'][text_box_rect]['hiddenObj'] = True
                    continue

                # apply person to the drop target
                img_obj = {
                    'id': self.get_obj_id('photo', sheet_dict['json_model']['svgObjects']),
                    'type': 'photo',
                    'position': obj['position'].copy(),
                    'src': person['thumbnail_URL'],
                    'clipPath': '%s-clip-path' % obj['id'],
                }

                rect_height = img_obj['position']['height']
                rect_width = img_obj['position']['width']

                # Assumption has always been that images are a 4:5 h:w ratio.
                if rect_height >= rect_width:
                    img_width = rect_height / 5 * 4
                    width_mod = (img_width - rect_width) / 2
                    img_obj['position']['x'] = img_obj['position']['x'] - width_mod
                    img_obj['position']['width'] = img_width
                else:
                    img_height = rect_width / 4 * 5
                    height_mod = (img_height - rect_height) / 4
                    img_obj['position']['y'] = img_obj['position']['y'] - height_mod
                    img_obj['position']['height'] = img_height

                sheet_dict['json_model']['svgObjects'][img_obj['id']] = img_obj

                # drop target
                sheet_dict['flowing_layer']['svgObjects'].append(obj['id'])
                # image object
                sheet_dict['flowing_layer']['svgObjects'].append(img_obj['id'])

                # create object relations
                if obj['id'] not in sheet_dict['json_model']['svgObjectsLinks']:
                    sheet_dict['json_model']['svgObjectsLinks'][obj['id']] = {}
                sheet_dict['json_model']['svgObjectsLinks'][obj['id']][img_obj['id']] = {
                    'photoboxLink': {'linkData': {'photobox': True}}
                }
                sheet_dict['json_model']['svgObjectsLinks'][img_obj['id']] = {
                    obj['id']: {'photoboxLink': {'linkData': {'photobox': True}}}
                }

                # object already added into flowing layer
                # we need to remove object from it's previous, if it's not flowing layer
                flowned_objects.append(obj['id'])

                # move related object into the flowing layer as well
                for key, value in sheet_dict['json_model']['svgObjectsLinks'][obj['id']].iteritems():
                    if 'textLink' in value:
                        flowned_objects.append(key)
                        # mark text box as hidden
                        sheet_dict['json_model']['svgObjects'][key]['hiddenObj'] = True
                    elif 'photoboxLink' in value:
                        flowned_objects.append(key)
                    elif 'tagForFlowLink' in value:
                        if key not in text_boxes:
                            text_boxes[key] = {
                                'flow_tag': obj['tagForFlowGroupID'],
                                'persons': {}
                            }

                        person_key = '%s/%s' % (obj['tagForFlowIndex'], obj['tagForFlowGroupID'])
                        text_boxes[key]['persons'][person_key] = person

            for text_box_id, value in text_boxes.iteritems():
                obj = sheet_dict['json_model']['svgObjects'][text_box_id]

                fn_index = None
                ln_index = None

                for i, item in enumerate(obj['text']):
                    if item[0][0] == 'fn':
                        fn_index = i
                    elif item[0][0] == 'ln':
                        ln_index = i
                    elif item[0][0] == value['flow_tag']:
                        if fn_index is None and ln_index is None:
                            return self.error_resp('Missing tags for first name nad last name, please retag.')

                        # we need to found get flow number and find person for the pair
                        # let's assume that number is two nodes before this one
                        tag_index = obj['text'][i - 2][0][0]

                        person_key = '%s/%s' % (tag_index, value['flow_tag'])
                        person = value['persons'].pop(person_key, None)
                        if person is None:
                            # person not found --> mark "tspans" as hidden
                            j = min(i, fn_index) if fn_index is not None else i
                            j = min(j, ln_index) if ln_index is not None else j
                        else:
                            if fn_index is not None:
                                obj['text'][fn_index][0][0] = person['first_name']
                                obj['text'][fn_index][0][1]['flowType'] = 'fn'
                            if ln_index is not None:
                                obj['text'][ln_index][0][0] = person['last_name']
                                obj['text'][ln_index][0][1]['flowType'] = 'ln'

                            j = max(fn_index, ln_index) + 1

                        # add hiddentObj attribute to text nodes
                        # FIXME: hiddenObj not implemented on FE
                        while j <= i:
                            obj['text'][j][0][1]['hiddenObj'] = True
                            j += 1

                        fn_index = None
                        ln_index = None

                # check that all requested tag were used
                if len(value['persons']) > 0:
                    # some tags not found in the text box -> tags probably corrupted
                    return self.error_resp(
                        'Your tags were corrupted. A required text object was missing. Please retag.'
                    )

                # move text box to flowing layer
                flowned_objects.append(obj['id'])
                # handle text's rect object
                text_box_rect = [
                    key for key, value in sheet_dict['json_model']['svgObjectsLinks'][text_box_id].iteritems()
                    if 'textLink' in value
                ][0]

                if text_box_id in unused_text_boxes:
                    # remove it --> it's used
                    unused_text_boxes.remove(text_box_id)
                    del obj['hiddenObj']
                    del sheet_dict['json_model']['svgObjects'][text_box_rect]['hiddenObj']
                else:
                    flowned_objects.append(text_box_rect)

            # de dupe flowned_objects
            flowned_objects = list(set(flowned_objects))

            for obj_id in flowned_objects:
                # remove object from current layer
                for layer in sheet_dict['json_model']['svgLayers']:
                    if layer['id'] == 'flowing_layer' or obj_id not in layer['svgObjects']:
                        # do nothing with objects in flowing layer
                        continue

                    # remove obj from original layer
                    layer['svgObjects'].remove(obj_id)
                    if obj_id not in sheet_dict['flowing_layer']['svgObjects']:
                        # move object to flowing layer
                        sheet_dict['flowing_layer']['svgObjects'].append(obj_id)
                    break

        # make sure none of the sheets is marked 'complete'
        current_sheet = None
        for sheet_dict in sheets_to_edit.itervalues():
            if sheet_dict['self'].completed:
                return self.error_resp('Cannot flow as one or more sheets is marked "Complete".')

            if sheet_dict['self'].locked:
                if sheet_dict['self'].user_id != user_id:
                    return self.error_resp('One sheet you are attempting to flow is currently in use.')
                current_sheet = sheet_dict['self'].id_

        # lock sheets
        # skip updating the version if it's the current spread as locking thinks another user updated the spread
        try:
            for sheet_dict in sheets_to_edit.itervalues():
                sheet_dict['self'].user_id = user_id
                sheet_dict['self'].active = 1
                if sheet_dict['self'].id_ != current_sheet:
                    sheet_dict['self'].version += 1
                sheet_dict['self'].locked = 1
            db.session.commit()
        except DatabaseError, e:
            db.session.rollback()
            return self.error_resp('Unable to lock sheets ("%s")' % e)

        # save the sheets back to the DB
        try:
            for sheet_dict in sheets_to_edit.itervalues():
                # FIXME: how to update sheets SVG (??)
                sheet_dict['self'].json_model = json.dumps(sheet_dict['json_model'])
                sheet_dict['self'].last_editor_uuid = user_id
                if sheet_dict['self'].id_ != current_sheet:
                    sheet_dict['self'].version += 1
            db.session.commit()
        except DatabaseError, e:
            db.session.rollback()
            return self.error_resp('Unable to update json models ("%s")' % e)

        # unlock all of the flown sheets
        try:
            for sheet_dict in sheets_to_edit.itervalues():
                sheet_dict['self'].user_id = None
                sheet_dict['self'].active = 0
                if sheet_dict['self'].id_ != current_sheet:
                    sheet_dict['self'].version += 1
                sheet_dict['self'].locked = 0
            db.session.commit()
        except DatabaseError, e:
            db.session.rollback()
            return self.error_resp('Unable to unlock sheets ("%s")' % e)

        # update tags as "flown"
        try:
            for tag in tags:
                tag.flow = 1
            db.session.commit()
        except DatabaseError, e:
            db.session.rollback()
            return self.error_resp('Unable to mark flow tag as flown ("%s")' % e)

        # return success message if nothing above failed
        data = {'Message': sheets_to_edit.keys()}
        resp = jsonify(data)
        resp.status_code = 200
        return resp
