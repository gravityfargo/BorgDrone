from flask import Blueprint, request
from flask_login import login_required

from borgdrone.helpers import ResponseHelper
from borgdrone.repositories import RepositoryManager as repository_manager

from . import ArchivesManager as archive_manager

archives_blueprint = Blueprint("archives", __name__, template_folder="templates")


@archives_blueprint.route("/")
@login_required
def index():
    rh = ResponseHelper(get_template="archives/index.html")

    result_log = repository_manager.get_all()
    rh.context_data = {"repositories": result_log.get_data()}

    return rh.respond()


@archives_blueprint.route("/get-archives", methods=["POST"])
@login_required
def get_archives():
    rh = ResponseHelper(post_success_template="archives/archives.html")

    repo_id = request.form["repo_id"]
    if not repo_id:
        rh.toast_error = "No repository selected."
        return rh.respond(empty=True)

    result_log = archive_manager.get_all(repo_id)
    rh.borgdrone_return = result_log.borgdrone_return()

    if result_log.status == "FAILURE":
        rh.toast_error = result_log.error_message
        return rh.respond(empty=True)

    rh.context_data = {"archives": result_log.get_data()}
    return rh.respond()
