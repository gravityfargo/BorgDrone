from flask import Blueprint

from borgdrone.helpers import ResponseHelper

dashboard_blueprint = Blueprint("dashboard", __name__, template_folder="templates")


@dashboard_blueprint.route("/")
def index():
    rh = ResponseHelper(get_template="dashboard/index.html")
    return rh.respond()
