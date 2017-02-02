from flask import request, jsonify
from flask_restful import Resource
import json
from sqlalchemy.exc import DatabaseError

from app.common.utils import log_request_error
from app.models import db, Book, Sheet, Tag


class UnFlowV3(Resource):
    """Implement unflowing on json_model (for BalfourPages)."""

    def error_resp(self, err_msg):
        resp = jsonify({'Error': err_msg})
        resp.status_code = 200
        log_request_error(err_msg, request)
        return resp

    def post(self, project_number):
        if request.json is None:
            return self.error_resp('No JSON payload detected.')

        if not all(x in request.json for x in ['userID', 'groups']):
            return self.error_resp(
                'Missing Fields: %s' % ', '.join(
                    [x for x in ['userID', 'groups'] if x not in request.json]
                )
            )

        user_id = request.json['userID']
        groups = request.json['groups']
        # group_meta_list = request.json["extra"]

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

        # list of tag ids
        tag_ids = [x.galleryID for x in tags]

        # find the sheets you need to edit
        sheets_to_edit = {}
        for sheet in sheets:
            if not sheet.json_model:
                # no json model --> nothing to do
                continue
            json_model = json.loads(sheet.json_model)

            # check that sheet contains flowing layer..
            flowing_layer = [layer for layer in json_model['svgLayers'] if layer['id'] == 'flowing_layer']
            if not flowing_layer:
                # if not skip it
                continue

            flowing_layer = flowing_layer[0]

            # find/create layer1 --> will be used as a target for unflown objects
            tmp_layer = [layer for layer in json_model['svgLayers'] if layer['id'] == 'Layer1']
            if not tmp_layer:
                # create new layer
                tmp_layer = {
                    'id': 'Layer1',
                    'name': 'Layer 1',
                    'visible': True,
                    'svgObjects': [],
                }

                json_model['svgLayers'].append(tmp_layer)
                json_model['layersFoldersTree']['folders'].append({
                    'id': 'Layer1',
                    'name': 'Layer1',
                    'folderType': 'layer',
                })
            else:
                tmp_layer = tmp_layer[0]

            # check whether sheet was edited
            edited = False

            # remove these objects from flowing layer
            remove_objs = {}

            # text object which have to be updated
            text_captions = []

            # remove flowned images
            for i, obj_id in enumerate(flowing_layer['svgObjects']):
                if obj_id in remove_objs:
                    # obj alreade deleted -> skip
                    continue

                obj = json_model['svgObjects'][obj_id]
                if obj['type'] != 'rect' or obj.get('tagForFlowGroupID') not in tag_ids:
                    continue

                # found droptarget --> unflow

                try:
                    # img should be next object
                    img_obj_id = flowing_layer['svgObjects'][i + 1]
                except IndexError:
                    img_obj_id = None

                # check that objects are properly linked
                if img_obj_id and img_obj_id in json_model['svgObjectsLinks'][obj_id] \
                  and 'photoboxLink' in json_model['svgObjectsLinks'][obj_id][img_obj_id]:
                    # remove image
                    del json_model['svgObjects'][img_obj_id]
                    # remove images relations
                    del json_model['svgObjectsLinks'][img_obj_id]
                    # remove image relation from droptarget
                    del json_model['svgObjectsLinks'][obj_id][img_obj_id]

                    # obj has to be remove after the cycle
                    remove_objs[img_obj_id] = img_obj_id
                else:
                    # unhide object
                    obj.pop('hiddenObj', None)

                # unhide text label for the object
                tag_text_id = [
                    key for key, value in json_model['svgObjectsLinks'][obj_id].iteritems()
                    if 'textLink' in value
                ][0]
                json_model['svgObjects'][tag_text_id].pop('hiddenObj', None)

                # save caption id for later use
                caption_text_id = [
                    key for key, value in json_model['svgObjectsLinks'][obj_id].iteritems()
                    if 'tagForFlowLink' in value
                ][0]

                # deal with them after img handling
                text_captions.append(caption_text_id)

                # move objects to "new layer"
                remove_objs[obj_id] = obj_id
                remove_objs[tag_text_id] = tag_text_id
                tmp_layer['svgObjects'].extend([
                    obj_id, tag_text_id
                ])

                edited = True

            text_captions = list(set(text_captions))
            for id_ in text_captions:
                obj = json_model['svgObjects'][id_]

                # get id of captions rectangle
                rect_id = [
                    key for key, value in json_model['svgObjectsLinks'][id_].iteritems()
                    if 'textLink' in value
                ][0]

                # move caption into "new layer"
                remove_objs[id_] = id_
                remove_objs[rect_id] = rect_id
                tmp_layer['svgObjects'].extend([rect_id, id_])

                if 'hiddenObj' in obj:
                    del obj['hiddenObj']
                    del json_model['svgObjects'][rect_id]['hiddenObj']
                    continue

                # iterate throught text node
                for item in obj['text']:
                    # update placeholders for first/last names
                    flow_type = item[0][1].get('flowType')
                    if flow_type == 'fn':
                        item[0][0] = 'fn'
                    elif flow_type == 'ln':
                        item[0][0] = 'ln'

                    # remove hiddenObj mark
                    item[0][1].pop('hiddenObj', None)

            for id_ in remove_objs:
                flowing_layer['svgObjects'].remove(id_)

            if edited:
                sheets_to_edit[sheet.id_] = {
                    # for save -> so we don't need to reload the sheet
                    'self': sheet,
                    # do string to json conversion only once
                    'json_model': json_model,
                }

        # make sure none of the sheets is marked 'complete'
        current_sheet = None
        for sheet_dict in sheets_to_edit.itervalues():
            if sheet_dict['self'].completed:
                return self.error_resp('Cannot unflow as one or more sheets is marked "Complete".')

            if sheet_dict['self'].locked:
                if sheet_dict['self'].user_id != user_id:
                    return self.error_resp('One sheet you are attempting to unflow is currently in use.')
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

        # update tags as "unflown"
        try:
            for tag in tags:
                tag.flow = 0
            db.session.commit()
        except DatabaseError, e:
            db.session.rollback()
            return self.error_resp('Unable to mark flow tag as unflown ("%s")' % e)

        # return success message if nothing above failed
        data = {'Message': sheets_to_edit.keys()}
        resp = jsonify(data)
        resp.status_code = 200
        return resp
