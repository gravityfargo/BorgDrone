from typing import Any

from flask import Blueprint, request
from flask_login import current_user, login_required

from borgdrone.helpers import ResponseHelper, datahelpers

from .managers import RepositoryManager

# from borgdrone.logging import BorgdroneEvent


repositories_blueprint = Blueprint("repositories", __name__, template_folder="templates")
repo_manager = RepositoryManager()


@repositories_blueprint.route("/")
@login_required
def index():
    rh = ResponseHelper(get_template="repositories/index.html")

    result_log = repo_manager.get_all()

    rh.context_data = {"repos": result_log.data, "convert_bytes": datahelpers.convert_bytes}
    rh.borgdrone_return = result_log.borgdrone_return()
    return rh.respond()


@repositories_blueprint.route("/create/", methods=["GET", "POST"])
@login_required
def create_repo() -> Any:
    # TODO: Encryption
    rh = ResponseHelper(
        get_template="repositories/create.html",
        post_success_template="repositories/index.html",
        post_error_template="repositories/create.html",
    )

    if request.method == "POST":
        form_data = request.form

        result_log = repo_manager.create_repo(path=form_data["path"], encryption=form_data["encryption"])
        rh.borgdrone_return = result_log.borgdrone_return()

        if result_log.status == "FAILURE":
            rh.toast_error = result_log.error_message
            return rh.respond(error=True)

        repos = repo_manager.get_all()
        rh.context_data = {"repos": repos.data, "convert_bytes": datahelpers.convert_bytes}
        rh.toast_success = result_log.message
        return rh.respond()

    return rh.respond()


@repositories_blueprint.route("/info", methods=["POST"])
@login_required
def get_repository_info() -> Any:
    rh = ResponseHelper(post_success_template="repositories/repo_stats.html")

    result_log = repo_manager.get_repository_info(path=request.form["path"])
    rh.borgdrone_return = result_log.borgdrone_return()

    if result_log.status == "FAILURE":
        rh.toast_error = result_log.error_message
        return rh.respond(empty=True)

    rh.context_data = {"repository": result_log.data, "convert_bytes": datahelpers.convert_bytes}
    return rh.respond()


@repositories_blueprint.route("/import", methods=["GET", "POST"])
@login_required
def import_repo() -> Any:
    rh = ResponseHelper(
        get_template="repositories/import.html",
        post_success_template="repositories/index.html",
        post_error_template="repositories/import.html",
    )

    if request.method == "POST":
        result_log = repo_manager.import_repo(path=request.form["path"])
        rh.borgdrone_return = result_log.borgdrone_return()

        if result_log.status == "FAILURE":
            rh.toast_error = result_log.error_message
            return rh.respond(error=True)

        rh.toast_success = result_log.message
        rh.htmx_refresh = True
        return rh.respond()

    return rh.respond()


@repositories_blueprint.route("/delete/<repo_id>", methods=["DELETE"])
@login_required
def delete_repo(repo_id) -> Any:
    rh = ResponseHelper()

    result_log = repo_manager.delete_repo(repo_id)
    rh.borgdrone_return = result_log.borgdrone_return()

    if result_log.status == "FAILURE":
        rh.toast_error = result_log.error_message
        return rh.respond()

    rh.toast_success = result_log.message
    return rh.respond()


@repositories_blueprint.route("/update/<repo_id>", methods=["POST"])
@login_required
def update_stats(repo_id):
    rh = ResponseHelper()

    result_log = repo_manager.update_repository_info(repo_id=repo_id)
    rh.borgdrone_return = result_log.borgdrone_return()

    if result_log.status == "FAILURE":
        rh.toast_error = result_log.error_message
        return rh.respond(empty=True)

    rh.toast_success = result_log.message
    rh.htmx_refresh = True
    return rh.respond(empty=True)
