"""
The 'uwsgi' module provides access to a running uwsgi server,
and isn't available outside of the uwsgi process. This module
provides a fake implementation so we can run the unit tests
independently of uwsgi (in pycharm, for example).

(So if you call uwsgi.xyz(), add a mock xyz() definition in here.)
"""
import logging


def register_signal(num, who, fun):
    """
    http://uwsgi-docs.readthedocs.org/en/latest/PythonModule.html#uwsgi.register_signal
    :param num:
    :param who:
    :param fun:
    :return:
    """
    pass


def add_timer(sig_num, seconds):
    """
    http://uwsgi-docs.readthedocs.org/en/latest/PythonModule.html#uwsgi.add_timer
    :param seconds:
    :param sig_num:
    :return:
    """
    pass


def log(msg):
    """
    http://uwsgi-docs.readthedocs.org/en/latest/PythonModule.html#uwsgi.log
    :param msg:
    :return:
    """
    logging.debug(msg)
