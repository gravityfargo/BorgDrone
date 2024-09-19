from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import db


class Archive(db.Model):
    __tablename__ = "archive"
    id: Mapped[int] = mapped_column(primary_key=True)

    # relationships
    ## child
    backupbundle_id: Mapped[int] = mapped_column(ForeignKey("backupbundle.id"))
    backupbundle = relationship("BackupBundle", back_populates="archives")

    end: Mapped[int]  # end timestamp
    duration: Mapped[float]  # duration in seconds
    command_line: Mapped[str]  # Array of strings of the command line that created the archive.
    chunker_params: Mapped[str]  # The chunker parameters the archive has been created with.
    hostname: Mapped[str] = mapped_column(default="")  # Hostname of the creating host
    username: Mapped[str] = mapped_column(default="")  # Name of the creating user
    comment: Mapped[str] = mapped_column(default="")  # Archive comment, if any

    # ArchiveStatsKey:
    original_size: Mapped[int]  # Size of files and metadata before compression
    compressed_size: Mapped[int]  # Size after compression
    deduplicated_size: Mapped[int]  # Size after deduplication
    nfiles: Mapped[int]  # Number of regular files in the archive

    # ArchiveLimitsKey:
    # Float between 0 and 1 describing how large this archive is relative to the maximum size allowed by Borg
    max_archive_size: Mapped[float]
