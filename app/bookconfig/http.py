from flask.ext.restful import Resource, Api
from .schema.nosql import BookConfig, BookConfigSchema
from flask import jsonify, Blueprint
from app.extensions import app_cache


class BookConfigCollection(Resource):

    mapper = BookConfig
    schema = BookConfigSchema(many=True)

    @app_cache.cached(timeout=300)
    def get(self):
        return jsonify({'bookSizes': self.schema.dump(self.mapper.objects())[0]})


blueprint = Blueprint(name='book_config', import_name=__name__)
api = Api(blueprint)

api.add_resource(
    BookConfigCollection, "/booksizes", "/booksize/list.json"
)
