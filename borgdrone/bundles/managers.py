from typing import Any, Dict, List, Optional

import yaml
from flask import request
from flask_login import current_user
from sqlalchemy import select

from borgdrone.borg.constants import BORG_CREATE_COMMAND
from borgdrone.extensions import db
from borgdrone.helpers import bash, datahelpers, filemanager
from borgdrone.logging import BorgdroneEvent
from borgdrone.repositories import Repository

from .models import BackupBundle, BackupDirectory


class BundleManager:
    def __init__(self):
        pass

    def get_last(self) -> BorgdroneEvent[BackupBundle]:
        _log = BorgdroneEvent[BackupBundle]()
        _log.event = "BundleManager.get_last"

        instance = (
            db.session.query(BackupBundle)
            .join(Repository)
            .filter(Repository.user_id == current_user.id)
            .order_by(BackupBundle.id.desc())
            .first()
        )

        if instance:
            _log.set_data(instance)

        return _log.return_success("Last Bundle Retrieved.")

    def get_one(
        self, bundle_id: Optional[int] = None, repo_id: Optional[int] = None, command_line: Optional[str] = None
    ) -> BorgdroneEvent[Optional[BackupBundle]]:
        _log = BorgdroneEvent[Optional[BackupBundle]]()
        _log.event = "BundleManager.get_one"

        if repo_id:
            instance = db.session.scalars(select(BackupBundle).where(BackupBundle.repo_id == repo_id)).first()
        elif bundle_id:
            instance = db.session.scalars(select(BackupBundle).where(BackupBundle.id == bundle_id)).first()
        elif command_line:
            instance = db.session.scalars(
                select(BackupBundle).where(BackupBundle.command_line == command_line)
            ).first()
        else:
            instance = db.session.scalars(select(BackupBundle).where(BackupBundle.user_id == current_user.id)).first()

        _log.set_data(instance)

        if not instance:
            _log.status = "FAILURE"
            _log.error_message = "Bundle not found."
        else:
            _log.status = "SUCCESS"
            _log.message = "BackupBundle Retrieved."

        return _log  # Dont need to log this, so not using return_success()

    def get_all(self, repo_id: Optional[str] = None) -> BorgdroneEvent[List[BackupBundle]]:
        _log = BorgdroneEvent[List[BackupBundle]]()
        _log.event = "BundleManager.get_all"

        if repo_id:
            instances = db.session.query(BackupBundle).filter(BackupBundle.repo_id == repo_id).all()
        else:
            instances = (
                db.session.query(BackupBundle).join(Repository).filter(Repository.user_id == current_user.id).all()
            )

        _log.set_data(instances)
        return _log.return_success("Bundles Retrieved.")

    def create_bundle(self, **kwargs) -> BorgdroneEvent[BackupBundle]:
        _log = BorgdroneEvent[BackupBundle]()
        _log.event = "BundleManager.create_bundle"

        bundle = BackupBundle()
        bundle.repo_id = kwargs["repo_id"]
        bundle.cron_minute = kwargs["cron_minute"]
        bundle.cron_hour = kwargs["cron_hour"]
        bundle.cron_day = kwargs["cron_day"]
        bundle.cron_month = kwargs["cron_month"]
        bundle.cron_weekday = kwargs["cron_weekday"]
        bundle.comment = kwargs.get("comment", None)
        bundle.commit()
        _log.set_data(bundle)

        included_dirs: list = []
        exclude_dirs: list = []

        for key, value in kwargs.items():
            if key.startswith("includedir"):
                yaml_data: Dict[str, Any] = yaml.safe_load(value)
                yaml_data["bundle_id"] = bundle.id

                included_dirs.append(yaml_data.get("path"))

                bdm = BundleDirectoryManager()
                result_log = bdm.create_bundledirectory(**yaml_data)
                if result_log.status == "FAILURE":
                    bundle.delete()
                    return _log.return_failure(result_log.error_message)

            elif key.startswith("excludedir"):
                yaml_data: Dict[str, Any] = yaml.safe_load(value)
                yaml_data["bundle_id"] = bundle.id
                yaml_data["exclude"] = True

                exclude_dirs.append("--exclude")
                exclude_dirs.append(yaml_data.get("path"))

                bdm = BundleDirectoryManager()
                result_log = bdm.create_bundledirectory(**yaml_data)
                if result_log.status == "FAILURE":
                    bundle.delete()
                    return _log.return_failure(result_log.error_message)

        if not included_dirs:
            bundle.delete()
            return _log.return_failure("You must include at least one include directory.")

        # "--list",
        backup_command = BORG_CREATE_COMMAND.copy()
        backup_command.extend(exclude_dirs)
        backup_command.append(f"{bundle.repo.path}::{bundle.repo.name_format}")
        backup_command.extend(included_dirs)

        bundle.command_line = " ".join(backup_command)
        bundle.commit()

        return _log.return_success("Bundle created successfully.")

    def delete_bundle(self, bundle_id: int) -> BorgdroneEvent:
        _log = BorgdroneEvent()
        _log.event = "BundleManager.delete_bundle"

        result_log = self.get_one(bundle_id=bundle_id)

        if not (bundle := result_log.get_data()):
            return _log.not_found_message("Bundle")

        bundle.delete()

        return _log.return_success("Bundle deleted successfully.")

    def check_dir(self, path: str) -> BorgdroneEvent[List[str]]:
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

    def create_backup(self, bundle_id: int) -> BorgdroneEvent[None]:
        _log = BorgdroneEvent[None]()
        _log.event = "BundleManager.create_backup"

        result_log = self.get_one(bundle_id=bundle_id)  # get the bundle
        if not (bundle := result_log.get_data()):
            return _log.not_found_message("Bundle")

        if not bundle.command_line:
            return _log.return_failure("Bundle has no command line set.")

        bash.popen(bundle.command_line.split(" "))

        return _log.return_success("Backup created successfully.")


class BundleDirectoryManager:
    def __init__(self):
        pass

    def create_bundledirectory(self, **kwargs) -> BorgdroneEvent[Optional[BackupDirectory]]:
        _log = BorgdroneEvent[Optional[BackupDirectory]]()
        _log.event = "BundleDirectoryManager.create_bundledirectory"

        try:
            backup_directory = BackupDirectory()
            backup_directory.backupbundle_id = kwargs["bundle_id"]
            backup_directory.path = kwargs["path"]
            backup_directory.permissions = kwargs["permissions"]
            backup_directory.owner = kwargs["owner"]
            backup_directory.group = kwargs["group"]
            backup_directory.exclude = kwargs.get("exclude", False)
            backup_directory.commit()
            _log.set_data(backup_directory)

        except Exception as e:
            return _log.return_failure(str(e))

        return _log.return_success("Backup Directory created successfully.")
