import json
from typing import Dict, List

from borgdrone.helpers import bash
from borgdrone.logging import BorgdroneEvent
from borgdrone.logging import logger as log

from .constants import (
    BORG_DELETE_COMMAND,
    BORG_INFO_COMMAND,
    BORG_INIT_COMMAND,
    BORG_LIST_COMMAND,
)


class BorgRunner:
    def __init__(self):
        pass

    def __process_error(self, result_log: BorgdroneEvent, error: str) -> BorgdroneEvent:
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

            log.borg_log(result_log.error_message)

        return result_log

    def create_repository(self, path: str, encryption: str) -> BorgdroneEvent[None]:
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
            result_log = self.__process_error(result_log, result["stderr"])

        else:
            result_log.status = "SUCCESS"

        return result_log

    def repository_info(self, path: str, first: int = 0, last: int = 0) -> BorgdroneEvent[dict]:
        result_log = BorgdroneEvent[dict]()
        result_log.event = "BorgRunner.repository_info"

        command = BORG_INFO_COMMAND.copy()
        command[1] = path

        result_log.message = " ".join(command)

        result = bash.run(command)
        if "stderr" in result:
            self.__process_error(result_log, result["stderr"])

        else:
            info: dict = json.loads(result["stdout"])
            result_log.status = "SUCCESS"
            result_log.set_data(info)

        return result_log

    def delete_repository(self, path: str) -> BorgdroneEvent[None]:
        _log = BorgdroneEvent[None]()
        _log.event = "BorgRunner.delete_repository"

        command = BORG_DELETE_COMMAND.copy()
        command[1] = path

        _log.message = " ".join(command)

        result = bash.run(command)
        if "stderr" in result:
            # Possible:
            # - Repository.DoesNotExist
            self.__process_error(_log, result["stderr"])

        else:
            _log.status = "SUCCESS"

        return _log

    def list_archives(self, repo_path: str, first: int = 0, last: int = 0) -> BorgdroneEvent[List[Dict[str, str]]]:
        _log = BorgdroneEvent[List[Dict[str, str]]]()
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
            self.__process_error(_log, result["stderr"])
        else:
            data = json.loads(result["stdout"])
            _log.set_data(data["archives"])

        return _log
