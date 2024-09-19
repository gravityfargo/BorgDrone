from typing import Optional

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import db


class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)

    # relationships
    ## parent
    settings = relationship("Settings", back_populates="user", cascade="all, delete")
    borgdronelogs = relationship("BorgdroneLog", back_populates="user", cascade="all, delete")
    borglogs = relationship("BorgLog", back_populates="user", cascade="all, delete")
    repositories = relationship("Repository", back_populates="user", cascade="all, delete")

    username: Mapped[str]
    password: Mapped[str]
    email: Mapped[Optional[str]]
