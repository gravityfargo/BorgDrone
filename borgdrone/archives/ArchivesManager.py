from sqlalchemy import select

from borgdrone.borg import BorgRunner as borg_runner
from borgdrone.bundles import BackupBundle
from borgdrone.bundles import BundleManager as bundle_manager
from borgdrone.extensions import db
from borgdrone.logging import BorgdroneEvent, logger
from borgdrone.repositories import RepositoryManager as repository_manager
from borgdrone.types import OptInt, OptStr

from .models import Archive, ListArchive, OptArchive, OptListArchive


def get_one(db_id: OptInt = None, archive_id: OptStr = None, archive_name: OptStr = None) -> OptArchive:
    instance = None
    stmt = None
    if db_id is not None:
        stmt = select(Archive).where(Archive.id == db_id)
    elif archive_id is not None:
        stmt = select(Archive).where(Archive.archive_id == archive_id)
    elif archive_name is not None:
        stmt = select(Archive).where(Archive.name == archive_name)

    if stmt is not None:
        instance = db.session.scalars(stmt).first()

    return instance


def get_all(repo_id: int) -> OptListArchive:
    stmt = select(Archive).join(BackupBundle).where(BackupBundle.repo_id == repo_id)
    instances = list(db.session.scalars(stmt).all())
    return instances


def refresh_archive(archive_name: str) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "ArchivesManager.refresh_archive"

    archive = get_one(archive_name=archive_name)
    if not archive:
        return _log.not_found_message("Archive")

    # get parent repository
    repository = repository_manager.get_one(db_id=archive.backupbundle.repo_id)
    if not repository:  # this should not be possible
        return _log.not_found_message("Repository")

    # run borg command
    result_log = borg_runner.archive_info(repository.path, archive.name)
    if not (data := result_log.get_data()):
        return _log.return_failure(result_log.error_message)

    archive.update_from_dict(data)
    archive.commit()

    return _log.return_success("Archive updated.")


# def refresh_archives(repo_db_id: int, first: int = 0, last: int = 0) -> BorgdroneEvent[ListArchive]:


#     # Update database with new archives

#         # Check if the archive exists
#         result_log = get_one(archive_id=archive["id"])
#         if result_log.status == "SUCCESS" and (instance := result_log.get_data()):
#             refresh_archive(instance.name)
#             continue

#         # Parse command line and create or find bundle
#         command_line = " ".join(archive["command_line"].split())
#         result_log = bundle_manager.get_or_create_bundle_from_command(repo_db_id, command_line)
#         if not (bundle := result_log.get_data()):
#             continue

#         # Create and link the archive to the bundle
#         instance = Archive()
#         instance.archive_id = archive["id"]
#         instance.name = archive["name"]
#         instance.comment = archive["comment"]
#         instance.end = archive["end"]
#         instance.hostname = archive["hostname"]
#         instance.start = archive["start"]
#         instance.tam = archive["tam"]
#         instance.time = archive["time"]
#         instance.username = archive["username"]

#         bundle.archives.append(instance)
#         instance.commit()

#         refresh_archive(instance.name)

#     return _log.return_success("Archives retrieved.")


def sync_archives_with_db(repo_db_id: int):
    _log = BorgdroneEvent[None]()
    _log.event = "ArchivesManager.sync_archives_with_db"

    # get parent repository
    repository = repository_manager.get_one(db_id=repo_db_id)
    if not repository:  # this should not be possible
        return _log.not_found_message("Repository")

    # Run borg command to list archives
    result_log = borg_runner.list_archives(repository.path)
    if not (archives := result_log.get_data()):
        return _log.return_failure(result_log.error_message)

    for archive in archives:
        logger.error(archive["name"])
