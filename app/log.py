from logging import Formatter
from logging.handlers import RotatingFileHandler

file_formatter = Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')


def get_file_handler(location):
    file_handler = RotatingFileHandler(
        filename=location,
        maxBytes=1024 * 1024 * 50,
        backupCount=10
    )
    file_handler.setFormatter(file_formatter)
    return file_handler
