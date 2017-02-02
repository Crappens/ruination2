from flask import Blueprint
from flask.ext.restful import Api
from flow_v2 import Flow
from flow_v3 import FlowV3
from unflow_v2 import UnFlow
from unflow_v3 import UnFlowV3
from validate import Validation
from index import Index, AvailableGroups

blueprint = Blueprint('flowing', import_name=__name__)
api = Api(blueprint)
api.add_resource(Flow, '/flow_v2/<string:projectID>')
api.add_resource(FlowV3, '/flow_v3/<string:project_number>')
api.add_resource(UnFlow, '/unflow_v2/<string:projectID>')
api.add_resource(UnFlowV3, '/unflow_v3/<string:project_number>')
api.add_resource(Validation, '/validate')
api.add_resource(Index, '/index')
api.add_resource(AvailableGroups, '/groups/<string:project_id>')

__all__ = [blueprint]
