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

    repositories = repository_manager.get_all()
    rh.context_data = {"repositories": repositories}

    return rh.respond()


@archives_blueprint.route("/get", methods=["POST"])
@login_required
def get_archives():
    rh = ResponseHelper(post_success_template="archives/archives.html")

    repo_db_id = request.form.get("repo_db_id")
    if not repo_db_id:
        rh.toast_error = "No repository selected."
        return rh.respond(empty=True)

    archives = archive_manager.get_all(int(repo_db_id))
    rh.context_data = {"archives": archives}
    return rh.respond()


@archives_blueprint.route("/refresh", methods=["POST"])
@login_required
def refresh_archives():
    rh = ResponseHelper(post_success_template="archives/archives.html")

    repo_db_id = request.form["repo_db_id"]
    if not repo_db_id:
        rh.toast_error = "No repository selected."
        return rh.respond(empty=True)

    result_log = archive_manager.refresh_archives(int(repo_db_id), first=10)
    rh.borgdrone_return = result_log.borgdrone_return()

    if result_log.status == "FAILURE":
        rh.toast_error = result_log.error_message
        return rh.respond(empty=True)

    rh.context_data = {"archives": result_log.get_data()}
    return rh.respond(empty=True)
