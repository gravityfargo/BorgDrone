from typing import List, Optional

from flask_login import current_user

from borgdrone.borg import borg_runner
from borgdrone.extensions import db
from borgdrone.helpers.datahelpers import ISO8601_to_human
from borgdrone.logging import BorgdroneEvent
from borgdrone.logging import logger as log

from .models import Repository


class RepositoryManager:
    def __init__(self):
        pass

    def get_one(self, repo_id: Optional[int] = None, path: Optional[str] = None) -> BorgdroneEvent[Repository]:
        _log = BorgdroneEvent[Repository]()
        _log.event = "RepositoryManager.get_one"

        if repo_id is not None:
            instance = db.session.query(Repository).filter(Repository.id == repo_id).first()
        elif path is not None:
            instance = db.session.query(Repository).filter(Repository.path == path).first()
        else:
            instance = db.session.query(Repository).filter(Repository.user_id == current_user.id).first()

        if instance:
            _log.set_data(instance)

        return _log.return_success("Repository retrieved.")

    def get_all(self) -> BorgdroneEvent[List[Repository]]:
        _log = BorgdroneEvent[List[Repository]]()
        _log.event = "RepositoryManager.get_all"

        instances = db.session.query(Repository).filter(Repository.user_id == current_user.id).all()
        _log.set_data(instances)

        return _log.return_success(f"All of {current_user.username}'s repositories retrieved.")

    def get_last(self) -> BorgdroneEvent[Repository]:
        _log = BorgdroneEvent[Repository]()
        _log.event = "RepositoryManager.get_last"

        instance = (
            db.session.query(Repository)
            .filter(Repository.user_id == current_user.id)
            .order_by(Repository.id.desc())
            .first()
        )
        if not instance:
            return _log.return_failure("No repositories found.")

        _log.set_data(instance)

        return _log.return_success("Last repository retrieved.")

    def create_repo(self, path: str, encryption: str) -> BorgdroneEvent[Repository]:
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

        info_result_log = self.get_repository_info(path=path)
        if info_result_log.status == "FAILURE":
            return _log.return_failure(info_result_log.error_message)

        if not (repo := info_result_log.get_data()):
            message = "Failed to get repository info. This should not be possible here!"
            return _log.return_failure(message)

        repo.user_id = current_user.id
        repo.commit()

        _log.set_data(repo)
        return _log.return_success("Repository created.")

    def get_repository_info(self, path: str) -> BorgdroneEvent[Repository]:
        """Get information about a repository.

        Arguments:
            path -- Path to the repository.

        Returns:
            BorgdroneEvent[Repository] -- A BorgdroneEvent with an uncommited Repository instance as data.
        """
        _log = BorgdroneEvent[Repository]()
        _log.event = "RepositoryManager.get_repository_info"

        info_result_log = borg_runner.repository_info(path)
        if info_result_log.status == "FAILURE":
            # we want to pass the error code and message
            # to the user and for BORG_RETURN
            _log.error_code = info_result_log.error_code
            _log.error_message = info_result_log.error_message
            return _log.return_failure(info_result_log.error_message)

        if not (stats := info_result_log.get_data()):
            message = "Failed to get repository info."
            return _log.return_failure(message)

        instance = Repository()
        instance.id = stats["repository"]["id"]
        instance.path = stats["repository"]["location"]

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

    def delete_repo(self, repo_id: int) -> BorgdroneEvent[None]:
        _log = BorgdroneEvent[None]()
        _log.event = "RepositoryManager.delete_repo"

        # get the repository
        result_log = self.get_one(repo_id=repo_id)
        if not (instance := result_log.data):
            return _log.not_found_message("Repository")

        instance.delete()
        log.success("Repository deleted from borgdrone database.")

        # borg delete --force
        result_log = borg_runner.delete_repository(instance.path)
        if result_log.status == "FAILURE":
            return _log.return_failure(result_log.error_message)

        return _log.return_success("Repository deleted from filesystem.")

    def update_repository_info(
        self, repo_id: Optional[int] = None, path: Optional[str] = None
    ) -> BorgdroneEvent[None]:
        _log = BorgdroneEvent[None]()
        _log.event = "RepositoryManager.update_repository_info"

        result_log = self.get_one(repo_id=repo_id, path=path)
        if not result_log.data:
            return _log.not_found_message("Repository")

        instance = result_log.data

        result_log = self.get_repository_info(instance.path)
        if result_log.status == "FAILURE":
            return _log.return_failure(result_log.error_message)

        data = result_log.get_data()
        if not data:
            error_message = "Failed to get repository info. This should not be possible!"
            return _log.return_failure(error_message)

        instance.path = data.path
        instance.last_modified = data.last_modified
        instance.encryption_mode = data.encryption_mode
        instance.encryption_keyfile = data.encryption_keyfile
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

    def import_repo(self, path: str) -> BorgdroneEvent[Repository]:
        _log = BorgdroneEvent[Repository]()
        _log.event = "RepositoryManager.import_repo"

        instance = self.get_one(path=path)
        if instance.data:
            error_message = "Repo exists in the database already. Cannot import."
            return _log.return_failure(error_message)

        result_log = self.get_repository_info(path=path)
        if result_log.status == "FAILURE":
            # we want to pass the error code and message
            # to the user and for BORG_RETURN
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
