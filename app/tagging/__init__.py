from flask import Blueprint
from flask.ext.restful import Api
from tagging import Tagging


blueprint = Blueprint(name='tags', import_name=__name__)
api = Api(blueprint)
api.add_resource(Tagging, "/tags/<string:galleryType>/<string:galleryName>/<string:project_id>")

__all__ = [blueprint]