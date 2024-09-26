import json
from typing import Any, Dict, List, Optional

from borgdrone.helpers import bash
from borgdrone.logging import BorgdroneEvent, logger
from borgdrone.types import OptStr

from .constants import (
    BORG_CHECK_COMMAND,
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
    result_log.event = "BorgRunner.create_repository"

    command = BORG_INIT_COMMAND
    command = command.replace("KEY", encryption)
    command = command.replace("PATH", path)

    result_log.message = command

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
    _log.status = "SUCCESS"

    command = BORG_DELETE_COMMAND.copy()
    command[1] = path

    _log.message = " ".join(command)

    result = bash.run(command)
    if "stderr" in result:
        # Possible:
        # - Repository.DoesNotExist
        __process_error(_log, result["stderr"])

    return _log


def list_archives(repo_path: str, first: int = 0, last: int = 0) -> BorgdroneEvent[List[Dict[str, Any]]]:
    _log = BorgdroneEvent[List[Dict[str, Any]]]()
    _log.event = "BorgRunner.get_archives"
    _log.status = "SUCCESS"

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


def __parse_archive_info(raw_data: dict) -> List[Dict[str, Any]]:
    """Parse the archive data.

    Arguments:
        archive_data -- BORG_INFO_COMMAND output

    Returns:
        None -- If the archive data is empty.
        Dict[str, Any] -- Archive data in Archive() model as a dict.
    """
    archives = []
    if not raw_data["archives"]:
        return archives

    repo_id = raw_data["repository"]["id"]

    for archive in raw_data["archives"]:
        info = archive
        stats = info.get("stats")

        return_data = {}

        return_data["archive_id"] = info["id"]
        return_data["repository_id"] = repo_id
        return_data["command_line"] = " ".join(info["command_line"])
        return_data["duration"] = info.get("duration")
        return_data["end"] = info["end"]
        return_data["hostname"] = info["hostname"]
        return_data["name"] = info["name"]
        return_data["start"] = info["start"]
        return_data["tam"] = info.get("tam")
        return_data["time"] = info.get("time")
        return_data["username"] = info["username"]

        if stats:
            return_data["stats_compressed_size"] = stats["compressed_size"]
            return_data["stats_deduplicated_size"] = stats["deduplicated_size"]
            return_data["stats_nfiles"] = stats["nfiles"]
            return_data["stats_original_size"] = stats["original_size"]

        archives.append(return_data)

    return archives


def archive_info(repo_path: str, archive_name: str) -> BorgdroneEvent[Dict[str, Any]]:
    _log = BorgdroneEvent[Dict[str, Any]]()
    _log.event = "BorgRunner.archive_info"

    result_log = borg_info(repo_path, archive_name=archive_name)
    if not (archive_data := result_log.get_data()):
        _log.status = "FAILURE"
        _log.error_message = result_log.error_message
        return _log

    data = __parse_archive_info(archive_data)
    if not data:
        _log.status = "FAILURE"
        _log.error_message = "Failed to parse archive data."
        return _log

    _log.set_data(data)
    return _log


def get_last_archive(repo_path: str) -> BorgdroneEvent[Optional[dict]]:
    """Get the last archive from the repository.

    Arguments:
        repo_path -- Path to the repository.

    Returns:
        BorgdroneEvent[Dict[str, Any]]:
            containing the archive info in the format of the Archive model.
    """
    _log = BorgdroneEvent[Optional[Dict[str, Any]]]()
    _log.event = "BorgRunner.get_last_archive"
    _log.status = "SUCCESS"

    result_log = borg_info(repo_path, last=1)
    if not (archive_data := result_log.get_data()):
        _log.status = "FAILURE"
        _log.error_message = result_log.error_message
        return _log

    data = __parse_archive_info(archive_data)
    if not data:
        _log.status = "FAILURE"
        _log.error_message = "Failed to parse archive data."
        return _log

    _log.set_data(data)
    return _log


def borg_check(repo_path: str, repository_only: bool = True) -> BorgdroneEvent[None]:
    _log = BorgdroneEvent[None]()
    _log.event = "BorgRunner.borg_check"
    _log.status = "SUCCESS"

    command = BORG_CHECK_COMMAND.copy()
    if repository_only:
        command.append("--repository-only")

    command.append(repo_path)
    result = bash.run(command)
    if "stderr" in result:
        __process_error(_log, result["stderr"])

    return _log
