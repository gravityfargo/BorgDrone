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
        user = um.get(username=user_name)

        if not user:
            rh.toast_error = "User not found."
            rh.borgdrone_return = "Auth.UserNotFound"
            return rh.respond(error=True)

        if not um.login(user, password, remember):
            rh.toast_error = "Invalid credentials."
            rh.borgdrone_return = "Auth.InvalidCredentials"
            return rh.respond(error=True)

        rh.borgdrone_return = "Auth.LoginSuccess"
        return rh.respond()

    rh.htmx_refresh = True
    # {% if current_user.is_authenticated %} needs the refresh
    return rh.respond()


@auth_blueprint.route("/logout")
@login_required
def logout():
    rh = ResponseHelper()

    um = UserManager()
    user = um.get(user_id=current_user.id)
    if user and um.logout():
        rh.borgdrone_return = "Auth.LogoutSuccess"
        rh.toast_success = "You have been logged out."
    else:
        rh.borgdrone_return = "Auth.LogoutFailure"
        rh.toast_error = "An error occurred while logging out."

    return rh.respond()
