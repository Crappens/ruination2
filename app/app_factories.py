import importlib

from flask import Flask
import logging
from logging.handlers import RotatingFileHandler

from raven.handlers.logging import SentryHandler

from app.config import config_map
from app import mysocket
from app import scheduler
from app.models import db
from app.s3_connection import init_s3_connection


class BlueprintError(Exception):
    """Error / Exception to be raised if there is an issue registering
    blueprints when constructing a RuinationWeb instance.
    """
    pass


class ExtensionsError(Exception):
    """Error / Exception to be raised if there is an issue initializing Flask
    extensions.
    """
    pass


class ConfigError(Exception):
    """Error / Exception to be raised if there is an issue loading
    configuration objects.
    """
    pass


class RuinationWeb(Flask):
    """Wrapper around flask.Flask app to handle streamlined
       registration of blueprints and extensions.
    """

    def __init__(self, **kwargs):
        """
        :param args:
        :param config_name: The name of the configuration used to launch this instance
        :param debug: Flag to enable or disable Flask debugging.
        :return RuinationWeb:
        """

        config_name = kwargs.pop('config_name')
        debug = kwargs.pop('debug')
        # super(RuinationWeb, self).__init__(import_name=__name__, static_url_path="/pyapi/static", **kwargs)
        super(RuinationWeb, self).__init__(import_name=__name__, **kwargs)
        self.debug = debug

        # TODO Handle KeyError for bad config names
        self.config.from_object(config_map[config_name])
        self.api_prefix = self.config.get('API_PREFIX')
        self.s3_conn = init_s3_connection(self)

        self._init_extensions()
        self._register_packages()
        self._init_logging()
        db.init_app(app=self)

    def _init_logging(self):
        """Initialize logging used by the app instance.

        :return: None
        """

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        handler = RotatingFileHandler(
            filename=self.config['LOGFILE'], maxBytes=1024 * 1024 * 50, backupCount=10
        )

        handler.setFormatter(formatter)

        sentry_handler = SentryHandler(self.config.get('SENTRY_DSN'))
        sentry_handler.setFormatter(formatter)

        self.logger.setLevel(self.config.get('LOGLEVEL'))
        self.logger.addHandler(handler)
        self.logger.addHandler(sentry_handler)

    def _init_extensions(self):
        """Initialize extensions used by the app instance.

        This method expects a python module named extensions and an
        iterable named extension_list that contains (as strings) the
        names of the extensions to be used by the app.

        :return: None
        :raises: ExtensionsError
        """

        try:
            ext_module = importlib.import_module("app.extensions")
            for extension in ext_module.extension_list:
                getattr(ext_module, extension).init_app(self)
        except Exception as ex:
            raise ExtensionsError(
                'Error registering extensions: {0:s}'.format(str(ex))
            )

    def _register_packages(self):
        """Registers flask blueprints for registered packages

        This method expects there to be a configuration valued named
        REGISTERED_PACKAGES that is a iterable of the names of packages.
        These packages must expose a Flask.Blueprint named 'blueprint' in
        the package's __init__ OR an iterable of Flask.Blueprints in the
        same location named 'blueprints'.

        :return: None
        :raises: BlueprintError
        """

        try:
            for package in self.config['REGISTERED_PACKAGES']:
                imported = importlib.import_module('app.%s' % package)

                if hasattr(imported, 'blueprint'):
                    self.register_blueprint(imported.blueprint, url_prefix=self.api_prefix)
                elif hasattr(imported, 'blueprints'):
                    for blueprint in imported.blueprints:
                        self.register_blueprint(blueprint, url_prefix=self.api_prefix)
                else:
                    raise AttributeError(
                        u'Package {0:s} does not expose blueprint(s)'.format(package))

        except AttributeError as ae:
            raise BlueprintError(
                'Error registering package due to error: {0:s}'.format(str(ae))
            )


def init_runination_app(debug=False, config_name='develop'):
    """Create and initialize a Flask application object.

    :param debug:
    :param config_name:
    :return: RuinationWeb
    """

    app = RuinationWeb(config_name=config_name, debug=debug)
    mysocket.register(app, "/pyapi/ws-connect")
    scheduler.start(config_name)

    return app
