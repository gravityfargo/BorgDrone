from typing import Any, Dict

from sqlalchemy import select

from borgdrone.borg import BorgRunner as borg_runner
from borgdrone.bundles import BackupBundle
from borgdrone.bundles import BundleManager as bundle_manager
from borgdrone.extensions import db
from borgdrone.logging import BorgdroneEvent, logger
from borgdrone.repositories import Repository
from borgdrone.repositories import RepositoryManager as repository_manager
from borgdrone.types import OptInt, OptStr

from .models import Archive, OptArchive, OptListArchive


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


def delete_archive(archive_name: str) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "ArchivesManager.delete_archive"

    archive = get_one(archive_name=archive_name)
    if not archive:
        return _log.not_found_message("Archive")
    repository = archive.backupbundle.repo

    # run borg command
    result_log = borg_runner.delete_archive(repository.path, archive.name)
    if result_log.status == "FAILURE":
        return _log.return_failure(result_log.error_message)
    logger.success("Archive deleted from disk.")

    archive.delete()
    return _log.return_success("Archive deleted.")


def refresh_archive(archive_name: str) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "ArchivesManager.refresh_archive"

    archive = get_one(archive_name=archive_name)
    if not archive:
        return _log.not_found_message("Archive")

    # get parent repository
    repository = repository_manager.get_one(db_id=archive.backupbundle.repo_id)
    if not repository:
        return _log.not_found_message("Repository")

    # run borg command
    result_log = borg_runner.archive_info(repository.path, archive.name)
    if not (data := result_log.get_data()):
        return _log.return_failure(result_log.error_message)

    archive.update_from_dict(data)
    archive.commit()

    return _log.return_success("Archive updated.")


def __process_command(command: str) -> Dict[str, Any]:
    """
    This function should not need any error checking,
    as the command is already validated by borg itself.
    """
    # borg [common options] create [options] ARCHIVE [PATH...]
    bundle_data = {
        "exclude_paths": [],
        "include_paths": [],
        "repository_path": "",
        "archive_name": "",
    }

    # borg [common options] create [options] REPO::ARCHIVENAMEFORMAT [PATHS.....]
    # |_part1a____________|        |_part1b_____________________________________|
    # part1a = command.split("create")[0].strip().split(" ")
    part1b = command.split("create")[1]

    # [options] REPO::ARCHIVENAMEFORMAT [PATHS.....]
    # |_part2a_____|  |_part2b_____________________|
    part2a = part1b.split("::")[0].split(" ")
    part2b = part1b.split("::")[1].split(" ")

    bundle_data["repository_path"] = part2a[-1]
    bundle_data["name_format"] = part2b[0]

    # [options] REPO::ARCHIVENAMEFORMAT [PATHS.....]
    #           |_part3_______________|
    part3 = f"{bundle_data["repository_path"]}::{bundle_data["name_format"]}"

    # example part1b
    # --stats --exclude /exclude/path1 --exclude /exclude/path2
    #  REPO::ARCHIVENAME /include/path1 /include/path2

    # [options]  REPO::ARCHIVENAMEFORMAT [PATHS.....]
    # |_part4a__|                      |_part4b_____|
    part4a = part1b.split(part3)[0].strip().split(" ")
    part4b = part1b.split(part3)[1].strip().split(" ")

    exclude_paths = []
    include_paths = []
    for i, part in enumerate(part4a):
        if part == "--exclude":
            path = part4a[i + 1]
            exclude_paths.append(path)

    for part in part4b:
        include_paths.append(part)

    logger.debug(f"exclude paths: {" ".join(exclude_paths)}")
    logger.debug(f"include paths: {" ".join(include_paths)}")
    bundle_data["exclude_paths"] = exclude_paths
    bundle_data["include_paths"] = include_paths

    return bundle_data


def import_archives(repository: Repository) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "ArchivesManager.sync_archives_with_db"

    # Run borg command to list all archives
    result_log = borg_runner.list_archives(repository.path)
    if not (archives := result_log.get_data()):
        return _log.return_failure(result_log.error_message)

    logger.success(f"Found {len(archives)} archives.")

    for archive in archives:
        logger.success(f"Processing {archive['name']}", "yellow")
        bundle_data = __process_command(archive["command_line"])

        bundle_command = bundle_manager.parse_bundle_create_command(
            bundle_data["repository_path"],
            bundle_data["name_format"],
            bundle_data["exclude_paths"],
            bundle_data["include_paths"],
        )
        bundle_data["command_line"] = bundle_command

        bundle = bundle_manager.get_one(command_line=bundle_command)
        if bundle:
            logger.success("A bundle for this archive was found.")
        else:
            result_log = bundle_manager.create_bundle_from_command(repository, bundle_data)
            if not (bundle := result_log.get_data()):
                return _log.return_failure(result_log.error_message)

        result = borg_runner.archive_info(repository.path, archive["name"])
        if not (archive_data := result.get_data()):
            return _log.return_failure(f"Error processing archive {archive['name']}.")

        archive = Archive().update_from_dict(archive_data)
        bundle.archives.append(archive)
        bundle.commit()
        logger.success("Archive processed successfully.")

    return _log.return_success("Archives imported.")
