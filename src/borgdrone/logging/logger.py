"""
stacklevel=2 tells the logger to look one stack frame up to find the correct module name and line number
rather than reporting this file and line number.
"""

from logging import getLogger

from flask import current_app as app


def success(message):
    app.logger.info(message, stacklevel=2)


def error(message):
    app.logger.error(message, stacklevel=2)


def debug(message):
    if app.config.get("PYTESTING", False):
        return
    app.logger.debug(message, stacklevel=2)


def warning(message):
    app.logger.warning(message, stacklevel=2)


def critical(message):
    app.logger.critical(message, stacklevel=2)


def exception(message):
    app.logger.exception(message, stacklevel=2)


def borg_log(message):
    if app.config.get("PYTESTING", False):
        return

    borgcreate_logger = getLogger("borg")
    borgcreate_logger.info(message, stacklevel=2)


def borg_temp_log(message):
    if app.config.get("PYTESTING", False):
        return

    borgcreate_logger = getLogger("borg")
    borgcreate_logger.debug(message, stacklevel=2)
