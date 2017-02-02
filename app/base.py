from functools import wraps
import logging

from flask import current_app, request, jsonify
from marshmallow import fields as mf
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.exc import NoResultFound, UnmappedInstanceError, MultipleResultsFound
from flask.ext.restful import Resource

from app.extensions import sql_db as db
from app.common.exceptions import (
    InvalidObjectType,
    DeleteInvalidObjectException,
    InvalidObjectException
)

from app.extensions import enfold_client
from app.common.utils import (
    json_response_factory,
    server_exception,
    not_found_response,
    bad_request,
    method_not_allowed
)

import inflect
textman = inflect.engine()

logger = logging.getLogger(__name__)

class HistoryBaseModel(object):

    insert_date = db.Column(db.DateTime)
    # TODO: This should be a uuid/fk
    insert_by_user_id = db.Column(db.String(32))
    update_date = db.Column(db.DateTime)
    update_user_id = db.Column(db.String(32))
    deleted_date = db.Column(db.DateTime)
    version = db.Column(db.Integer)
    # TODO: this should be a uuid/fk
    version_source = db.Column(db.String(32))


class CrudMixIn(object):
    created = db.Column(db.DateTime)
    updated = db.Column(db.DateTime)
    __excluded__ = []

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


class DataServiceBase(object):

    model = None
    db_engine = None
    serializer = None

    def __init__(self):
        self.name = self.model.__table__.name.lower()
        self.plural_name = textman.plural(self.name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __repr__(self):
        return '{0:s}(model:{1:s}, db_engine:{2:s}, serializer:{3:s})'.format(
            self.__class__.__name__, self.model, self.db_engine, self.serializer
        )

    def preprocess_parameters(self, kwargs):
        """Returns a dict of parameters for needed to create a new instance or update
        an instance of self.model.

        This method should be overrode by subclasses.

        :param kwargs: A dictionary of model parameters.
        :return: dict
        """

        return kwargs

    def get_collection(self):
        """Returns all objects for the model

        :return:
        """
        try:
            return self.db_engine.session.query(self.model).all()
        except Exception as ex:
            raise ex

    def get_by_id(self, object_id):
        try:
            return self.db_engine.session.query(self.model).filter_by(id=object_id).one()
        except NoResultFound:
            logger.debug("No result found for object_id %s", object_id)
            return None

    def find(self, **kwargs):
        """Returns a list of instances of the service's model filtered by the
        specified key word arguments.
        :param **kwargs: filter parameters
        """
        return self.model.query.filter_by(**kwargs)

    def one(self, **kwargs):
        """Returns a single instance of self.model based on the parameters supplied."""

        try:
            return self.find(**kwargs).one()
        except (NoResultFound, MultipleResultsFound) as ex:
            if isinstance(ex, NoResultFound):
                return None
            else:
                raise InvalidObjectException("More than one result found for query.")

    def pre_process_update_args(self, kwargs):
        """Pre-Process arguments supplied to the update method.

        :param kwargs:
        :return:
        """
        return kwargs

    def on_before_update(self, instance):
        """Implementation to perform any operations on the instance before performing an update.

        :param instance:
        :return:
        """
        pass

    def on_after_update(self, instance):
        """Implementation to perform any operations on the instance after performing an update.

        :param instance:
        :return:
        """
        pass

    def update_instance(self, instance, **kwargs):
        """Update an instance with the supplied keyword arguments.

        :param instance:
        :param kwargs:
        :return:
        """
        try:
            self.on_before_update(instance)
            kwords = self.pre_process_update_args(kwargs)
            for key, value in kwords.items():
                setattr(instance, key, value)
            self.save(instance)
            self.on_after_update(instance)
            return instance
        except Exception as ex:
            raise ex

    def update(self, id, **kwargs):
        """Returns an updated instance of the service's model class.
        :param model: the model to update
        :param **kwargs: update parameters
        """

        try:
            instance = self.get_by_id(id)
            if instance is None:
                return None
            else:
                return self.update_instance(instance, **kwargs)
        except Exception as ex:
            raise ex

    def delete(self, object_id):
        """Delete an object by it's id.

        :param object_id:
        :return:
        """
        try:
            self.db_engine.session.delete(self.get_by_id(object_id))
            self.db_engine.session.commit()
        except UnmappedInstanceError as ex:
            if self.get_by_id(object_id) is None:
                logger.info("Attempted to delete an invalid object object_id: %s", object_id)
                raise DeleteInvalidObjectException("Attempting to delete invalid object.")
            else:
                raise DeleteInvalidObjectException("Unable to delete object.")

    def on_before_save(self, instance):
        """Implementation hook to handle any operation on the instance before it is saved.

        :param instance:
        :return:
        """
        pass

    def save(self, instance):
        """Save an instance.

        :param instance:
        :return:
        """

        if not isinstance(instance, self.model):
            raise InvalidObjectType("Cannot save model of %s" % type(instance))
        self.on_before_save(instance)
        try:
            self.db_engine.session.add(instance)
            self.db_engine.session.commit()
            return instance
        except Exception as ex:
            logger.warn("An unhandled error happened %s", str(ex))
            raise ex

    def on_new_instance(self, instance):
        """Implementation hook for pre-processing on the new_instance method.
        This method should be implemented by subclasses to handle any manipulation
        on a model after it has been instantiated and before it is saved.

        :param kwargs:
        :return: None
        """

        pass

    def pre_process_new_args(self, kwargs):
        """Returns a dict of parameters for needed to create a new instance or update
        an instance of self.model.

        This method should be overrode by subclasses and used to pre-validate and pre-process
        keyword arguments as needed.

        :param kwargs: A dictionary of model parameters.
        :return: dict
        """

        return kwargs

    # TODO: Is this method necassary?
    def new_instance(self, **kwargs):
        """Factory method to create and return a new model instance.

        :param kwargs:
        :return:
        """

        instance = self.model(**self.pre_process_new_args(kwargs))
        self.on_new_instance(instance)
        return instance

    def on_before_create(self, **kwargs):
        """Implementation hook for pre-processing on the create method.
        This method should be used by subclasses to handle pre-validation.

        :param kwargs:
        :return:
        """
        pass

    def on_after_create(self, instance):
        """Implementation hook for post processing an instance after it has been created.

        :param instance:
        :return:
        """
        pass

    def create(self, **kwargs):
        """Create an instance

        :param kwargs:
        :return:
        """
        self.on_before_create(**kwargs)
        try:
            instance = self.save(self.new_instance(**kwargs))
            self.on_after_create(instance)
            return instance
        except Exception as ex:
            logger.error("An unhandled error in create %s", str(ex))
            raise ex


def authorize_request(func):
    """ Enfold authentication to verify x-subject-token or x-auth-token for access to urls.

    :param token:  An x-auth or x-subject token issued during authentication.
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        app = current_app
        ctx = app.app_context()
        ctx.push()

        result = enfold_client.authorize(
            request.headers.get('UserId'),
            auth_token=request.headers.get('Authorization'),
            project_id=request.headers.get('ProjectId'))

        if result.status_code == 200:
            ctx.pop()
            return func(*args, **kwargs)
        else:
            response = jsonify({"error": "Unable to authorize user."})
            response.status_code = 401
            current_app.logger.info("Unable to authorize user.")
            ctx.pop()
            return response

    return wrapper


class AuthorizedResource(Resource):
    """Resources that require user authorization viz enfold."""

    method_decorators = [authorize_request]


class BaseResource(Resource):

    data_service = None
    serializer = None
    post_fields = None
    patch_fields = None
    disabled_methods = None
    is_collection = False
    prefix = None
    id_attribute = None

    def pre_process_patch_data(self, patch_data):
        """Used to pre-process input data for the patch process.

        Here, implementing classes should handle pre-validation and pre-processing
        of patch data.  The method can / should raise 400 exceptions for invalid
        patch params.  This method should return a dictionary containing the
        parameters that will be ultimately passed to data_service(s) for updating
        the underlying data model.

        :param patch_data:
        :return: dict
        """
        return patch_data

    def pre_process_post_data(self, post_data):
        """Used to pre-process input data for the post process.

        Here, implementing classes should handle pre-validation and pre-processing
        of post data.  The method can / should raise 400 exceptions for invalid
        post params.  This method should return a dictionary containing the
        parameters that will be ultimately passed to data_service(s) for updating
        the underlying data model.

        :param post_data:
        :return: dict
        """
        return post_data

    def pre_process_put_data(self, put_data):
        """Used to pre-process input data for the put process.

        Here, implementing classes should handle pre-validation and pre-processing
        of put data.  The method can / should raise 400 exceptions for invalid
        put params.  This method should return a dictionary containing the
        parameters that will be ultimately passed to data_service(s) for updating
        the underlying data model.

        :param put_data:
        :return:
        """
        pass

    def get_collection(self):
        """

        :return:
        """
        try:
            sdata, errors = self.serializer.dump(self.data_service.get_all(), many=self.is_collection)
            resp = json_response_factory(200, {"projects": sdata})
            return resp
        except Exception as ex:
            return server_exception(ex)

    def get_resource(self, id):
        """
        :param id:
        :return:
        """
        instance = self.data_service.one(id=id)
        if instance is None:
            return not_found_response(self.prefix, id)

        sdata, serrors = self.serializer.dump(instance)
        if serrors:
            return bad_request(serrors)

        self.data_service.save(instance)

        return json_response_factory(status_code=200, data={"project": sdata})

    def get_id_value(self, **kwargs):
        """
        :param kwargs:
        :return:
        """
        if self.id_attribute is None:
            return kwargs.get('id')
        else:
            return kwargs.get(self.id_attribute)

    def get(self, **kwargs):
        """
        :param kwargs:
        :return:
        """

        if self.is_collection:
            return self.get_collection()
        else:
            return self.get_resource(self.get_id_value(**kwargs))

    def post(self):
        """

        :return:
        """
        if not self.is_collection:
            return method_not_allowed()

        post_data = self.pre_process_post_data(request.get_json())
        instance = self.data_service.create(**post_data)
        sdata, serrors = self.serializer.dump(instance, many=False)

        if serrors:
            return bad_request(serrors)
        return jsonify(self.serializer.dump({self.prefix: sdata}))

    def patch(self, object_id):
        """

        :param object_id:
        :return:
        """
        if self.is_collection:
            return method_not_allowed()

        patch_data = self.pre_process_patch_data(request.get_json())
        instance = self.data_service.get_by_id(object_id)
        if instance is None:
            return not_found_response(self.prefix, object_id)

        self.data_service.update_instance(instance, patch_data)
        sdata, serrors = self.serializer.dump(instance, many=False)
        if serrors:
            return bad_request(serrors)
        return json_response_factory(200, {self.prefix: sdata})


class SchemaCrudMixin(object):
    """

    """

    versionSource = mf.String()
    insertDate = mf.DateTime()
    insertByUserId = mf.String()
    updateDate = mf.DateTime()
    updateByUserId = mf.String()
    deletedTimeStamp = mf.DateTime()
    version = mf.String()
