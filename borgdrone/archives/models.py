import json
from typing import List, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import db

OptArchive = Optional["Archive"]
OptListArchive = Optional[List["Archive"]]
ListArchive = List["Archive"]


class Archive(db.Model):
    __tablename__ = "archive"
    id: Mapped[int] = mapped_column(primary_key=True)

    archive_id: Mapped[str]
    backupbundle_id: Mapped[int] = mapped_column(ForeignKey("backupbundle.id"))
    backupbundle = relationship("BackupBundle", back_populates="archives")

    name: Mapped[str]
    comment: Mapped[str]
    end: Mapped[str]
    hostname: Mapped[str]
    start: Mapped[str]
    tam: Mapped[Optional[str]]
    time: Mapped[Optional[str]]
    username: Mapped[str]

    command_line = Mapped[Optional[str]]
    duration: Mapped[Optional[str]]
    repository_id: Mapped[Optional[str]]
    stats_compressed_size: Mapped[Optional[str]]
    stats_deduplicated_size: Mapped[Optional[str]]
    stats_nfiles: Mapped[Optional[int]]
    stats_original_size: Mapped[Optional[str]]

    def commit(self):
        db.session.add(self)
        db.session.commit()

    def create_from_dict(self, data: dict) -> "Archive":
        """Expects raw output from `borg list --json`"""
        for key, value in data.items():
            setattr(self, key, value)
        return self
