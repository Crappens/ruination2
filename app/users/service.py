from app.base import DataServiceBase
from app.common.utils import set_model_uuid_and_dates


class UserDataService(object):

    def on_new_instance(self, instance):
        """

        :param instance: app.users.schema.sqlmodels.UserModel
        :return:
        """
        set_model_uuid_and_dates(instance)

    def create(self, **kwargs):
        """
        :keyword id:
        :keyword name:
        :keyword first_name:
        :keyword last_name:
        :keyword email_address:
        :param kwargs:
        :return: app.users.schema.sqlmodels.UserModel
        """
        return super(UserDataService, self).create(**kwargs)
