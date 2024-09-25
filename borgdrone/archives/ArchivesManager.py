from sqlalchemy import select

from borgdrone.borg import BorgRunner as borg_runner
from borgdrone.bundles import BackupBundle
from borgdrone.bundles import BundleManager as bundle_manager
from borgdrone.extensions import db
from borgdrone.helpers import datahelpers
from borgdrone.logging import BorgdroneEvent, logger
from borgdrone.repositories import RepositoryManager as repository_manager
from borgdrone.types import OptInt, OptStr

from .models import Archive, ListArchive, OptArchive, OptListArchive


def get_one(
    db_id: OptInt = None, archive_id: OptStr = None, archive_name: OptStr = None
) -> BorgdroneEvent[OptArchive]:
    _log = BorgdroneEvent[OptArchive]()
    _log.event = "ArchivesManager.get_one"

    instance = None
    if db_id is not None:
        stmt = select(Archive).where(Archive.id == db_id)
        instance = db.session.scalars(stmt).first()

    elif archive_id is not None:
        stmt = select(Archive).where(Archive.archive_id == archive_id)
        instance = db.session.scalars(stmt).first()

    elif archive_name is not None:
        stmt = select(Archive).where(Archive.name == archive_name)
        instance = db.session.scalars(stmt).first()

    _log.set_data(instance)
    if not instance:
        _log.status = "FAILURE"
        _log.error_message = "Archive not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "Archive Retrieved."

    return _log


def get_all(repo_id: int) -> BorgdroneEvent[OptListArchive]:
    _log = BorgdroneEvent[OptListArchive]()
    _log.event = "ArchivesManager.get_all"

    stmt = select(Archive).join(BackupBundle).where(BackupBundle.repo_id == repo_id)
    instances = list(db.session.scalars(stmt).all())

    _log.set_data(instances)
    if not instances:
        _log.status = "FAILURE"
        _log.error_message = "Archives not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "Archives Retrieved."

    return _log


def refresh_archive(archive_name: str) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "ArchivesManager.refresh_archive"

    result_log = get_one(archive_id=archive_name)
    if not (archive := result_log.get_data()):
        return _log.not_found_message("Archive")

    # get parent repository
    result_log = repository_manager.get_one(db_id=archive.backupbundle.repo_id)
    if not (repository := result_log.get_data()):
        return _log.not_found_message("Repository")

    # run borg command
    result_log = borg_runner.borg_info(repository.path, archive.name)
    if not (data := result_log.get_data()):
        return _log.return_failure(result_log.error_message)

    info = data["archives"][0]
    stats = info["stats"]

    archive.duration = info["duration"]
    archive.stats_compressed_size = datahelpers.convert_bytes(stats["compressed_size"])
    archive.stats_deduplicated_size = datahelpers.convert_bytes(stats["deduplicated_size"])
    archive.stats_nfiles = stats["nfiles"]
    archive.stats_original_size = datahelpers.convert_bytes(stats["original_size"])
    archive.commit()

    return _log.return_success("Archive updated.")


def refresh_archives(repo_db_id: int, first: int = 0, last: int = 0) -> BorgdroneEvent[ListArchive]:
    _log = BorgdroneEvent[ListArchive]()
    _log.event = "ArchivesManager.get_all"

    # Get parent repository
    result_log = repository_manager.get_one(db_id=repo_db_id)
    if not (repository := result_log.get_data()):
        return _log.not_found_message("Repository")

    # Run borg command to list archives
    result_log = borg_runner.list_archives(repository.path, first, last)
    if not (archives := result_log.get_data()):
        return _log.return_failure(result_log.error_message)

    # Update database with new archives
    for archive in archives:
        # Check if the archive exists
        result_log = get_one(archive_id=archive["id"])
        if result_log.status == "SUCCESS" and (instance := result_log.get_data()):
            refresh_archive(instance.name)
            continue

        # Parse command line and create or find bundle
        command_line = " ".join(archive["command_line"].split())
        result_log = bundle_manager.get_or_create_bundle_from_command(repo_db_id, command_line)
        if not (bundle := result_log.get_data()):
            continue

        # Create and link the archive to the bundle
        instance = Archive()
        instance.archive_id = archive["id"]
        instance.name = archive["name"]
        instance.comment = archive["comment"]
        instance.end = archive["end"]
        instance.hostname = archive["hostname"]
        instance.start = archive["start"]
        instance.tam = archive["tam"]
        instance.time = archive["time"]
        instance.username = archive["username"]

        bundle.archives.append(instance)
        instance.commit()

        refresh_archive(instance.name)

    return _log.return_success("Archives retrieved.")
