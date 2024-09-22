from typing import Optional

from flask_login import login_user, logout_user
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from borgdrone.extensions import db
from borgdrone.logging import BorgdroneEvent
from borgdrone.types import OptInt, OptStr

from .models import OptUsers, Users


def get_one(user_id: OptInt = None, username: OptStr = None, email: OptStr = None) -> BorgdroneEvent[OptUsers]:
    _log = BorgdroneEvent[OptUsers]()
    _log.event = "UserManager.get"

    instance = None
    if user_id is not None:
        stmt = select(Users).where(Users.id == user_id)
        instance = db.session.scalars(stmt).first()

    elif username is not None:
        stmt = select(Users).where(Users.username == username)
        instance = db.session.scalars(stmt).first()

    elif email is not None:
        stmt = select(Users).where(Users.email == email)
        instance = db.session.scalars(stmt).first()

    _log.set_data(instance)
    if not instance:
        _log.status = "FAILURE"
        _log.error_message = "User not found."
    else:
        _log.status = "SUCCESS"
        _log.message = "User Retrieved."

    return _log


def create(username: str, password: str, email: str = "user@example.com") -> BorgdroneEvent[Users]:
    _log = BorgdroneEvent[Users]()
    _log.event = "UserManager.create"
    user = Users()
    user.username = username
    user.password = generate_password_hash(password)
    user.email = email
    user.commit()
    _log.set_data(user)
    return _log.return_success("User created.")


def login(user: Users, password: str, remember: bool = False) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[Optional[Users]]()
    _log.event = "UserManager.login"

    if not check_password_hash(str(user.password), password):
        return _log.return_failure("Password incorrect.")

    login_user(user, remember=remember)
    return _log.return_success("User logged in.")


def logout() -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[Optional[Users]]()
    _log.event = "UserManager.logout"

    logout_user()

    return _log.return_success("User logged out.")


# def get_one(
#      user_id: Optional[int] = None, bundle_id: Optional[int] = None, repo_id: Optional[int] = None
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

# def get_all( user_id: Optional[int] = None, repo_id: Optional[int] = None) -> Optional[List[BackupBundle]]:
#     if user_id is not None:
#         instances = self._get_all_by("user_id", user_id)
#     elif repo_id is not None:
#         instances = self._get_all_by("repo_id", repo_id)
#     else:
#         instances = None

#     self.repo = instances
#     return instances

# def delete( bundle: Settings) -> None:
#     super()._delete(bundle)

# def delete_all( user_id: Optional[int] = None, repo_id: Optional[int] = None) -> bool:
#     if user_id is not None:
#         all_bundles = self._get_all_by("user_id", user_id)
#     elif repo_id is not None:
#         all_bundles = self._get_all_by("repo_id", repo_id)
#     else:
#         return False

#     for bundle in all_bundles:
#         self.delete(bundle)

#     return True
