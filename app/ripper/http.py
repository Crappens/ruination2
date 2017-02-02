import json

from flask import request, Blueprint, send_file, jsonify, current_app
from flask.ext.restful import Resource, Api

from app.ripper import ripper


class RipBook(Resource):

    def post(self):
        req_data = json.loads(request.data)

        ripper.rip_book(project_id=req_data.get("project_id"), project_name=req_data.get("project_name"),
                        user_id=req_data.get("user_id"), token=req_data.get("token"),
                        thumbnail=req_data.get("thumbnail"), split_spread=req_data.get("split_spread"))

        data = {"Status": "Complete"}
        resp = jsonify(data)
        resp.status_code = 200
        return resp


class RipSheet(Resource):

    def post(self):
        req_data = json.loads(request.data)

        pdf = ripper.rip_book(project_id=req_data.get("project_id"), project_name=req_data.get("project_name"),
                        user_id=req_data.get("user_id"), token=req_data.get("token"), sheet_id=req_data.get("sheet_id"),
                        thumbnail=req_data.get("thumbnail"), split_spread=req_data.get("split_spread"),
                        image_type=req_data.get("image_type"))

        if req_data.get("thumbnail") is True:
            data = {"thumbnails": pdf}
            resp = jsonify(data)
            resp.status_code = 200
            return resp
        else:
            data = {"url": pdf}
            resp = jsonify(data)
            resp.status_code = 200
            return resp


blueprint = Blueprint(name="ripper", import_name=__name__)
api = Api(app=blueprint)

api.add_resource(RipBook, '/ripBook')
api.add_resource(RipSheet, '/ripSheet')
