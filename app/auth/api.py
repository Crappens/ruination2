import uuid
from flask import current_app

from sqlalchemy.orm.exc import NoResultFound
from app.common.utils import log_request_error
from app.models import db, User


# @app_cache.memoize(timeout=300)
def get_login_url(project, user_id, token, user_name):
    """

    :param project:
    :param user_id:
    :param token:
    :param user_name:
    :return:
    """

    with current_app.app_context():
        app_host = current_app.config.get('APP_HOST')
        url = "{0:s}/index.html#/loginFromStudio/{1:s}/{2:s}/{3:s}/{4:s}/{5:s}/{6:s}".format(
            app_host, project.id, project.number, user_id, token, project.id, user_name)

    return url


def create_user(name):
    user = User()
    user.id = uuid.uuid4().hex
    user.name = name

    db.session.add(user)
    db.session.commit()

    return user


def get_user(user_id):
    try:
        return db.session.query(User).filter_by(id=user_id).first()
    except NoResultFound as ex:
        log_request_error(str(ex))
        return None
    except Exception as ex:
        raise ex
        log_request_error(str(ex))
        raise ex
