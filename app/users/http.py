from flask import jsonify, Blueprint
from flask.ext.restful import Resource, Api
from flask import current_app, request
import requests

blueprint = Blueprint('user_blueprint', import_name=__name__)
api = Api(app=blueprint)


class UserRoleResource(Resource):

    def get(self, user_id):

        url = "%s/users/%s/all" % (current_app.config['ENFOLD_URL'], user_id)
        result = requests.get(url, headers={"X-Auth-Token": "ADMIN"}).json()
        projects = result['projects']

        rols = ""
        for project in projects:
            if project['number'] == request.headers.get('number'):
                for role in project['roles']:
                    rols += '{0:s}:{1:s},'.format(role['id'], role['name'])

        return jsonify(string=rols)

api.add_resource(UserRoleResource, '/users/<string:user_id>/roles')
