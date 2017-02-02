from flask.ext.restful import Resource, Api
from .schema.nosql import Theme, ThemeSchema
from flask import jsonify, Blueprint
from app.extensions import app_cache

class ThemeCollection(Resource):

    mapper = Theme
    schema = ThemeSchema(many=True)

    def get(self):
        return jsonify({"themesList": self.schema.dump(self.mapper.objects())[0]})

class ThemeResource(Resource):

    mapper = Theme
    schema = ThemeSchema(many=False)

    @app_cache.cached(timeout=300)
    def get(self, themeId):
        instance = self.mapper.objects.get_or_404(id=themeId)
        return jsonify(self.schema.dump(instance)[0])


blueprint = Blueprint(name='themes', import_name=__name__)
api = Api(blueprint)
api.add_resource(ThemeCollection, "/themes", "/themes/listall.json")
api.add_resource(ThemeResource, "/themes/<string:themeId>", "/themes/view/<string:themeId>.json")
