"""
curl -v -X POST -H "accept:application/json" -H "X-Subject-Tken:79c5b55c61f840708d649d14556513a3"
-H "project:crappens" -H "spread:butter" -H "sig:abc" -H "startpage:34" -H "endpage:35" -H "type:MY"
-H "category:proof" -F file=@/home/crappens/Desktop/crappens_034_035.pdf
http://localhost:8100/api/v1.0/submission/postfiles

"""
# import json
import os
import requests

from app.models import db  # , Book, User

from flask import Blueprint, jsonify, current_app  # , request
from flask.ext.restful import Resource, Api

from app.ripper import ripper


def submit_book(req_data, user, user_name, book, override=False, post=False):
    uncompleted = 0
    for sheet in book.sheets:
        if sheet.type in ["FIRST_SHEET", "LAST_SHEET", "SHEET"] and not sheet.completed:
            uncompleted += 1

    if not override:
        # This will allow the book to be re-published in event of failed pages.
        for each in book.sheets:
            if each.status and each.status == "PUBLISHED":
                return {"msg": "Your book has already been published.", "failed": True}

    # This is already checked in MyYear, but let's double check to be safe.
    if uncompleted > 0:
        return {"msg": "You have " + str(uncompleted) + " sheets that are not completed.", "failed": True}

    # MyYear is "whole book" submission, no individual spreads
    pdf = ripper.rip_book(project_id=req_data.get("project_id"), project_name=req_data.get("project_name"),
                          user_id=req_data.get("user_id"), token=req_data.get("token"),
                          split_spread=True, image_type="HighRes", thumbnail=False)

    url = current_app.config["SUBMISSION_URL"]

    failures = []
    for num, page in enumerate(pdf):
        _headers_ = {"accept": "application/json", "X-Subject-Token": req_data.get("token"),
                     "project": req_data.get("project_name"), "category": "final", "sig": "abc",
                     "startpage": num + 1, "endpage": num + 1, "spread": "butter", "type": "MY"}
        print "sending:", page
        resp = requests.post(url, headers=_headers_, files={'file': open(page, 'r')})

        if resp.status_code != 200:
            print resp
            resp = requests.post(url, headers=_headers_, files={'file': open(page, 'r')})
            if resp.status_code != 200:
                print resp
                failures.append(str(num))
        os.remove(page)

    if len(failures) > 0:
        msg = "Submission process completed by " + user_name + ". The following pages failed to be submitted: " + \
              ",".join(failures) + ". Please contact technical support."
    else:
        msg = "Your book was submitted successfully by %s." % user_name

    for sheet in book.sheets:
        sheet.status = "PUBLISHED"

    db.session.commit()

    return {"msg": msg}


class Submit(Resource):

    def post(self):
        # req_data = json.loads(request.data)
        # override = req_data.get("override")
        # user = db.session.query(User).filter_by(user_uuid=request.headers['UserID']).first()
        # user_name = user.user_first_name + " " + user.user_last_name
        # book = db.session.query(Book).filter_by(id_=req_data.get("project_id")).first()
        #
        # finished = submit_book(req_data, user, user_name, book, override, post=True)
        #
        # if finished.get("failed") != None:
        #     data = {"Error": finished["msg"]}
        # else:
        #     data = {"Success": finished["msg"]}
        # resp = jsonify(data)
        # resp.status_code = 200
        # return resp
        data = {"Error": "This should only be done over websockets."}
        resp = jsonify(data)
        resp.status_code = 400
        return resp


blueprint = Blueprint(name="submission", import_name=__name__)
api = Api(app=blueprint)

api.add_resource(Submit, '/submit')
