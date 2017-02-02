from flask import Blueprint, current_app, jsonify
from flask.ext.restful import Resource, Api
from flask.ext.swagger import swagger


class Docs(Resource):
    """Swagger Docs."""

    def get(self):

        return jsonify(swagger(current_app))


blueprint = Blueprint(name="docs", import_name=__name__)
api = Api(app=blueprint)

api.add_resource(Docs, "/docs")