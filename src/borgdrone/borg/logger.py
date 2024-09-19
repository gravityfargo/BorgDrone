from typing import Optional

from flask_login import current_user

from borgdrone.extensions import db

from .models import BorgLog, BorgdroneLog


def info(
    message: str,
    event: str,
    level: str = "INFO",
    status: str = "NOSTATUS",
    borg_log: Optional[BorgLog] = None,
) -> BorgdroneLog:
    bl = BorgdroneLog()
    bl.user_id = current_user.id

    bl.level = level
    bl.message = message
    bl.event = event
    bl.status = status
    bl.borg_log = borg_log

    db.session.add(bl)
    db.session.commit()
    return bl


def error(
    event: str,
    message: str,
    borg_log: Optional[BorgLog] = None,
) -> BorgdroneLog:
    bl = info(
        event=event,
        message=message,
        level="INFO",
        status="FAILURE",
        borg_log=borg_log,
    )
    return bl


def success(
    event: str,
    message: str,
    borg_log: Optional[BorgLog] = None,
) -> BorgdroneLog:
    bl = info(
        event=event,
        message=message,
        level="INFO",
        status="SUCCESS",
        borg_log=borg_log,
    )
    return bl


def debug(
    event: str,
    message: str,
    borg_log: Optional[BorgLog] = None,
) -> BorgdroneLog:
    bl = info(
        event=event,
        message=message,
        level="DEBUG",
        status="NOSTATUS",
        borg_log=borg_log,
    )
    return bl
