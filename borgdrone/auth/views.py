from flask import Blueprint, request
from flask_login import current_user, login_required

from borgdrone.helpers import ResponseHelper

from .managers import UserManager

auth_blueprint = Blueprint("auth", __name__, template_folder="templates")


@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    rh = ResponseHelper(
        get_template="auth/login.html",
        post_error_template="auth/login.html",
        post_success_template="dashboard/index.html",
    )

    if request.method == "POST":
        form_data = request.form
        user_name: str = form_data["username"]
        password: str = form_data["password"]
        remember: bool = form_data.get("remember", default=False, type=bool)

        um = UserManager()

        result_log = um.get(username=user_name)
        if not (user := result_log.data):
            rh.toast_error = "User not found."
            return rh.respond(error=True)

        result_log = um.login(user, password, remember)
        rh.borgdrone_return = result_log.borgdrone_return()

        if not (user := result_log.get_data()):
            rh.toast_error = result_log.error_message
            return rh.respond(error=True)

        rh.toast_success = result_log.message
        return rh.respond()

    rh.htmx_refresh = True
    # {% if current_user.is_authenticated %} needs the refresh
    return rh.respond()


@auth_blueprint.route("/logout")
@login_required
def logout():
    rh = ResponseHelper()

    um = UserManager()
    result_log = um.logout()
    rh.toast_success = result_log.message
    rh.borgdrone_return = result_log.borgdrone_return()

    return rh.respond()
