from typing import Optional

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

    def get_all(self) -> BorgdroneEvent[list[Repository]]:
        _log = BorgdroneEvent()
        _log.event = "RepositoryManager.get_all"

        instances = db.session.query(Repository).filter(Repository.user_id == current_user.id).all()
        _log.data = instances

        return _log.return_success("Repositories retrieved.")

    def get_last(self, user_id: int) -> Optional[Repository]:
        instance = Repository.query.filter_by(user_id=user_id).order_by(Repository.id.desc()).first()
        log.debug("RETRIEVED_LAST_REPOSITORY")
        return instance

    def create_repo(self, path: str, encryption: str) -> BorgdroneEvent:
        _log = BorgdroneEvent()
        _log.event = "RepositoryManager.create_repo"

        run_result_log = borg_runner.run("create_repo", path=path, encryption=encryption)
        if run_result_log.status == "FAILURE":
            log.error(run_result_log.error_code)
            return run_result_log

        info_result_log = self.get_repository_info(path=path)
        if info_result_log.status == "FAILURE":
            log.error(info_result_log.message)
            return info_result_log

        repo = info_result_log.get_data()
        if not repo:
            # this should not be possible
            _log.status = "FAILURE"
            _log.error_message = "Failed to get repository info. This should not be possible!"
            log.error(_log.error_message)
            return _log

        repo.user_id = current_user.id
        repo.commit()

        # Success
        _log.set_data(run_result_log.data)

        success = "Repository created."
        return _log.return_success(success)

    def get_repository_info(self, path: str) -> BorgdroneEvent[Repository]:
        _log = BorgdroneEvent[Repository]()
        _log.event = "RepositoryManager.get_repository_info"

        runner_result = borg_runner.run("get_repository_info", path=path)
        if runner_result.status == "FAILURE":
            log.error(runner_result.error_code)
            return runner_result

        stats = runner_result.get_data()
        if not stats:
            error_message = "Failed to get repository info. This should not be possible!"
            return _log.return_failure(error_message)

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

        success = "Repository info retrieved."
        return _log.return_success(success)

    def delete_repo(self, repo_id: int) -> BorgdroneEvent:
        _log = BorgdroneEvent()
        _log.event = "RepositoryManager.delete_repo"

        result_log = self.get_one(repo_id=repo_id)
        if not result_log.data:
            return _log.not_found_message("Repository")

        instance = result_log.data
        instance.delete()
        log.success("Repository deleted from borgdrone database.")

        result_log = borg_runner.run("delete_repo", path=instance.path)
        if result_log.status == "ERROR":
            return _log.return_failure(result_log.error_message)

        success = "Repository deleted from filesystem."
        return _log.return_success(success)

    def update_repository_info(self, repo_id: Optional[int] = None, path: Optional[str] = None) -> BorgdroneEvent:
        _log = BorgdroneEvent()
        _log.event = "RepositoryManager.update_repository_info"

        result_log = self.get_one(repo_id=repo_id, path=path)
        if not result_log.data:
            return _log.not_found_message("Repository")

        instance = result_log.data

        result_log = self.get_repository_info(instance.path)
        if result_log.status == "FAILURE":
            return result_log

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

        success = "Repository info updated."
        return _log.return_success(success)

    def import_repo(self, path: str) -> BorgdroneEvent:
        _log = BorgdroneEvent()
        _log.event = "RepositoryManager.import_repo"

        instance = self.get_one(path=path)
        if instance.data:
            error_message = "Repo exists in the database already. Cannot import."
            return _log.return_failure(error_message)

        result_log = self.get_repository_info(path=path)
        if result_log.status == "ERROR":
            return result_log

        instance = result_log.get_data()
        if not instance:
            return result_log

        instance.user_id = current_user.id
        instance.commit()

        success_message = "Repository imported to borgdrone"
        return _log.return_success(success_message)
