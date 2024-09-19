import os

from flask import Blueprint, render_template

template_dir = os.path.join(os.path.dirname(__file__), "templates")
settings_blueprint = Blueprint("settings", __name__, template_folder="templates")


@settings_blueprint.route("/")
def index():
    return render_template("settings/settings_index.html")
