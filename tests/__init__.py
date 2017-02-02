from flask import Flask
import json
from mock import MagicMock, patch
from sqlalchemy import Integer, Enum, String, text
import unittest

from tests.sample_data import B4PUB_SAMPLE_DATA_SQL_HEADERS, B4PUB_SAMPLE_DATA_SQL_VALUES


# Disable logging when running unit tests
import logging
logging.disable(logging.CRITICAL)


def mock_integer(*a, **b):
    return Integer


def mock_text(a):
    if a == "'0000-00-00 00:00:00' ON UPDATE CURRENT_TIMESTAMP":
        return text("'0000-00-00 00:00:00'")
    elif a == "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP":
        return text("CURRENT_TIMESTAMP")
    return text(a)


# BIGINT is mocked to enable autoincrement in sqllite
with patch.multiple('sqlalchemy.dialects.mysql',
    TINYINT=mock_integer, MEDIUMINT=mock_integer, ENUM=Enum, LONGTEXT=String, BIGINT=mock_integer):
    with patch.multiple('sqlalchemy', text=mock_text, Index=MagicMock()):
        import b4.schema.models.b4pub_models as b4
        from app.models import db
        from app.mysocket import MyYearCommander
        from app.projects import blueprint as projects_blueprint


REQUIRED_TABLES = [
    'project', 'book', 'sheet', 'project_meta', 'project_status', 'user'
]


class TestCase(unittest.TestCase):

    def insert_data(self, db):
        for i, header in enumerate(B4PUB_SAMPLE_DATA_SQL_HEADERS):
            for stmt in B4PUB_SAMPLE_DATA_SQL_VALUES[i]:
                db.engine.execute(header % stmt)

    def setUp(self):
        # prepare test flask app
        app = Flask(__name__)

        app.config['DEBUG'] = True
        app.config['TESTING'] = True

        # use in memory sqlite for faster test run
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        app.config['ENFOLD_URL'] = 'http://127.0.0.1:8000'
        app.config['ENFOLD_ADMIN_TOKEN'] = 'TESTER'

        app.config['FIRST_SHEET_THUMB'] = '/test/url/thumb'
        app.config['NORMAL_SHEET_THUMB'] = '/test/url/thumb'
        app.config['LAST_SHEET_THUMB'] = '/test/url/thumb'

        # for debug only
        # app.config['SQLALCHEMY_ECHO'] = True

        # init DB
        db.init_app(app)

        self.app = app
        self.ctx = self.app.test_request_context()
        self.ctx.push()

        # create required DB tables
        for table in REQUIRED_TABLES:
            b4.metadata.tables[table].create(bind=db.get_engine(self.app))

        # insert test data
        self.insert_data(db)

        # register url blueprints
        app.register_blueprint(projects_blueprint)

        # prepare test client
        self.client = app.test_client()

        # prepare websockets API
        self.register_websocket(app)

    def register_websocket(self, app):
        ws = MagicMock()
        self.ws_view = MyYearCommander(app, ws)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

        self.ctx.pop()

    def check_404(self, resp, msg, uuid):
        self.assertEqual(resp.status_code, 404, 'Unexpected status code (!= 404)')

        resp_json = json.loads(resp.data)

        self.assertIn('error', resp_json)
        self.assertIn('description', resp_json['error'])
        self.assertTrue(msg in resp_json['error']['description'])
        self.assertTrue(uuid in resp_json['error']['description'])
