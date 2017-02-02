from __future__ import absolute_import
import copy
from datetime import datetime

from sqlalchemy.orm.exc import NoResultFound

from app.common.exceptions import InvalidObjectException
from app.projects.svg_api import SheetSVG
from app.common.utils import set_model_uuid_and_dates, log_request_error
from app.projects.api import project_exists
from app.models import db, Sheet


class SheetService(object):

    def __init__(self):
        super(SheetService, self).__init__()

    def get_child_sheet(self, id):
        try:
            return db.session.query(Sheet).filter_by(parent_sheet=id).first()
        except NoResultFound as ex:
            log_request_error(str(ex))
            return None

    def get_svg(self, page_size, sheet_type, cutback):
        svg = SheetSVG(width=page_size.width, height=page_size.height, cutback=cutback)
        if sheet_type == "COVER":
            return svg.fullSVG
        elif sheet_type == "FIRST_SHEET":
            return svg.rightPageSVG.replace("LEFT_FOLIO", "")
        elif sheet_type == "LAST_SHEET":
            return svg.leftPageSVG.replace("RIGHT_FOLIO", "")
        else:
            return svg.fullSVG

    def pre_process_new_args(self, kwargs):
        try:
            kwords = copy.deepcopy(kwargs)
            page_size = kwords.pop("page_size")
            kwords['svg'] = self.get_svg(page_size, kwargs.get("type"), kwargs.get("cutback"))
            return kwords
        except Exception as ex:
            log_request_error(str(ex))
            raise ex

    def on_new_instance(self, instance):
        set_model_uuid_and_dates(instance)

    def on_before_create(self, **kwargs):

        if not project_exists(kwargs.get("book_id")):
            log_request_error("Unable to create a sheet due to an invalid project id being provided.")
            raise InvalidObjectException(
                "Unable to create a sheet due to an invalid project id being provided."
            )

    def on_before_save(self, instance):

        if isinstance(instance.version, int):
            instance.updated = datetime.now()
        if isinstance(instance.version, type(None)):
            instance.version = 1
