from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import Base, db
from borgdrone.logging import logger

OptBackupBundle = Optional["BackupBundle"]
ListBackupBundle = List["BackupBundle"]

OptBackupDirectory = Optional["BackupDirectory"]
ListBackupDirectory = List["BackupDirectory"]

association_table = Table(
    "association_table",
    Base.metadata,
    Column("backupbundle_id", ForeignKey("backupbundle.id", ondelete="CASCADE"), primary_key=True),
    Column("backupdirectory_id", ForeignKey("backupdirectory.id", ondelete="CASCADE"), primary_key=True),
)


class BackupBundle(db.Model):
    __tablename__ = "backupbundle"
    id: Mapped[int] = mapped_column(primary_key=True)

    # child relationships
    repo_id: Mapped[int] = mapped_column(ForeignKey("repository.id"))
    repo = relationship("Repository", back_populates="backupbundles")

    ## parent
    backupdirectories: Mapped[List["BackupDirectory"]] = relationship(
        secondary=association_table,
        back_populates="backupbundles",
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
    name_format: Mapped[Optional[str]]
    command_line: Mapped[Optional[str]]

    def commit(self):
        db.session.add(self)
        db.session.commit()

    def add_to_session(self):
        db.session.add(self)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        for directory in self.backupdirectories:
            if not directory.backupbundles:
                directory.delete()

    def update(self):
        db.session.commit()


class BackupDirectory(db.Model):
    __tablename__ = "backupdirectory"

    id: Mapped[int] = mapped_column(primary_key=True)

    # child relationships
    backupbundles: Mapped[List[BackupBundle]] = relationship(
        secondary=association_table,
        back_populates="backupdirectories",
    )

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

    def delete(self):
        db.session.delete(self)
        db.session.commit()
