import json
import uuid
from datetime import datetime
from typing import Any, Optional, TypeVar

from borgdrone.database import CRUD

from .dataclasses import (
    BorgInfo,
    BorgLogMessage,
    CacheKey,
    CacheStatsKey,
    EncryptionKey,
    RepositoryKey,
)

BorgTypes = TypeVar("BorgTypes", BorgInfo, CacheKey, CacheStatsKey, EncryptionKey, RepositoryKey)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_unix_timestamp() -> float:
    now = datetime.now()
    return datetime.timestamp(now)


class BorgdroneLogMessage(CRUD):

    def __init__(
        self,
        sender: str,
        message: str,
        levelname: str = "INFO",
        status: str = "NOSTATUS",
        child_message_table=None,
    ):
        super().__init__(BorgdroneLogMessageModel)
        self.sender = sender
        self.message = message
        self.levelname = levelname
        self.status = status
        self.time = generate_unix_timestamp()
        self.child_message_table = child_message_table

    def update(self, **kwargs) -> None:
        super()._update(self, **kwargs)

    def commit(self) -> BorgdroneLogMessageModel:
        instance = self._create(
            sender=self.sender,
            message=self.message,
            time=self.time,
            levelname=self.levelname,
            status=self.status,
            child_message_table=self.child_message_table,
        )
        return instance
