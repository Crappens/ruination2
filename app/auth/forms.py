from flask_wtf import Form
from wtforms import StringField, SubmitField

"""
<!DOCTYPE html>
<html>
<body>

<form action="http://127.0.0.1/api/login/studio" method="post">
<table>
<tr><td>Baan Book Number: <input type="text" name="project_number" value="JCA123" /></td></tr>
<tr><td>KeyStone Book Id: <input type="text" name="project_id" value="af2279264ac44162bb18244705433d3f" /></td></tr>
<tr><td>KeyStone User Id: <input type="text" name="user_id" value="92f4ac8b53af4b73b3e83161538fc721" /></td></tr>
<tr><td>KeyStone Auth Token: <input type="text" name="token" value="2819cc1d8b034f84884044960e6b2695" /></td></tr>
<tr><td>LoginName: <input type="text" name="login_name" value="ChrisAustinDevelop" /></td></tr>
</table>
<input type="submit"/>
</form>
      <p>Click on the submit button".</p>
      </body>
</html>
"""


class FullLoginForm(Form):

    project_number = StringField('Baan Book Number')
    project_id = StringField("Enfold Book Id")
    user_id = StringField("Enfold User Id")
    token = StringField("Auth Token")
    login_name = StringField("Login Name")
    app_name = StringField("Program")
    submit = SubmitField("Login")
