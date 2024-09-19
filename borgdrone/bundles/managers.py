from typing import List, Optional

from flask_login import current_user

from borgdrone.extensions import db
from borgdrone.helpers import bash, datahelpers, filemanager
from borgdrone.logging import BorgdroneEvent
from borgdrone.logging import logger as log
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

    def get_one(self, bundle_id: Optional[int] = None, repo_id: Optional[int] = None) -> BorgdroneEvent[BackupBundle]:

        _log = BorgdroneEvent[BackupBundle]()
        _log.event = "BundleManager.get_one"

        if repo_id:
            instance = db.session.query(BackupBundle).filter(BackupBundle.repo_id == repo_id).first()
        elif bundle_id:
            instance = db.session.query(BackupBundle).filter(BackupBundle.id == bundle_id).first()
        else:
            instance = (
                db.session.query(BackupBundle).join(Repository).filter(Repository.user_id == current_user.id).first()
            )

        if instance:
            _log.set_data(instance)

        return _log.return_success("Bundle Retrieved.")

    def get_all(self, repo_id: Optional[int] = None) -> BorgdroneEvent[List[BackupBundle]]:
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

    def create_bundle(self, **kwargs) -> BorgdroneEvent:
        _log = BorgdroneEvent()
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

        bdm = BundleDirectoryManager()
        number_of_dirs = 0

        for key, value in kwargs.items():
            if key.startswith("includedir"):
                # bdm.create_bundledirectory(bundle_id=bundle.id, path=value)
                # number_of_dirs += 1
                print(key, value)
                print()

            elif key.startswith("excludedir"):
                pass
                # bdm.create_bundledirectory(bundle_id=bundle.id, path=value, exclude=True)

        if number_of_dirs == 0:
            bundle.delete()
            return _log.return_failure("You must include at least one include directory.")

        return _log.return_success("Bundle created successfully.")

    def delete_bundle(self, bundle_id: int) -> BorgdroneEvent:
        _log = BorgdroneEvent()
        _log.event = "BundleManager.delete_bundle"

        result_log = self.get_one(bundle_id=bundle_id)

        if not result_log or not result_log.data:
            return _log.return_failure("Bundle not found.")

        result_log.data.delete()

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


class BundleDirectoryManager:
    def __init__(self):
        pass

    # get_last

    def get_one(self, bundle_directory_id: int) -> None:
        pass

    def get_all(self, repo_id: Optional[int] = None, bundle_id: Optional[int] = None) -> None:
        pass

    def create_bundledirectory(self, bundle_id: int, path: str, exclude: bool = False, commit: bool = True) -> None:
        log.debug(
            f"Creating new bundle directory with bundle_id ({bundle_id}), path ({path}), and exclude ({exclude})"
        )
        bd = BackupDirectory()
        bd.backupbundle_id = bundle_id
        bd.path = path
        if exclude:
            bd.exclude = True

        if commit:
            bd.commit()
        else:
            bd.add_to_session()

    def delete_bundledirectory(self, repo_id: Optional[int] = None, bundle_id: Optional[int] = None) -> None:
        pass
