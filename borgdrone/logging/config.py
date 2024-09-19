import atexit
from logging import (
    DEBUG,
    ERROR,
    INFO,
    WARNING,
    Filter,
    StreamHandler,
    getHandlerByName,
    getLogger,
)
from logging.config import dictConfig
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from queue import Queue
from typing import List, Union

from flask import current_app as app
from flask.logging import default_handler

# Color constants
Color_Off = "\033[0m"
Red = "\033[0;31m"
Green = "\033[0;32m"
Yellow = "\033[0;33m"
Cyan = "\033[0;36m"
Purple = "\033[0;35m"


class InfoOnlyFilter(Filter):
    def filter(self, record):
        return record.levelno == INFO


class WarningOnlyFilter(Filter):
    def filter(self, record):
        return record.levelno == WARNING


class ErrorOnlyFilter(Filter):
    def filter(self, record):
        return record.levelno == ERROR


class DebugOnlyFilter(Filter):
    def filter(self, record):
        return record.levelno == DEBUG


def validate_handlers(handlers) -> List[Union[StreamHandler, RotatingFileHandler]]:
    """
    Validate that all the required handlers are properly instantiated.
    """
    for handler in handlers:
        if not isinstance(handler, (StreamHandler, RotatingFileHandler)):
            raise ValueError(f"{handler._name} is not a valid Handler")  # pylint: disable=protected-access

    return handlers


def apply_filters(handlers, filters) -> None:
    """
    Apply filters to the handlers.
    """
    # pylint: disable=protected-access

    for handler in handlers:
        if handler._name == "log_file":
            continue

        handler.addFilter(filters[handler._name])


def setup_queues(
    borgdrone_handlers: List[Union[StreamHandler, RotatingFileHandler]],
    borg_handlers: List[Union[StreamHandler, RotatingFileHandler]],
) -> None:
    """
    Sets up the queue logging to handle logs asynchronously.
    """

    log_queue_1 = Queue()
    borgdrone_queue_handler = QueueHandler(log_queue_1)
    borgdrone_queue_listener = QueueListener(log_queue_1, *borgdrone_handlers, respect_handler_level=True)

    root_logger = getLogger()
    root_logger.setLevel(DEBUG)
    root_logger.addHandler(borgdrone_queue_handler)
    root_logger.propagate = False

    log_queue_2 = Queue()
    borg_queue_handler = QueueHandler(log_queue_2)
    borg_queue_listener = QueueListener(log_queue_2, *borg_handlers, respect_handler_level=True)

    borgcreate_logger = getLogger("borg")  # did not create in the dictConfig
    borgcreate_logger.setLevel(DEBUG)
    borgcreate_logger.addHandler(borg_queue_handler)
    borgcreate_logger.propagate = False

    borgdrone_queue_listener.start()
    borg_queue_listener.start()

    atexit.register(borgdrone_queue_listener.stop)
    atexit.register(borg_queue_listener.stop)


def configure_logging() -> None:
    """
    Main function to configure logging by combining formatters, handlers, and queue logging.
    """
    app.logger.removeHandler(default_handler)  # for when dev mode restarts the app

    logs_path = app.config.get("LOGS_DIR")
    log_file = f"{logs_path}/borgdrone.log"

    borg_log_file = f"{logs_path}/borg.log"
    borg_temp_log_file = f"{logs_path}/borg_temp.log"

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "info": {"format": f"{Green}[Success]{Color_Off} %(message)s"},
            "warning": {"format": f"{Yellow}[%(levelname)-s]{Color_Off} %(message)s"},
            "error": {"format": f"{Red}[%(levelname)-s]{Color_Off} %(message)s"},
            "debug": {"format": f"{Purple}[%(levelname)-s]{Color_Off} %(message)s"},
            "default": {
                "format": "[%(asctime)s] %(levelname)-8s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "borg_temp": {
                "format": "%(message)s",
            },
            "borg": {
                "format": "[%(asctime)s]: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "info_console": {
                "class": "logging.StreamHandler",
                "level": INFO,
                "formatter": "info",
                "stream": "ext://flask.logging.wsgi_errors_stream",
            },
            "warning_console": {
                "class": "logging.StreamHandler",
                "level": WARNING,
                "formatter": "warning",
                "stream": "ext://flask.logging.wsgi_errors_stream",
            },
            "error_console": {
                "class": "logging.StreamHandler",
                "level": ERROR,
                "formatter": "error",
                "stream": "ext://flask.logging.wsgi_errors_stream",
            },
            "debug_console": {
                "class": "logging.StreamHandler",
                "level": DEBUG,
                "formatter": "debug",
                "stream": "ext://flask.logging.wsgi_errors_stream",
            },
            "log_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": DEBUG,
                "formatter": "default",
                "filename": log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 3,
            },
            "borg_log_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": INFO,
                "formatter": "borg",
                "filename": borg_log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 3,
            },
            "borg_temp_log_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": DEBUG,
                "formatter": "borg_temp",
                "filename": borg_temp_log_file,
            },
        },
    }

    dictConfig(log_config)

    borg_handlers = [
        getHandlerByName("borg_log_file"),
        getHandlerByName("borg_temp_log_file"),
    ]

    # using different levels for the handlers so I don't need to create a queue for each handler
    borg_filters = {
        "borg_log_file": InfoOnlyFilter(),
        "borg_temp_log_file": DebugOnlyFilter(),
    }

    borgdrone_handlers = [
        getHandlerByName("info_console"),
        getHandlerByName("warning_console"),
        getHandlerByName("error_console"),
        getHandlerByName("debug_console"),
        getHandlerByName("log_file"),
    ]

    borgdrone_filters = {
        "info_console": InfoOnlyFilter(),
        "warning_console": WarningOnlyFilter(),
        "error_console": ErrorOnlyFilter(),
        "debug_console": DebugOnlyFilter(),
    }

    try:
        borg_handlers = validate_handlers(borg_handlers)
        borgdrone_handlers = validate_handlers(borgdrone_handlers)
    except ValueError as e:
        print(e)
        return

    apply_filters(borgdrone_handlers, borgdrone_filters)
    apply_filters(borg_handlers, borg_filters)

    setup_queues(borgdrone_handlers, borg_handlers)

    getLogger("werkzeug").disabled = True
