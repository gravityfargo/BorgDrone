from typing import Any, Dict, List, Optional

import yaml
from flask_login import current_user
from sqlalchemy import select

from borgdrone.borg.constants import BORG_CREATE_COMMAND
from borgdrone.extensions import db
from borgdrone.helpers import bash, datahelpers, filemanager
from borgdrone.logging import BorgdroneEvent
from borgdrone.repositories import Repository
from borgdrone.types import OptInt, OptStr

from . import BundleDirectoryManager as bundle_directory_manager
from .models import BackupBundle, ListBackupBundle, OptBackupBundle


def get_one(
    bundle_id: OptInt = None, repo_id: OptInt = None, command_line: OptStr = None
) -> BorgdroneEvent[OptBackupBundle]:
    _log = BorgdroneEvent[OptBackupBundle]()
    _log.event = "BundleManager.get_one"

    instance = None
    if repo_id:
        stmt = select(BackupBundle).where(BackupBundle.repo_id == repo_id)
        instance = db.session.scalars(stmt).first()

    elif bundle_id:
        stmt = select(BackupBundle).where(BackupBundle.id == bundle_id)
        instance = db.session.scalars(stmt).first()

    elif command_line:
        stmt = select(BackupBundle).where(BackupBundle.command_line == command_line)
        instance = db.session.scalars(stmt).first()

    _log.set_data(instance)

    if not instance:
        _log.status = "FAILURE"
        _log.error_message = "Bundle not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "BackupBundle Retrieved."

    return _log  # No need to log this, so not using return_success()


def get_all(repo_id: OptStr = None) -> BorgdroneEvent[Optional[ListBackupBundle]]:
    _log = BorgdroneEvent[Optional[ListBackupBundle]]()
    _log.event = "BundleManager.get_all"

    instances = None
    if repo_id:
        stmt = select(BackupBundle).where(BackupBundle.repo_id == repo_id)
        instances = list(db.session.scalars(stmt).all())
    else:
        stmt = select(BackupBundle).join(Repository).where(Repository.user_id == current_user.id)
        instances = list(db.session.scalars(stmt).all())

    _log.set_data(instances)
    if not instances:
        _log.status = "FAILURE"
        _log.error_message = "Bundles not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "BackupBundles Retrieved."

    return _log  # No need to log this, so not using return_success()


def _set_bundle_values(bundle: BackupBundle, **kwargs) -> BackupBundle:
    bundle.repo_id = kwargs["repo_id"]
    bundle.cron_minute = kwargs["cron_minute"]
    bundle.cron_hour = kwargs["cron_hour"]
    bundle.cron_day = kwargs["cron_day"]
    bundle.cron_month = kwargs["cron_month"]
    bundle.cron_weekday = kwargs["cron_weekday"]
    bundle.comment = kwargs.get("comment", None)
    return bundle


def __process_form_data(bundle: BackupBundle, form_data: Dict[str, Any]) -> Optional[Dict[str, list]]:
    """Process form data for included and excluded directories.

    creates BackupDirectory instances for each included and excluded directory.

    Arguments:
        bundle -- BackupBundle instance
        form_data -- reqires "includedir..." and "excludedir..." keys

    Returns:
        Optional[Dict[str, list]]: "included_dirs", "exclude_dirs" keys with list of paths
    """
    data = {}
    data["included_dirs"] = []
    data["exclude_dirs"] = []

    status = ""
    for key, value in form_data.items():
        if key.startswith("includedir"):
            yaml_data: Dict[str, Any] = yaml.safe_load(value)
            data["included_dirs"].append(yaml_data.get("path"))

            result_log = bundle_directory_manager.create_bundledirectory(**yaml_data)
            if result_log.status == "FAILURE":
                status = "FAILURE"
                break

            if backup_dir := result_log.get_data():
                # this won't fail because of the previous status check
                bundle.backupdirectories.append(backup_dir)

        elif key.startswith("excludedir"):
            yaml_data: Dict[str, Any] = yaml.safe_load(value)
            yaml_data["bundle_id"] = bundle.id
            yaml_data["exclude"] = True

            data["exclude_dirs"].append("--exclude")
            data["exclude_dirs"].append(yaml_data.get("path"))

            result_log = bundle_directory_manager.create_bundledirectory(**yaml_data)
            if result_log.status == "FAILURE":
                status = "FAILURE"
                break

            if backup_dir := result_log.get_data():
                # this won't fail because of the previous status check
                bundle.backupdirectories.append(backup_dir)

    if status == "FAILURE":
        return None

    return data


def update_bundle(bundle_id: int, **kwargs) -> BorgdroneEvent[BackupBundle]:
    _log = BorgdroneEvent[BackupBundle]()
    _log.event = "BundleManager.update_bundle"

    result_log = get_one(bundle_id=bundle_id)
    if not (bundle := result_log.get_data()):
        return _log.not_found_message("Bundle")

    _set_bundle_values(bundle, **kwargs)
    bundle.commit()

    _log.set_data(bundle)

    data = __process_form_data(bundle, kwargs)
    if not data:
        bundle.delete()
        return _log.return_failure("Error processing form data.")

    if not data["included_dirs"]:
        bundle.delete()
        return _log.return_failure("You must include at least one include directory.")

    # "--list",
    backup_command = BORG_CREATE_COMMAND.copy()
    backup_command.extend(data["exclude_dirs"])
    backup_command.append(f"{bundle.repo.path}::{bundle.repo.name_format}")
    backup_command.extend(data["included_dirs"])

    bundle.command_line = " ".join(backup_command)
    bundle.commit()

    return _log.return_success("Bundle updated successfully.")


def create_bundle(**kwargs) -> BorgdroneEvent[BackupBundle]:
    """Create or Update a bundle.

    Returns:
        _description_
    """
    _log = BorgdroneEvent[BackupBundle]()
    _log.event = "BundleManager.create_bundle"

    bundle = _set_bundle_values(BackupBundle(), **kwargs)
    bundle.commit()
    _log.set_data(bundle)

    data = __process_form_data(bundle, kwargs)
    if not data:
        bundle.delete()
        return _log.return_failure("Error processing form data.")

    if not data["included_dirs"]:
        bundle.delete()
        return _log.return_failure("You must include at least one include directory.")

    # "--list",
    backup_command = BORG_CREATE_COMMAND.copy()
    backup_command.extend(data["exclude_dirs"])
    backup_command.append(f"{bundle.repo.path}::{bundle.repo.name_format}")
    backup_command.extend(data["included_dirs"])

    bundle.command_line = " ".join(backup_command)
    bundle.commit()

    return _log.return_success("Bundle created successfully.")


def delete_bundle(bundle_id: int) -> BorgdroneEvent:
    _log = BorgdroneEvent()
    _log.event = "BundleManager.delete_bundle"

    result_log = get_one(bundle_id=bundle_id)

    if not (bundle := result_log.get_data()):
        return _log.not_found_message("Bundle")

    bundle.delete()

    return _log.return_success("Bundle deleted successfully.")


def check_dir(path: str) -> BorgdroneEvent[List[str]]:
    _log = BorgdroneEvent[list]()
    _log.event = "BundleManager.check_dir"

    if not filemanager.check_dir(path):
        return _log.return_failure("Directory does not exist.")

    result = bash.run(f"ls -ld {path}")
    if result.get("stderr"):
        resultstr = result["stderr"].replace("ls: ", "")
        return _log.return_failure(resultstr)

    data = result["stdout"].split()
    perms = datahelpers.convert_rwx_to_octal(data[0])
    user = data[2]
    group = data[3]

    _log.set_data([perms, user, group])

    return _log.return_success("Directory exists.")


def create_backup(bundle_id: int) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "BundleManager.create_backup"

    result_log = get_one(bundle_id=bundle_id)  # get the bundle
    if not (bundle := result_log.get_data()):
        return _log.not_found_message("Bundle")

    if not bundle.command_line:
        return _log.return_failure("Bundle has no command line set.")

    bash.popen(bundle.command_line.split(" "))

    return _log.return_success("Backup created successfully.")
