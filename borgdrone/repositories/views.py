from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from borgdrone.helpers import ResponseHelper, datahelpers

from . import RepositoryManager as repository_manager

repositories_blueprint = Blueprint("repositories", __name__, template_folder="templates")


@repositories_blueprint.route("/")
@login_required
def index():
    rh = ResponseHelper(get_template="repositories/index.html")
    rh.context_data = {"repositories": [], "convert_bytes": datahelpers.convert_bytes}
    repos = repository_manager.get_all()
    if repos:
        rh.context_data["repositories"] = repos

    return rh.respond()


@repositories_blueprint.route("/create/", methods=["GET", "POST"])
@login_required
def create_repo() -> Any:
    rh = ResponseHelper(
        get_template="repositories/create.html",
        post_success_template="repositories/index.html",
        post_error_template="repositories/create.html",
    )  # TODO: Encryption

    if request.method == "POST":
        form_data = request.form
        rh.context_data = {"repositories": [], "convert_bytes": datahelpers.convert_bytes}

        result_log = repository_manager.create_repo(form_data["path"], form_data["encryption"])
        rh.borgdrone_return = result_log.borgdrone_return()

        if result_log.status == "FAILURE":
            rh.toast_error = result_log.error_message
            return rh.respond(error=True)

        repos = repository_manager.get_all()
        if repos:
            rh.context_data["repositories"] = repos

        rh.toast_success = result_log.message
        return rh.respond()

    return rh.respond()


@repositories_blueprint.route("/info", methods=["POST"])
@login_required
def get_repository_info() -> Any:
    rh = ResponseHelper(
        post_success_template="repositories/repo_stats.html",
    )

    form_data = request.form
    result_log = repository_manager.get_repository_info(path=form_data["path"], passphrase=form_data["passphrase"])
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
        form_data = request.form

        result_log = repository_manager.import_repo(path=form_data["path"], passphrase=form_data["passphrase"])
        rh.borgdrone_return = result_log.borgdrone_return()

        if result_log.status == "FAILURE":
            rh.toast_error = result_log.error_message
            return rh.respond(error=True)

        rh.toast_success = result_log.message
        rh.htmx_refresh = True
        return rh.respond()

    return rh.respond()


@repositories_blueprint.route("/delete/<db_id>", methods=["DELETE"])
@login_required
def delete_repo(db_id) -> Any:
    rh = ResponseHelper()

    result_log = repository_manager.delete_repo(db_id)
    rh.borgdrone_return = result_log.borgdrone_return()

    if result_log.status == "FAILURE":
        rh.toast_error = result_log.error_message
        return rh.respond()

    rh.toast_success = result_log.message
    return rh.respond()


@repositories_blueprint.route("/update/<db_id>", methods=["POST"])
@login_required
def update_stats(db_id):
    rh = ResponseHelper()

    result_log = repository_manager.update_repository_info(db_id=db_id)
    rh.borgdrone_return = result_log.borgdrone_return()

    if result_log.status == "FAILURE":
        rh.toast_error = result_log.error_message
        return rh.respond(empty=True)

    rh.toast_success = result_log.message
    rh.htmx_refresh = True
    return rh.respond(empty=True)
