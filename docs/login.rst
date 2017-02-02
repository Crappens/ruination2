My Year Login Process:
=======================

The initial login request is against:

    POST http://APP_HOST/api/login/studio

With the following parameters:

    * project_number
    * project_id
    * user_id
    * token
    * login_name

This request processes the input to validate that the user is authorized.  Once complete,
the user is redirected to.

    http://APP_HOST/index.html#/loginFromStudio/<projectid>/<project_number>/<user_id>/<token>/<bookid>/<username>

When the post is processed, the user's and project's information is verified.  Once it is verified,
the user is redirected to

    http://APP_HOST/book/<bookid>
