import os

from flask import Blueprint, render_template

template_dir = os.path.join(os.path.dirname(__file__), "templates")
archives_blueprint = Blueprint("archives", __name__, template_folder="templates")


@archives_blueprint.route("/")
def index():
    return render_template("archives/index.html", archives={})
