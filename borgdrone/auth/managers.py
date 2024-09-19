from typing import Optional

from flask_login import login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..database import CRUD
from .models import Users


class UserManager(CRUD):
    def __init__(self):
        super().__init__(Users)

    def create(self, username: str, password: str) -> Users:
        user = self._create(username=username, password=generate_password_hash(password))
        return user

    def get(
        self, user_id: Optional[int] = None, username: Optional[str] = None, email: Optional[str] = None
    ) -> Optional[Users]:
        if user_id is not None:
            instance = self._get_one("id", user_id)
        elif username is not None:
            instance = self._get_one("username", username)
        elif email is not None:
            instance = self._get_one("email", email)
        else:
            return None
        return instance

    def login(self, user: Users, password: str, remember: bool = False) -> bool:
        if not check_password_hash(str(user.password), password):
            # print("Password incorrect.")
            return False

        login_user(user, remember=remember)
        return True

    def logout(self) -> None:
        logout_user()

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
