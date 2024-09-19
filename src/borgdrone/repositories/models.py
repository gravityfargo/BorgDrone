from typing import Any, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from borgdrone.extensions import db


class Repository(db.Model):
    __tablename__ = "repository"

    # relationships
    ## child
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user = relationship("Users", back_populates="repositories")
    ## parent
    backupbundles = relationship("BackupBundle", back_populates="repo", cascade="all, delete")

    # RepositoryKey
    id: Mapped[str] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(unique=True)  # location
    last_modified: Mapped[Optional[str]]

    # EncryptionKey
    encryption_mode: Mapped[str]
    encryption_keyfile: Mapped[Optional[str]]

    # CacheKey
    cache_path: Mapped[Optional[str]]

    # CacheStatsKey
    total_chunks: Mapped[Optional[int]]  # Number of chunks
    total_unique_chunks: Mapped[Optional[int]]  # Number of unique chunks
    total_size: Mapped[Optional[int]]  # Total uncompressed size of all chunks multiplied with their reference counts
    total_csize: Mapped[
        Optional[int]
    ]  # Total compressed and encrypted size of all chunks multiplied with their reference counts
    unique_size: Mapped[Optional[int]]  # Uncompressed size of all chunks
    unique_csize: Mapped[Optional[int]]  # Compressed and encrypted size of all chunks

    # SecurityDirKey
    security_dir: Mapped[Optional[str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "last_modified": self.last_modified,
            "encryption_mode": self.encryption_mode,
            "encryption_keyfile": self.encryption_keyfile,
            "cache_path": self.cache_path,
            "total_chunks": self.total_chunks,
            "total_unique_chunks": self.total_unique_chunks,
            "total_size": self.total_size,
            "total_csize": self.total_csize,
            "unique_size": self.unique_size,
            "unique_csize": self.unique_csize,
            "security_dir": self.security_dir,
        }

    def commit(self) -> None:
        db.session.add(self)
        db.session.commit()

    def add_to_db(self) -> None:
        db.session.add(self)

    def delete(self) -> None:
        db.session.delete(self)
        db.session.commit()
