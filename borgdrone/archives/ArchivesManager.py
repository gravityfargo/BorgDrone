from flask_login import current_user
from sqlalchemy import select

from borgdrone.borg import BorgRunner
from borgdrone.bundles import BackupBundle, BundleManager
from borgdrone.extensions import db
from borgdrone.logging import BorgdroneEvent
from borgdrone.repositories import Repository
from borgdrone.repositories import RepositoryManager as repo_manager
from borgdrone.types import OptStr

from .models import Archive, ListArchive, OptArchive, OptListArchive


def get_one(archive_id: OptStr) -> BorgdroneEvent[OptArchive]:
    _log = BorgdroneEvent[OptArchive]()
    _log.event = "ArchivesManager.get_one"

    stmt = select(Archive).where(Archive.id == archive_id)
    instance = db.session.scalars(stmt).first()

    _log.set_data(instance)
    if not instance:
        _log.status = "FAILURE"
        _log.error_message = "Archive not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "Archive Retrieved."

    return _log


def get_all(repo_id: OptStr = None) -> BorgdroneEvent[OptListArchive]:
    _log = BorgdroneEvent[OptListArchive]()
    _log.event = "ArchivesManager.get_all"

    instances = None
    if repo_id:
        stmt = select(Archive).join(BackupBundle).where(BackupBundle.repo_id == repo_id)
        instances = list(db.session.scalars(stmt).all())
    else:
        stmt = select(Archive).join(BackupBundle).join(Repository).where(Repository.user_id == current_user.id)
        instances = list(db.session.scalars(stmt).all())

    _log.set_data(instances)
    if not instances:
        _log.status = "FAILURE"
        _log.error_message = "Archives not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "Archives Retrieved."

    return _log


def get_archives(repo_id: str, number_of_archives: int = 0) -> BorgdroneEvent[ListArchive]:
    _log = BorgdroneEvent[ListArchive]()
    _log.event = "ArchivesManager.get_all"

    # get the asociated repository
    get_repo_log = repo_manager.get_one(repo_id)
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
        get_archive_log = get_one(archive_id=archive["id"])  # get the bundle
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


# def update_archives_db( repo_path: str) -> BorgdroneEvent[None]:
#     _log = BorgdroneEvent[None]()
#     _log.event = "ArchivesManager.update_archives_db"

#     result_log = BorgRunner().get_archives(repo_path)

#     log.success(result_log.message)
#     log.error(result_log.error_message)

#     return _log.return_success("Archives updated.")
