from app.models import db, Tag

import uuid

from flask import request, jsonify
from flask.ext.restful import Resource
from werkzeug.exceptions import BadRequest


class Tagging(Resource):

    def __init__(self):
        super(Tagging, self).__init__()

    def get(self, **kwargs):
        try:
            galleryName = kwargs.get("galleryName")
            galleryType = kwargs.get("galleryType")
            project_id = kwargs.get("project_id")
            tag = db.session.query(Tag).filter_by(galleryID=galleryType + "/" + galleryName, book_id=project_id).first()
            if tag is None:
                tag = self.create_new_tag(galleryName, galleryType, project_id)
                resp = jsonify({"lastUsed": tag.lastUsed,
                                "tagCount": tag.tagCount,
                                "galleryID": tag.galleryID,
                                "flow": tag.flow})
                resp.status_code = 200
            else:
                if tag.tagCount < 0:
                    tag.tagCount = 0
                    db.session.commit()

                if tag.book_id in [None, '']:
                    tag.book_id = project_id
                    db.session.commit()

                resp = jsonify({"lastUsed": tag.lastUsed,
                                "tagCount": tag.tagCount,
                                "galleryID": tag.galleryID,
                                "flow": tag.flow})
                resp.status_code = 200

        except Exception as Ex:
            resp = jsonify({"Error": str(Ex)})
            resp.status_code = 500

        return resp

    def put(self, **kwargs):
        try:
            galleryName = kwargs.get("galleryName")
            galleryType = kwargs.get("galleryType")
            project_id = kwargs.get("project_id")
            tag = db.session.query(Tag).filter_by(galleryID=galleryType + "/" + galleryName, book_id=project_id).first()
            if tag:
                blob = request.json
                improper_keys = [x for x in blob.keys() if x not in ['lastUsed', 'tagCount']]
                tagCount = blob.get("tagCount")
                lastUsed = blob.get("lastUsed")
                if tag.book_id in [None, '']:
                    tag.book_id = project_id
                if lastUsed is None and tagCount is None:
                    resp = jsonify({"message": "Did not pass 'lastUsed' or 'tagCount' to update."})
                    resp.status_code = 400
                elif len(improper_keys) > 0:
                    resp = jsonify({"message": "Extra keys were passed on tag update: %s" % ",".join(improper_keys)})
                    resp.status_code = 400
                else:
                    if lastUsed is not None:
                        tag.lastUsed = lastUsed
                    if tagCount is not None:
                        tag.tagCount = tagCount

                    db.session.commit()

                    resp = jsonify({"message": "Tag updated."})
                    resp.status_code = 200
            else:
                resp = jsonify({"message": "Tag with galleryID %s does not exist for book %s." %
                                           (galleryType + "/" + galleryName, project_id)})
                resp.status_code = 404

        except BadRequest:
            resp = jsonify({"message": "No json detected."})
            resp.status_code = 400
        except ValueError:
            resp = jsonify({"message": "TagCount and lastUsed need to be integers."})
            resp.status_code = 400
        except Exception as Ex:
            resp = jsonify({"message": str(Ex)})
            resp.status_code = 500

        return resp

    def create_new_tag(self, galleryName, galleryType, project_id):
        tag = Tag()
        tag.id = uuid.uuid4().hex
        tag.flow = False
        tag.lastUsed = 0
        tag.tagCount = 0
        tag.galleryID = galleryType + "/" + galleryName
        tag.book_id = project_id

        db.session.add(tag)
        db.session.commit()

        return tag
