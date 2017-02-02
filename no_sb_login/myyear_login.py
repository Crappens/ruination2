__author__ = 'bcrysler'


import json
import requests
import webbrowser


RUINATION_ADDR = "http://localhost"

ENFOLD_ADDR = "http://10.90.30.54:8000"
ENFOLD_PORT = 8000
MYYEAR_URL = "http://www.testmyyear.com"

USERNAME = "adminuser001"
PASSWORD = "asdfasdf"
PROJECT_ID = None
PROJECT_NUMBER = None

auth_resp = requests.post(url=ENFOLD_ADDR + "/authenticate",
                          data=json.dumps({"username": USERNAME, "password": PASSWORD}),
                          headers={"Content-Type": "application/json"})
auth_dict = json.loads(auth_resp.text)
print auth_dict

TOKEN = auth_dict["token"]["x-subject-token"]
USER_ID = auth_dict["token"]["user"]["id"]

if PROJECT_ID is None and PROJECT_NUMBER is None:
    PROJECT_ID = auth_dict["projects"][0]["id"]
    PROJECT_NUMBER = auth_dict["projects"][0]["number"]
elif PROJECT_ID is None:
    PROJECT_ID = [x for x in auth_dict["projects"] if x["number"] == PROJECT_NUMBER][0]["id"]
elif PROJECT_NUMBER is None:
    PROJECT_NUMBER = [x for x in auth_dict["projects"] if x["id"] == PROJECT_ID][0]["number"]

form_data = {"user_id": USER_ID,
             "project_id": PROJECT_ID,
             "token": TOKEN,
             "project_number": PROJECT_NUMBER,
             "login_name": USERNAME}

url = "{0:s}/index.html#/loginFromStudio/{1:s}/{2:s}/{3:s}/{4:s}/{5:s}/{6:s}/BP".format(
    MYYEAR_URL, PROJECT_ID, PROJECT_NUMBER, USER_ID, TOKEN, PROJECT_ID, USERNAME
)
webbrowser.open(url)
