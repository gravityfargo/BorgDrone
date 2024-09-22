from typing import Optional

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import db

OptUsers = Optional["Users"]


class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)

    # relationships
    ## parent
    settings = relationship("Settings", back_populates="user", cascade="all, delete")
    repositories = relationship("Repository", back_populates="user", cascade="all, delete")

    username: Mapped[str]
    password: Mapped[str]
    email: Mapped[Optional[str]]

    def commit(self):
        db.session.add(self)
        db.session.commit()
