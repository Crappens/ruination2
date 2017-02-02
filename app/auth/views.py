from __future__ import absolute_import

import json
import requests

from flask import current_app, request, redirect, Blueprint, render_template, jsonify

from app.common.utils import json_response_factory, log_request_error
from app.extensions import enfold_client as client
from .forms import FullLoginForm
from app.models import db, UserModel


auth_blueprint = Blueprint('auth', __name__, template_folder='templates')


def get_login_url(project_id, project_number, user_id, token, user_name, app_name):

    url = "{0:s}/index.html#/loginFromStudio/{1:s}/{2:s}/{3:s}/{4:s}/{5:s}/{6:s}/{7:s}".format(
        current_app.config["MYYEAR_URL"], project_id, project_number, user_id, token, project_id, user_name, app_name
    )
    return url


# Haven't figured out how to get swagger models off of this yet, may refactor to a standard resource format
@auth_blueprint.route("/login", methods=["POST", "GET"])
def simple_login():
    # View forms.py to see what fields need to be sent
    form = FullLoginForm(csrf_enabled=False)

    if form.validate_on_submit():
        user_id = form.user_id.data
        auth_token = form.token.data
        project_id = form.project_id.data

        form_values = {"user_id": form.user_id.data, "token": form.token.data, "project_id": form.project_id.data,
                       "login_name": form.login_name.data, "project_number": form.project_number.data}

        missing_params = [k for k, v in form_values.iteritems() if (str(v) is None or str(v) == "")]

        if len(missing_params) > 0:
            data = {"Error": {"Missing Fields": missing_params}}
            log_request_error('"Missing Fields":' + str(missing_params), request)
            return json_response_factory(status_code=401, data=data)

        authorization_response = client.authorize(
            user_id=user_id, auth_token=auth_token, project_id=project_id
        )

        if authorization_response.status_code == 200:

            project_number = form.project_number.data

            if not db.session.query(UserModel).filter_by(id=user_id).first():
                enfold_user_response = client.client.users.get(user_id=user_id)
                enfold_user = enfold_user_response.json()

                new_user = UserModel()
                new_user.id = enfold_user['user']['id']
                new_user.name = enfold_user['user']['name']
                new_user.first_name = enfold_user['user']['firstname']
                new_user.last_name = enfold_user['user']['lastname']
                new_user.email_address = enfold_user['user']['email']

            from app.projects.project_api import on_first_login
            # on_first_login will create a new book if an active book isn't found, otherwise return the active book
            proj = on_first_login(
                project_number=project_number,
                user_id=user_id,
                project_id=project_id,
                auth_token=auth_token
            )

            return redirect(
                get_login_url(
                    project_id=proj.id,
                    project_number=proj.number,
                    user_id=user_id,
                    token=auth_token,
                    user_name=form.login_name.data,
                    app_name=form.app_name.data
                )
            )
        else:
            data = {"Error": {"Unauthorized": "Invalid username/password combination."}}
            log_request_error('{"Unauthorized": "Invalid username/password combination."}', request)
            return json_response_factory(status_code=401, data=data)

    return render_template('loginform.html', form=form)


@auth_blueprint.route("/login/studio", methods=["POST"])
def login():
    """
    The login process should go like
    authorize -> retrieve project -> redirect

    The redirect expects project_id, user_id, token, project_number, login_name.

    The possible problem we have here is that
    1) The project_id is mongodb id....this may require a code change.....
        -> The call to p.getBooks().get(0).getId().toString() in now obsolete.

    """
    # project_number, project_id, user_id, token, login_name

    ar = client.authorize(
        user_id=request.form['user_id'],
        auth_token=request.form['token'],
        project_id=request.form['project_id']
    )

    status_code = ar.status_code
    if status_code == 200:
        return redirect(
            get_login_url(
                project_id=request.form['project_id'],
                project_number=request.form['project_number'],
                user_id=request.form['user_id'],
                token=request.form['token'],
                user_name=request.form['login_name'],
                app_name=request.form['app_name']
            )
        )

    else:
        log_request_error('User unauthorized', request)
        return render_template('401.html')


# This mirrors the Enfold /v2/authorize function except in the return.
# This function will return a dict of perm: true/false dictating what actions are allowed inside MyYear/Pages.
@auth_blueprint.route("/authorize", methods=["POST"])
def authorize():
    req_data = json.loads(request.data)
    req_perms = req_data["req_perms"]
    user_id = req_data["user_id"]
    project_id = req_data["project_id"]
    token = req_data["token"]
    auth_dict = {}
    for perm in req_perms:
        resp = requests.post(url=current_app.config["ENFOLD_URL"] + "/v2/authorize",
                             headers={"Content-Type": "application/json",
                                      "X-Auth-Header": current_app.config["ENFOLD_ADMIN_TOKEN"]},
                             data=json.dumps({"user_id": user_id, "project_id": project_id, "token": token,
                                              "req_perms": [perm]}))
        if resp.status_code == 200:
            auth_dict[perm] = True
        else:
            auth_dict[perm] = False
    return json_response_factory(status_code=200, data=auth_dict)


@auth_blueprint.route("/deauth/<token_uuid>", methods=["DELETE"])
def de_auth_token(token_uuid):

    # def delete(self, token_uuid):
    temp = requests.delete(current_app.config["ENFOLD_URL"] + "/token/" + token_uuid,
                           headers={"X-Auth-Token": current_app.config["ENFOLD_ADMIN_TOKEN"]})

    data = {"message": temp.status_code == 204}
    resp = jsonify(data)
    resp.status_code = 200
    return resp

