from typing import Optional

from flask_login import login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from borgdrone.extensions import db
from borgdrone.logging import BorgdroneEvent

from .models import Users


class UserManager:
    def __init__(self):
        pass

    def create(self, username: str, password: str, email: str = "user@example.com") -> BorgdroneEvent[Users]:
        _log = BorgdroneEvent[Users]()
        _log.event = "UserManager.create"
        user = Users()
        user.username = username
        user.password = generate_password_hash(password)
        user.email = email
        user.commit()
        _log.set_data(user)
        return _log.return_success("User created.")

    def get(
        self, user_id: Optional[int] = None, username: Optional[str] = None, email: Optional[str] = None
    ) -> BorgdroneEvent[Optional[Users]]:
        _log = BorgdroneEvent[Optional[Users]]()
        _log.event = "UserManager.get"

        if user_id is not None:
            instance = db.session.query(Users).filter(Users.id == user_id).first()
        elif username is not None:
            instance = db.session.query(Users).filter(Users.username == username).first()
        elif email is not None:
            instance = db.session.query(Users).filter(Users.email == email).first()
        else:
            instance = None

        _log.set_data(instance)
        return _log.return_success("User retrieved.")

    def login(self, user: Users, password: str, remember: bool = False) -> BorgdroneEvent[None]:
        _log = BorgdroneEvent[Optional[Users]]()
        _log.event = "UserManager.login"

        if not check_password_hash(str(user.password), password):
            return _log.return_failure("Password incorrect.")

        login_user(user, remember=remember)
        return _log.return_success("User logged in.")

    def logout(self) -> BorgdroneEvent[None]:
        _log = BorgdroneEvent[Optional[Users]]()
        _log.event = "UserManager.logout"

        logout_user()

        return _log.return_success("User logged out.")

    # def get_one(
    #     self, user_id: Optional[int] = None, bundle_id: Optional[int] = None, repo_id: Optional[int] = None
    # ) -> Optional[Settings]:
    #     if bundle_id is not None:
    #         instance = self._get_one("id", bundle_id)
    #     elif user_id is not None:
    #         instance = self._get_one("user_id", user_id)
    #     elif repo_id is not None:
    #         instance = self._get_one("repo_id", repo_id)
    #     else:
    #         instance = None

    #     self.bundle = instance
    #     return instance

    # def get_all(self, user_id: Optional[int] = None, repo_id: Optional[int] = None) -> Optional[List[BackupBundle]]:
    #     if user_id is not None:
    #         instances = self._get_all_by("user_id", user_id)
    #     elif repo_id is not None:
    #         instances = self._get_all_by("repo_id", repo_id)
    #     else:
    #         instances = None

    #     self.repo = instances
    #     return instances

    # def delete(self, bundle: Settings) -> None:
    #     super()._delete(bundle)

    # def delete_all(self, user_id: Optional[int] = None, repo_id: Optional[int] = None) -> bool:
    #     if user_id is not None:
    #         all_bundles = self._get_all_by("user_id", user_id)
    #     elif repo_id is not None:
    #         all_bundles = self._get_all_by("repo_id", repo_id)
    #     else:
    #         return False

    #     for bundle in all_bundles:
    #         self.delete(bundle)

    #     return True
