from typing import List, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import db


class BackupBundle(db.Model):
    __tablename__ = "backupbundle"
    id: Mapped[int] = mapped_column(primary_key=True)

    # relationships
    ## child

    repo_id: Mapped[int] = mapped_column(ForeignKey("repository.id"))
    repo = relationship("Repository", back_populates="backupbundles")

    ## parent
    backupdirectories: Mapped[List["BackupDirectory"]] = relationship(
        "BackupDirectory", back_populates="backupbundle", cascade="all, delete"
    )
    archives = relationship("Archive", back_populates="backupbundle", cascade="all, delete")

    # Cron job settings
    cron_minute: Mapped[str] = mapped_column(default="*")
    cron_hour: Mapped[str] = mapped_column(default="*")
    cron_day: Mapped[str] = mapped_column(default="*")
    cron_month: Mapped[str] = mapped_column(default="*")
    cron_weekday: Mapped[str] = mapped_column(default="*")

    cron_human: Mapped[str] = mapped_column(default="Not set")
    last_backup: Mapped[str] = mapped_column(default="Never")

    # Archive options
    comment: Mapped[Optional[str]]
    command_line: Mapped[Optional[str]]

    def commit(self):
        db.session.add(self)
        db.session.commit()

    def add_to_session(self):
        db.session.add(self)

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class BackupDirectory(db.Model):
    __tablename__ = "backupdirectory"

    id: Mapped[int] = mapped_column(primary_key=True)

    # relationships
    ## child
    backupbundle_id: Mapped[int] = mapped_column(ForeignKey("backupbundle.id"))
    backupbundle = relationship("BackupBundle", back_populates="backupdirectories")

    # archives = db.relationship("Archive", backref="backupdirectory", lazy=True)

    path: Mapped[str]
    permissions: Mapped[str]
    owner: Mapped[str]
    group: Mapped[str]

    exclude: Mapped[bool] = mapped_column(default=False)

    def commit(self):
        db.session.add(self)
        db.session.commit()

    def add_to_session(self):
        db.session.add(self)
