"""
A laughably primitive dependency injector for the 'uwsgi' module.
(see mock_uwsgi.py for details)
"""
try:
    import uwsgi
except ImportError:
    import mock_uwsgi as uwsgi
