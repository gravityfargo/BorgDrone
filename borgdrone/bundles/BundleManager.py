from typing import Any, Dict, List, Optional

import yaml
from flask_login import current_user
from sqlalchemy import select

from borgdrone.borg.constants import BORG_CREATE_COMMAND
from borgdrone.extensions import db
from borgdrone.helpers import bash, datahelpers, filemanager
from borgdrone.logging import BorgdroneEvent
from borgdrone.repositories import Repository
from borgdrone.repositories import RepositoryManager as repository_manager
from borgdrone.types import OptInt, OptStr

from . import BackupDirectoryManager as backup_directory_manager
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


def get_latest() -> BorgdroneEvent[OptBackupBundle]:
    _log = BorgdroneEvent[OptBackupBundle]()
    _log.event = "BundleManager.get_latest"

    stmt = select(BackupBundle).order_by(BackupBundle.id.desc())
    instance = db.session.scalars(stmt).first()

    _log.set_data(instance)
    if not instance:
        _log.status = "FAILURE"
        _log.error_message = "Bundle not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "Latest Bundle retrieved."

    return _log


def _set_bundle_values(bundle: BackupBundle, **kwargs) -> BackupBundle:
    bundle.repo_id = kwargs["repo_db_id"]
    bundle.cron_minute = kwargs["cron_minute"]
    bundle.cron_hour = kwargs["cron_hour"]
    bundle.cron_day = kwargs["cron_day"]
    bundle.cron_month = kwargs["cron_month"]
    bundle.cron_weekday = kwargs["cron_weekday"]
    bundle.comment = kwargs.get("comment", None)
    return bundle


def __process_directories(bundle, form_data: Dict[str, Any]) -> Optional[Dict[str, List[Any]]]:
    data = {
        "include_dirs": [],
        "include_dirs_paths": [],
        "exclude_dirs": [],
        "exclude_dirs_paths": [],
    }

    status = ""
    for key, value in form_data.items():
        if key.startswith("includedir") or key.startswith("excludedir"):
            yaml_data: Dict[str, Any] = yaml.safe_load(value)

            # Set the exclude field based on the key type
            if key.startswith("includedir"):
                yaml_data["exclude"] = False
            else:
                yaml_data["exclude"] = True

            result_log = backup_directory_manager.get_or_create_bundledirectory(bundle, **yaml_data)

            if result_log.status == "FAILURE":
                status = "FAILURE"
                break

            backup_dir = result_log.get_data()
            if not backup_dir:
                status = "FAILURE"
                break

            if key.startswith("includedir"):
                data["include_dirs"].append(backup_dir)
                data["include_dirs_paths"].append(backup_dir.path)
            else:
                data["exclude_dirs"].append(backup_dir)
                data["exclude_dirs_paths"].append("--exclude")
                data["exclude_dirs_paths"].append(backup_dir.path)

    if status == "FAILURE":
        return None

    return data


def update_bundle(bundle_id: int, **kwargs) -> BorgdroneEvent[OptBackupBundle]:
    _log = BorgdroneEvent[OptBackupBundle]()
    _log.event = "BundleManager.update_bundle"

    result_log = get_one(bundle_id=bundle_id)
    if not (bundle := result_log.get_data()):
        return _log.not_found_message("Bundle")

    bundle = _set_bundle_values(bundle, **kwargs)

    data = __process_directories(bundle, kwargs)
    if not data:
        _log.set_data(None)
        return _log.return_failure("Error processing form data.")

    if not data["include_dirs"]:
        _log.set_data(None)
        return _log.return_failure("You must include at least one include directory.")

    # remove deleted directories
    for directory in bundle.backupdirectories:
        if directory not in data["include_dirs"] or directory not in data["exclude_dirs"]:
            directory.delete()

    kwargs.pop("repo_db_id")
    kwargs.pop("excludedir")
    kwargs.pop("includedir")

    backup_command = BORG_CREATE_COMMAND.copy()
    backup_command.extend(data["exclude_dirs_paths"])
    backup_command.append(f"{bundle.repo.path}::{bundle.repo.name_format}")
    backup_command.extend(data["include_dirs_paths"])

    kwargs["command_line"] = " ".join(backup_command)

    bundle.update_kwargs(**kwargs)
    _log.set_data(bundle)

    return _log.return_success("Bundle updated successfully.")


def create_bundle(**kwargs) -> BorgdroneEvent[OptBackupBundle]:
    _log = BorgdroneEvent[OptBackupBundle]()
    _log.event = "BundleManager.create_bundle"

    bundle = _set_bundle_values(BackupBundle(), **kwargs)
    repo = repository_manager.get_one(db_id=bundle.repo_id)
    if not (repo := repo.get_data()):
        return _log.not_found_message("Repository")

    repo.backupbundles.append(bundle)

    bundle.commit()
    _log.set_data(bundle)

    data = __process_directories(bundle, kwargs)
    if not data:
        _log.set_data(None)
        bundle.delete()
        return _log.return_failure("Error processing form data.")

    if not data["include_dirs"]:
        _log.set_data(None)
        bundle.delete()
        return _log.return_failure("You must include at least one include directory.")

    # Only add unique directories to the backupdirectories list
    for directory in data["include_dirs"]:
        if directory not in bundle.backupdirectories:
            bundle.backupdirectories.append(directory)
        else:
            directory.delete()

    for directory in data["exclude_dirs"]:
        if directory not in bundle.backupdirectories:
            bundle.backupdirectories.append(directory)
        else:
            directory.delete()

    # "--list",
    backup_command = BORG_CREATE_COMMAND.copy()
    backup_command.extend(data["exclude_dirs_paths"])
    backup_command.append(f"{bundle.repo.path}::{bundle.repo.name_format}")
    backup_command.extend(data["include_dirs_paths"])

    bundle.command_line = " ".join(backup_command)
    bundle.update()

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
    if result.get("stderr"):  # this should never happen
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
