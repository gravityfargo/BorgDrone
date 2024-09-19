from datetime import datetime
from typing import Any, Optional

from flask_login import current_user
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import db


def generate_unix_timestamp() -> float:
    now = datetime.now()
    return datetime.timestamp(now)


class BorgdroneLog(db.Model):
    """
    - `sender`:     "RepositoryManager.create_repo"
    - `message`:    "Invalid command or arguments."
    - `event`:      "BorgRunner.InvalidCommand"
    - `levelname`: (default: INFO) DEBUG, WARNING, ERROR, CRITICAL
    - `status`: SUCCESS, FAILURE
    """

    __tablename__ = "borgdrone_log"
    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user = relationship("Users", back_populates="borgdronelogs")

    level: Mapped[str] = mapped_column(default="NOLEVEL")
    message: Mapped[str]
    event: Mapped[str]
    time: Mapped[float] = mapped_column(default=generate_unix_timestamp)
    status: Mapped[str] = mapped_column(default="NOSTATUS")

    borg_log: Mapped[Optional["BorgLog"]] = relationship(back_populates="borgdronelog", cascade="all, delete")

    def commit(self) -> None:
        db.session.add(self)
        db.session.commit()

    def add_to_db(self) -> None:
        db.session.add(self)

    def set_borg_log(self, borg_log: "BorgLog") -> None:
        self.borg_log = borg_log
        borg_log.borgdronelog_id = self.id
        borg_log.user_id = current_user.id
        db.session.add(borg_log)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "message": self.message,
            "event": self.event,
            "time": self.time,
            "status": self.status,
        }


class BorgLog(db.Model):
    __tablename__ = "borg_log"
    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user = relationship("Users", back_populates="borglogs")

    type: Mapped[str]
    time: Mapped[float]
    levelname: Mapped[str]
    name: Mapped[str]
    message: Mapped[str]
    msgid: Mapped[str]

    borgdronelog_id: Mapped[int] = mapped_column(ForeignKey("borgdrone_log.id"))
    borgdronelog: Mapped["BorgdroneLog"] = relationship(back_populates="borg_log", single_parent=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "time": self.time,
            "levelname": self.levelname,
            "name": self.name,
            "message": self.message,
            "msgid": self.msgid,
        }

    def commit(self) -> None:
        db.session.add(self)
        db.session.commit()

    def add_to_db(self) -> None:
        db.session.add(self)
