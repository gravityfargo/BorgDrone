from typing import Optional

from flask_login import current_user
from sqlalchemy import select

from borgdrone.borg import BorgRunner as borg_runner
from borgdrone.extensions import db
from borgdrone.helpers.datahelpers import ISO8601_to_human
from borgdrone.logging import BorgdroneEvent, logger
from borgdrone.types import OptInt, OptStr

from .models import ListRepository, OptRepository, Repository


def get_one(db_id: OptInt = None, repo_id: OptStr = None, path: OptStr = None) -> OptRepository:
    stmt = None
    instance = None

    if db_id is not None:
        stmt = select(Repository).where(Repository.id == db_id)
    elif repo_id is not None:
        stmt = select(Repository).where(Repository.repo_id == repo_id)
    elif path is not None:
        stmt = select(Repository).where(Repository.path == path)

    if stmt is not None:
        instance = db.session.scalars(stmt).first()

    return instance


def get_all() -> Optional[ListRepository]:
    instances = None
    stmt = select(Repository).where(Repository.user_id == current_user.id)
    instances = list(db.session.scalars(stmt).all())

    return instances


def create_repo(path: str, encryption: str) -> BorgdroneEvent[Repository]:
    _log = BorgdroneEvent[Repository]()
    _log.event = "RepositoryManager.create_repo"

    # borg init
    init_result_log = borg_runner.create_repository(path, encryption)
    if init_result_log.status == "FAILURE":
        # we want to pass the error code and message
        # to the user and for BORG_RETURN
        _log.error_code = init_result_log.error_code
        _log.error_message = init_result_log.error_message
        return _log.return_failure(init_result_log.error_message)

    info_result_log = get_repository_info(path=path)
    if not (repo := info_result_log.get_data()):
        message = "Failed to get repository info. This should not be possible here!"
        return _log.return_failure(message)

    repo.user_id = current_user.id
    repo.commit()

    _log.set_data(repo)
    return _log.return_success("Repository created.")


def get_repository_info(path: str, passphrase: Optional[str] = None) -> BorgdroneEvent[Optional[Repository]]:
    """Get information about a repository.

    Arguments:
        path -- Path to the repository.

    Returns:
        BorgdroneEvent[Repository] -- A BorgdroneEvent with an uncommited Repository instance as data.
    """
    _log = BorgdroneEvent[Optional[Repository]]()
    _log.event = "RepositoryManager.get_repository_info"

    instance = get_one(path=path)
    if not instance:
        instance = Repository()
        instance.path = path
        instance.passphrase = passphrase
        logger.debug(f"Getting info for unmanaged repository: {path}", "yellow")
    else:
        logger.debug(f"Getting info for managed repository: {path}", "yellow")

    result_log = borg_runner.repository_info(instance.path, instance.passphrase)
    if not (stats := result_log.get_data()):
        if result_log.error_code == "Borg.PassphraseWrong":
            error_message = "Passphrase is wrong or was not provided."
        else:
            error_message = result_log.error_message

        return _log.return_failure(error_message)

    instance.repo_id = stats["repository"]["id"]

    date_str = stats["repository"]["last_modified"]
    instance.last_modified = ISO8601_to_human(date_str)
    instance.encryption_mode = stats["encryption"]["mode"]
    instance.encryption_keyfile = stats["encryption"].get("keyfile", None)
    instance.cache_path = stats["cache"]["path"]
    instance.total_chunks = stats["cache"]["stats"]["total_chunks"]
    instance.total_unique_chunks = stats["cache"]["stats"]["total_unique_chunks"]
    instance.total_size = stats["cache"]["stats"]["total_size"]
    instance.total_csize = stats["cache"]["stats"]["total_csize"]
    instance.unique_size = stats["cache"]["stats"]["unique_size"]
    instance.unique_csize = stats["cache"]["stats"]["unique_csize"]
    instance.security_dir = stats["security_dir"]

    _log.set_data(instance)
    return _log.return_success("Repository info retrieved.")


def delete_repo(db_id: int) -> BorgdroneEvent[None]:
    """Delete a repository from the database and filesystem.

    Arguments:
        db_id -- database id of the repository.

    Returns:
        BorgdroneEvent with no data.
    """
    _log = BorgdroneEvent[None]()
    _log.event = "RepositoryManager.delete_repo"

    # get the repository
    instance = get_one(db_id=db_id)
    if not instance:
        return _log.not_found_message("Repository")

    instance.delete()
    logger.success("Repository deleted from borgdrone database.")

    # borg delete --force
    # result_log = borg_runner.delete_repository(instance.path)
    # if result_log.status == "FAILURE":
    #     return _log.return_failure(result_log.error_message)

    return _log.return_success("Repository deleted from filesystem.")


def update_repository_info(
    db_id: OptInt = None, path: OptStr = None, passphrase: Optional[str] = None
) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "RepositoryManager.update_repository_info"

    instance = get_one(db_id=db_id, path=path)
    if not instance:
        return _log.not_found_message("Repository")

    result_log = get_repository_info(instance.path, instance.passphrase)
    if not (data := result_log.get_data()):
        if result_log.error_code == "Borg.PassphraseWrong":
            error_message = "Passphrase is wrong or was not provided."
        else:
            error_message = result_log.error_message

        return _log.return_failure(error_message)

    instance.path = data.path
    instance.last_modified = data.last_modified
    instance.encryption_mode = data.encryption_mode
    instance.encryption_keyfile = data.encryption_keyfile
    instance.passphrase = passphrase
    instance.cache_path = data.cache_path
    instance.total_chunks = data.total_chunks
    instance.total_unique_chunks = data.total_unique_chunks
    instance.total_size = data.total_size
    instance.total_csize = data.total_csize
    instance.unique_size = data.unique_size
    instance.unique_csize = data.unique_csize
    instance.security_dir = data.security_dir

    db.session.commit()

    return _log.return_success("Repository info updated.")


def import_repo(path: str, passphrase: Optional[str] = None) -> BorgdroneEvent[Repository]:
    _log = BorgdroneEvent[Repository]()
    _log.event = "RepositoryManager.import_repo"

    instance = get_one(path=path)
    if instance:
        error_message = "Repo exists in the database already. Cannot import."
        return _log.return_failure(error_message)

    result_log = get_repository_info(path=path, passphrase=passphrase)
    if result_log.status == "FAILURE":
        _log.error_code = result_log.error_code
        _log.error_message = result_log.error_message
        return _log.return_failure(result_log.error_message)

    if not (instance := result_log.get_data()):
        message = "Failed to get repository info."
        return _log.return_failure(message)

    instance.user_id = current_user.id
    instance.commit()

    _log.set_data(instance)
    return _log.return_success("Repository imported to borgdrone")
