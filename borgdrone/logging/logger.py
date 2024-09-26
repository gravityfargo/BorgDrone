from logging import getLogger
from typing import Any, Optional

from flask import current_app as app

from .config import COLOR


def success(message: Any, color: Optional[str] = None) -> None:
    """proxies app.logger.info

    colors: `red`, `green`, `yellow`, `cyan`, `purple`
    """
    if color:
        if COLOR.get(color):
            message = f"{COLOR[color]}{message}{COLOR['off']}"

    app.logger.info(message, stacklevel=2)


def error(message: Any) -> None:
    """proxies app.logger.error"""
    app.logger.error(message, stacklevel=2)


def warning(message: Any) -> None:
    """proxies app.logger.warning"""
    # An additional stacklevel is needed so log.error will show the caller of this module
    app.logger.warning(message, stacklevel=2)


def critical(message: Any) -> None:
    """proxies app.logger.critical"""
    # An additional stacklevel is needed so log.error will show the caller of this module
    app.logger.critical(message, stacklevel=2)


def exception(message: Any) -> None:
    """proxies app.logger.exception"""
    # An additional stacklevel is needed so log.error will show the caller of this module
    app.logger.exception(message, stacklevel=2)


def debug(message: Any, color: Optional[str] = None) -> None:
    """proxies app.logger.debug

    colors: `red`, `green`, `yellow`, `cyan`, `purple`
    """
    if color:
        if COLOR.get(color):
            message = f"{COLOR[color]}{message}{COLOR['off']}"

    app.logger.debug(message, stacklevel=2)


def success_event(message: Any) -> None:
    app.logger.info(message, stacklevel=3)


def error_event(message: Any) -> None:
    app.logger.error(message, stacklevel=3)


def debug_event(message: Any, color: Optional[str] = None) -> None:
    if color:
        if COLOR.get(color):
            message = f"{COLOR[color]}{message}{COLOR['off']}"

    app.logger.debug(message, stacklevel=4)


def borg_log(message: Any) -> None:
    """Logger for borg messages

    Logs messages to `instance/logs/borg.log` via the borg logger

    If the environment variable PYTESTING is set to True, the message will not be logged.
    """
    if app.config["PYTESTING"] == "True":
        return

    borgcreate_logger = getLogger("borg")
    borgcreate_logger.info(message, stacklevel=2)


def borg_temp_log(message: Any) -> None:
    """proxies app.logger.error"""
    # An additional stacklevel is needed so log.error will show the caller of this module
    if app.config["PYTESTING"] == "True":
        return

    borg_logger = getLogger("borg")
    borg_logger.debug(message, stacklevel=2)


# def process_borg_temp_log(target_file: str) -> None:
#     logs_path = app.config.get("LOGS_DIR")
#     log_file = f"{logs_path}/borg_temp.log"
