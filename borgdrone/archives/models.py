from typing import List, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import db

OptArchive = Optional["Archive"]
OptListArchive = Optional[List["Archive"]]
ListArchive = List["Archive"]


class Archive(db.Model):
    __tablename__ = "archive"
    id: Mapped[str] = mapped_column(primary_key=True)

    backupbundle_id: Mapped[int] = mapped_column(ForeignKey("backupbundle.id"))
    backupbundle = relationship("BackupBundle", back_populates="archives")

    name: Mapped[str]
    command_line: Mapped[str]
    comment: Mapped[str]
    end: Mapped[str]
    hostname: Mapped[str]
    start: Mapped[str]
    tam: Mapped[str]
    time: Mapped[str]

    def commit(self):
        db.session.add(self)
        db.session.commit()
