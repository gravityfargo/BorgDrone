import random
from typing import Any

from flask import Blueprint, request
from flask_login import login_required
from flask_socketio import emit

from borgdrone.extensions import socketio
from borgdrone.helpers import ResponseHelper
from borgdrone.repositories import RepositoryManager

from .managers import BundleManager
from .models import BackupBundle

bundles_blueprint = Blueprint("bundles", __name__, template_folder="templates")
bundle_manager = BundleManager()


@bundles_blueprint.route("/")
@login_required
def index():
    rh = ResponseHelper(get_template="bundles/index.html")

    result_log = bundle_manager.get_all()
    rh.context_data = {"bundles": result_log.get_data()}

    return rh.respond()


@bundles_blueprint.route("/check-dir/<path_type>", methods=["POST"])
@login_required
def check_dir(path_type):
    rh = ResponseHelper()

    input_path = ""
    if path_type == "include":
        input_path = request.form.get("include_path")
    else:
        input_path = request.form.get("exclude_path")

    if not input_path:
        rh.toast_error = "No path provided."
        return rh.respond(empty=True)

    result_log = bundle_manager.check_dir(input_path)
    rh.borgdrone_return = result_log.borgdrone_return()
    if result_log.status == "FAILURE":
        return rh.respond(empty=True)

    if not (data := result_log.get_data()):
        return rh.respond(empty=True)

    html = f"""
    <tr id="{input_path}">
        <textarea name="{path_type}dir{random.randint(0, 1000)}" hidden>
            path: {input_path}
            permissions: {data[0]}
            owner: {data[1]}
            group: {data[2]}
        </textarea>
        <td>
            {input_path}
        </td>
        <td>
            {data[0]}
        </td>
        <td>
            {data[1]}
        </td>
        <td>
            {data[2]}
        </td>
        <td>
            <i class="text-danger bi bi-trash3-fill"
                onclick="removePath(event)"
                id="{input_path}">
            </i>
        </td>
    </tr>
    """

    rh.toast_success = result_log.message
    # TODO: Check if the path is already in the form
    return rh.respond(data=html)


@bundles_blueprint.route("/form/<purpose>", defaults={"bundle_id": None}, methods=["GET", "POST"])
@bundles_blueprint.route("/form/<purpose>/<bundle_id>", methods=["GET", "POST"])
@login_required
def bundle_form(purpose, bundle_id) -> Any:
    # form inputs must be named the same as the BackupBundle model
    rh = ResponseHelper(
        get_template="bundles/bundle_form.html",
        post_success_template="bundles/index.html",
        post_error_template="bundles/bundle_form.html",
    )

    result_log = RepositoryManager().get_all()
    rh.context_data = {"repos": result_log.get_data(), "form_purpose": purpose}

    if request.method == "POST":
        data = request.form

        if purpose == "create":
            result_log = bundle_manager.create_bundle(**data)
            rh.borgdrone_return = result_log.borgdrone_return()

            if result_log.status == "FAILURE":
                rh.toast_error = result_log.error_message
                rh.context_data["bundle"] = result_log.data

                return rh.respond(error=True)

            rh.toast_success = result_log.message
            return rh.respond(redirect_url="bundles.index")

    # GET
    if purpose == "create":
        # Non-commited instance
        bundle = BackupBundle()
        bundle.cron_day = "*"
        bundle.cron_hour = "*"
        bundle.cron_minute = "*"
        bundle.cron_month = "*"
        bundle.cron_weekday = "*"

        rh.context_data["bundle"] = bundle

    elif purpose == "update":  # TODO
        result_log = bundle_manager.get_one(bundle_id=bundle_id)
        if result_log.status == "FAILURE":
            rh.toast_error = result_log.error_message
            return rh.respond()

        if not result_log.data:
            rh.toast_error = "Bundle not found."
            return rh.respond()

        rh.context_data["bundle"] = result_log.get_data()

    return rh.respond()


@bundles_blueprint.route("/delete/<int:bundle_id>", methods=["DELETE"])
@login_required
def delete_bundle(bundle_id):
    rh = ResponseHelper()

    result_log = bundle_manager.delete_bundle(bundle_id)
    rh.borgdrone_return = result_log.borgdrone_return()

    if result_log.status == "FAILURE":
        rh.toast_error = result_log.error_message
        return rh.respond()

    rh.toast_success = result_log.message
    return rh.respond()


@bundles_blueprint.route("/<int:bundle_id>/run")
@login_required
def run_backup(bundle_id: int):
    rh = ResponseHelper(
        get_template="bundles/runner.html",
    )
    result_log = bundle_manager.get_one(bundle_id=bundle_id)
    if not (bundle := result_log.get_data()):
        return rh.respond(empty=True)

    rh.context_data = {"bundle": bundle}
    return rh.respond()


@socketio.on("backup_start")
def handle_message(msg):

    bundle_id = msg["bundle_id"]
    result_log = bundle_manager.create_backup(bundle_id)

    if result_log.status == "FAILURE":
        emit("send_line", {"text": result_log.error_message})
        return

    emit("send_line", {"text": result_log.message})
