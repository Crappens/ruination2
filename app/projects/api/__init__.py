from sqlalchemy import exists
from sqlalchemy.orm.exc import NoResultFound

from app.models import db, Book


def project_exists(project_id):
    try:
        return db.session.query(exists().where(Book.id == project_id))[0][0]
    except NoResultFound:
        return None
