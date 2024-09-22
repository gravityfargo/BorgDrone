from typing import List, Optional

from flask_login import current_user
from sqlalchemy import select

from borgdrone.borg import BorgRunner
from borgdrone.bundles import BackupBundle, BundleManager
from borgdrone.extensions import db
from borgdrone.logging import BorgdroneEvent
from borgdrone.repositories import Repository, RepositoryManager

from .models import Archive


class ArchivesManager:
    def __init__(self):
        pass

    def get_one(self, archive_id: str) -> BorgdroneEvent[Optional[Archive]]:
        _log = BorgdroneEvent[Optional[Archive]]()
        _log.event = "ArchivesManager.get_one"

        instance = db.session.scalars(select(Archive).where(Archive.id == archive_id)).first()

        _log.set_data(instance)
        if not instance:
            _log.status = "FAILURE"
            _log.error_message = "Archive not found."
        else:
            _log.status = "SUCCESS"
            _log.message = "Archive Retrieved."

        return _log  # Dont need to log this, so not using return_success()

    def get_all(self, repo_id: Optional[str] = None) -> BorgdroneEvent[List[Archive]]:
        _log = BorgdroneEvent[List[Archive]]()
        _log.event = "ArchivesManager.get_all"

        if repo_id:
            instances = db.session.query(Archive).join(BackupBundle).filter(BackupBundle.repo_id == repo_id).all()
        else:
            instances = (
                db.session.query(Archive)
                .join(BackupBundle)
                .join(Repository)
                .filter(Repository.user_id == current_user.id)
                .all()
            )

        _log.set_data(instances)
        return _log.return_success("Archives Retrieved.")

    def get_archives(self, repo_id: str, number_of_archives: int = 0) -> BorgdroneEvent[List[Archive]]:
        _log = BorgdroneEvent[List[Archive]]()
        _log.event = "ArchivesManager.get_all"

        # get the asociated repository
        get_repo_log = RepositoryManager().get_one(repo_id)
        if not (repository := get_repo_log.get_data()):
            return _log.not_found_message("Repository")
        # run borg command
        list_archives_log = BorgRunner().list_archives(repository.path, number_of_archives)
        if not (archives := list_archives_log.get_data()):
            _log.status = "FAILURE"
            _log.error_code = list_archives_log.error_code
            _log.error_message = list_archives_log.error_message
            return _log

        # update db
        for archive in archives:

            # check if archive exists, skip if it does
            get_archive_log = self.get_one(archive_id=archive["id"])  # get the bundle
            if get_archive_log.get_data():
                continue

            # ensure command_line is a list
            command_line = archive["command_line"]
            if isinstance(command_line, str):
                command_line = command_line.split()

            # replace the borg binary path with the command
            command_line[0] = "borg"
            command = " ".join(archive["command_line"])

            # check if bundle exists
            get_bundle_log = BundleManager().get_one(command_line=command)  # get the bundle
            if bundle := get_bundle_log.get_data():
                # create the archive and associate it with the bundle
                instance = Archive()
                instance.backupbundle_id = bundle.id
                instance.id = archive["id"]
                instance.name = archive["name"]
                instance.command_line = command
                instance.comment = archive["comment"]
                instance.end = archive["end"]
                instance.hostname = archive["hostname"]
                instance.start = archive["start"]
                instance.tam = archive["tam"]
                instance.time = archive["time"]
                instance.commit()

        return _log.return_success("Archives retrieved.")

    # def update_archives_db(self, repo_path: str) -> BorgdroneEvent[None]:
    #     _log = BorgdroneEvent[None]()
    #     _log.event = "ArchivesManager.update_archives_db"

    #     result_log = BorgRunner().get_archives(repo_path)

    #     log.success(result_log.message)
    #     log.error(result_log.error_message)

    #     return _log.return_success("Archives updated.")

    # archive = {
    #     "archive": "desktop-manjaro-nathan-2024-09-20T16:36:22",
    #     "barchive": "desktop-manjaro-nathan-2024-09-20T16:36:22",
    #     "command_line": [
    #         "/usr/bin/borg",
    #         "create",
    #         "--list",
    #         "--stats",
    #         "/tmp/borgdrone::{hostname}-{user}-{now}",
    #         "/home/nathan/Downloads",
    #     ],
    #     "comment": "",
    #     "end": "2024-09-20T16:36:22.000000",
    #     "hostname": "desktop-manjaro",
    #     "id": "94e0c98df697b42a653575ae6b0bc3a4f82979a11d3b77ddba64e59dd22bf2dd",
    #     "name": "desktop-manjaro-nathan-2024-09-20T16:36:22",
    #     "start": "2024-09-20T16:36:22.000000",
    #     "tam": "verified",
    #     "time": "2024-09-20T16:36:22.000000",
    #     "username": "nathan",
    # }
