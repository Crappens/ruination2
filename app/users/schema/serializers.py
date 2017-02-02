import marshmallow
from marshmallow import fields as mf

from app.base import SchemaCrudMixin
from app.extensions import enfold_client


class UserSchema(marshmallow.Schema, SchemaCrudMixin):

    id = mf.UUID()
    name = mf.String()
    firstName = mf.String()
    lastName = mf.String()
    middleName = mf.String()
    emailAddress = mf.Email()


class UserCache(object):

    def authorize(self):
        pass

    def authenticate(self):
        pass
