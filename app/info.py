from flask import jsonify, Blueprint, current_app
from flask.ext.restful import Resource, Api
from flask_restful_swagger import swagger



class Info(Resource):

    def get(self):
        data = {"Info": "Ruination imminent.  You have been warned."}
        resp = jsonify(data)
        resp.status_code = 200
        return resp

blueprint = Blueprint('info', __name__)
api = swagger.docs(Api(app=blueprint),
                   api_spec_url="/docs")
api.add_resource(Info, '/Info')

__all__ = [blueprint, ]
