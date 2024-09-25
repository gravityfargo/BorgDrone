from typing import Any, Dict, List, Optional

import yaml
from flask import current_app as app
from flask_login import current_user
from sqlalchemy import select

from borgdrone.archives.models import Archive
from borgdrone.borg import BorgRunner as borg_runner
from borgdrone.borg.constants import BORG_CREATE_COMMAND
from borgdrone.extensions import db
from borgdrone.helpers import bash, datahelpers, filemanager
from borgdrone.logging import BorgdroneEvent, logger
from borgdrone.repositories import Repository
from borgdrone.repositories import RepositoryManager as repository_manager
from borgdrone.types import OptInt, OptStr

from . import BackupDirectoryManager as backup_directory_manager
from .models import BackupBundle, ListBackupBundle, OptBackupBundle


def get_one(bundle_id: OptInt = None, repo_id: OptInt = None, command_line: OptStr = None) -> OptBackupBundle:
    stmt = None
    instance = None
    if repo_id:
        stmt = select(BackupBundle).where(BackupBundle.repo_id == repo_id)
    elif bundle_id:
        stmt = select(BackupBundle).where(BackupBundle.id == bundle_id)
    elif command_line:
        stmt = select(BackupBundle).where(BackupBundle.command_line == command_line)

    if stmt is not None:
        instance = db.session.scalars(stmt).first()

    return instance


def get_all(repo_id: OptStr = None) -> Optional[ListBackupBundle]:
    if repo_id:
        stmt = select(BackupBundle).where(BackupBundle.repo_id == repo_id)
    else:
        stmt = select(BackupBundle).join(Repository).where(Repository.user_id == current_user.id)

    instances = list(db.session.scalars(stmt).all())

    return instances


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

    for key, value in form_data.items():
        if key.startswith("includedir") or key.startswith("excludedir"):
            yaml_data: Dict[str, Any] = yaml.safe_load(value)

            # check if exists
            backup_dir = backup_directory_manager.get_one(path=yaml_data["path"])
            if not backup_dir:
                # else create the directory
                backup_dir = backup_directory_manager.create_bundledirectory(**yaml_data)

            if backup_dir not in bundle.backupdirectories:
                bundle.backupdirectories.append(backup_dir)
                bundle.update()

            if backup_dir.exclude:
                data["exclude_dirs"].append(backup_dir)
                data["exclude_dirs_paths"].append("--exclude")
                data["exclude_dirs_paths"].append(backup_dir.path)
            else:
                data["include_dirs"].append(backup_dir)
                data["include_dirs_paths"].append(backup_dir.path)

    return data


def __form_new_command(repo_path, name_format, exclude_dirs_paths, include_dirs_paths):
    backup_command = BORG_CREATE_COMMAND.copy()
    backup_command.extend(exclude_dirs_paths)
    backup_command.append(f"{repo_path}::{name_format}")
    backup_command.extend(include_dirs_paths)
    command_line = " ".join(backup_command)
    return command_line


def process_bundle_form(purpose: str, **kwargs) -> BorgdroneEvent[OptBackupBundle]:
    _log = BorgdroneEvent[OptBackupBundle]()
    _log.event = "BundleManager.process_bundle_form"

    if purpose == "create":
        # create the bundle object
        bundle = _set_bundle_values(BackupBundle(), **kwargs)

    elif purpose == "update":
        bundle_id = kwargs.get("bundle_id", None)
        bundle = get_one(bundle_id=bundle_id)
        if not bundle:
            return _log.not_found_message("Bundle")
    else:
        return _log.return_failure("Invalid purpose.")

    # get the parent repository
    repo = repository_manager.get_one(db_id=bundle.repo_id)
    if not repo:
        return _log.not_found_message("Repository")

    # add the bundle to the repository
    repo.backupbundles.append(bundle)
    bundle.commit()

    if not (data := __process_directories(bundle, kwargs)):
        bundle.delete()
        return _log.return_failure("Error processing form data.")

    if not data["include_dirs"]:
        bundle.delete()
        return _log.return_failure("You must include at least one include directory.")

    backup_command = __form_new_command(
        bundle.repo.path, bundle.repo.name_format, data["exclude_dirs_paths"], data["include_dirs_paths"]
    )
    bundle.command_line = backup_command
    bundle.update()

    _log.set_data(bundle)
    return _log.return_success("Bundle created successfully.")


def __process_command(command_line: str) -> Optional[Dict[str, Any]]:
    exclude_dirs_paths = []
    include_dirs_paths = []
    repo_path = ""
    name_format = ""

    if "create" not in command_line:
        return None

    command = command_line.split("create")

    part1 = command[0].split(" ")
    if part1[0] != "borg":
        return None

    part2 = command[1].split(" ")

    pos = 0
    for i, part in enumerate(part2):
        if not pos:
            if part == "--exclude":
                exclude_dirs_paths.append(part2[i + 1])
                continue

            if "::" in part:
                j = part.split("::")
                repo_path = j[0]
                name_format = j[1]
                pos = 1
                continue
        else:
            include_dirs_paths.append(part)
            continue

    return {
        "repo_path": repo_path,
        "name_format": name_format,
        "exclude_dirs_paths": exclude_dirs_paths,
        "include_dirs_paths": include_dirs_paths,
    }


def delete_bundle(bundle_id: int) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "BundleManager.delete_bundle"

    bundle = get_one(bundle_id=bundle_id)
    if not bundle:
        return _log.not_found_message("Bundle")

    bundle.delete()

    return _log.return_success("Bundle deleted successfully.")


def check_dir(path: str) -> BorgdroneEvent[List[str]]:
    _log = BorgdroneEvent[List[str]]()
    _log.event = "BundleManager.check_dir"

    if not filemanager.check_dir(path):
        return _log.return_failure("Directory does not exist.")

    result = bash.run(f"ls -ld {path}")
    if result.get("stderr"):  # this should never happen
        resultstr = result["stderr"].replace("ls: ", "")
        return _log.return_failure(resultstr)

    data = result["stdout"].split()
    perms = datahelpers.convert_rwx_to_octal(data[0])
    owner = data[2]
    group = data[3]

    _log.set_data([perms, owner, group])

    return _log.return_success("Directory ok.")


def create_backup(bundle_id: int) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "BundleManager.create_backup"

    bundle = get_one(bundle_id=bundle_id)  # get the bundle
    if not bundle:
        return _log.not_found_message("Bundle")

    if not bundle.command_line:
        return _log.return_failure("Bundle has no command line set.")

    emit_socket = True
    if app.config["PYTESTING"] == "True":
        emit_socket = False

    bash.popen(bundle.command_line, emit_socket)
    # TODO: Add a check for the return code of the borg command
    # i.e OSError: [Errno 28] No space left on device

    # Add the new archive to the database
    result_log = borg_runner.get_last_archive(bundle.repo.path)
    if not (archive_data := result_log.get_data()):
        logger.error(bundle.command_line)
        return _log.return_failure("Error getting archive data.")

    archive = Archive().update_from_dict(archive_data)

    bundle.archives.append(archive)
    bundle.commit()

    return _log.return_success("Backup created successfully.")
