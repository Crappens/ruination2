import json
from app.base import CrudMixIn
from app.extensions import sql_db as db

class UserModel(db.Model, CrudMixIn):

    id = db.Column(db.String(length=32), primary_key=True)
    name = db.Column(db.String(length=255))
    first_name = db.Column(db.String(length=255))
    last_name = db.Column(db.String(length=255))
    email_address = db.Column(db.String(length=255))

    def __repr__(self):
        return json.dumps({"UserModel": { "id": self.id, "name": self.name }})
