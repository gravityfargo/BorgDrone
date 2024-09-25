import json
from typing import Any, Dict, List

from borgdrone.helpers import bash
from borgdrone.logging import BorgdroneEvent, logger
from borgdrone.types import OptStr

from .constants import (
    BORG_DELETE_COMMAND,
    BORG_INFO_COMMAND,
    BORG_INIT_COMMAND,
    BORG_LIST_COMMAND,
)


def __process_error(result_log: BorgdroneEvent, error: str) -> BorgdroneEvent:
    result_log.status = "FAILURE"

    if "usage: borg" in error:
        lines = error.split("\n")
        error_line = lines[-2]

        if "argument -e/--encryption" in error_line:
            result_log.error_message = error_line
        else:
            result_log.error_message = "Invalid command or arguments."

    else:
        e: dict = json.loads(error)
        result_log.error_message = e.get("message", "Unknown error.")

        result_log.error_code = e.get("msgid", "Unknown.Error.")
        result_log.error_code = f"Borg.{result_log.error_code}"

        logger.borg_log(result_log.error_message)

    return result_log


def create_repository(path: str, encryption: str) -> BorgdroneEvent[None]:
    result_log = BorgdroneEvent[None]()
    result_log.event = "BorgRunner._create_repository"

    command = BORG_INIT_COMMAND.copy()
    command[1] = f"--encryption={encryption}"
    command[2] = path

    result_log.message = " ".join(command)

    result = bash.run(command)
    if "stderr" in result:
        # - Repository.ParentPathDoesNotExist
        # - Repository.AlreadyExists
        result_log = __process_error(result_log, result["stderr"])

    else:
        result_log.status = "SUCCESS"

    return result_log


def borg_info(path: str, archive_name: OptStr = None, first: int = 0, last: int = 0) -> BorgdroneEvent[dict]:
    _log = BorgdroneEvent[dict]()
    _log.event = "BorgRunner.borg_info"

    command = BORG_INFO_COMMAND.copy()
    command[1] = path

    if first > 0:
        command.insert(3, f"--first {str(first)}")
    elif last > 0:
        command.insert(3, f"--last {str(last)}")

    if archive_name:
        command[1] = f"{path}::{archive_name}"
    else:
        command[1] = path

    _log.message = " ".join(command)

    result = bash.run(command)
    if "stderr" in result:
        __process_error(_log, result["stderr"])

    else:
        info: dict = json.loads(result["stdout"])
        _log.status = "SUCCESS"
        _log.set_data(info)

    return _log


def delete_repository(path: str) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "BorgRunner.delete_repository"

    command = BORG_DELETE_COMMAND.copy()
    command[1] = path

    _log.message = " ".join(command)

    result = bash.run(command)
    if "stderr" in result:
        # Possible:
        # - Repository.DoesNotExist
        __process_error(_log, result["stderr"])

    else:
        _log.status = "SUCCESS"

    return _log


def list_archives(repo_path: str, first: int = 0, last: int = 0) -> BorgdroneEvent[List[Dict[str, Any]]]:
    _log = BorgdroneEvent[List[Dict[str, Any]]]()
    _log.event = "BorgRunner.get_archives"

    command = BORG_LIST_COMMAND.copy()
    command[1] = repo_path

    if first > 0:
        command.insert(3, f"--first {str(first)}")
    elif last > 0:
        command.insert(3, f"--last {str(last)}")

    result = bash.run(command)
    if "stderr" in result:
        # Possible:
        # - Repository.DoesNotExist
        __process_error(_log, result["stderr"])
    else:
        data = json.loads(result["stdout"])
        _log.set_data(data["archives"])

    return _log


def get_last_archive(repo_path: str) -> BorgdroneEvent[Dict[str, Any]]:
    """Get the last archive from the repository.

    Arguments:
        repo_path -- Path to the repository.

    Returns:
        BorgdroneEvent[Dict[str, Any]]:
            containing the archive info in the format of the Archive model.
    """
    _log = BorgdroneEvent[Dict[str, Any]]()
    _log.event = "BorgRunner.get_last_archive"

    result_log = borg_info(repo_path, last=1)

    if not (archive_data := result_log.get_data()):
        _log.status = "FAILURE"
        _log.error_message = result_log.error_message
        return _log

    if not archive_data["archives"]:
        _log.status = "FAILURE"
        _log.error_message = "No archives found."
        return _log

    info = archive_data["archives"][0]
    repo = archive_data["repository"]
    stats = info["stats"]

    return_data = {}
    return_data["archive_id"] = info["id"]
    return_data["command_line"] = " ".join(info["command_line"])
    return_data["comment"] = info["comment"]
    return_data["duration"] = info["duration"]
    return_data["end"] = info["end"]
    return_data["hostname"] = info["hostname"]
    return_data["name"] = info["name"]
    return_data["start"] = info["start"]
    return_data["tam"] = info.get("tam")
    return_data["time"] = info.get("time")
    return_data["username"] = info["username"]
    return_data["stats_compressed_size"] = stats["compressed_size"]
    return_data["stats_deduplicated_size"] = stats["deduplicated_size"]
    return_data["stats_nfiles"] = stats["nfiles"]
    return_data["stats_original_size"] = stats["original_size"]
    return_data["repository_id"] = repo["id"]

    _log.set_data(return_data)
    return _log
