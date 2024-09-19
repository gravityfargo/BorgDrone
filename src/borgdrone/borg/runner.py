import json
from typing import Dict

from borgdrone.helpers import bash
from borgdrone.logging import BorgdroneEvent
from borgdrone.logging import logger as log


class BorgRunner:
    def __init__(self):
        pass

    def run(self, purpose: str, **kwargs) -> BorgdroneEvent:
        match purpose:
            case "create_repo":
                result_log = self._create_repository(kwargs["path"], kwargs["encryption"])
            case "delete_repo":
                result_log = self.__delete_repository(kwargs["path"])
            case "get_repository_info":
                result_log = self.__repository_info(kwargs["path"])
            case _:
                result_log = BorgdroneEvent()
                result_log.status = "FAILURE"
                result_log.error_message = "Invalid BorgRunner purpose."

        return result_log

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

    def _create_repository(self, path: str, encryption: str) -> BorgdroneEvent:
        result_log = BorgdroneEvent()
        result_log.event = "BorgRunner._create_repository"

        command = f"borg --log-json init --encryption={encryption} {path}"
        result_log.message = command

        result = bash.run(command)
        if "stderr" in result:
            # - Repository.ParentPathDoesNotExist
            # - Repository.AlreadyExists
            result_log = self.__process_error(result_log, result["stderr"])

        else:
            result_log.status = "SUCCESS"

        return result_log

    def __repository_info(self, path: str) -> BorgdroneEvent[Dict[str, str]]:
        result_log = BorgdroneEvent[Dict[str, str]]()
        result_log.event = "BorgRunner.repository_info"

        command = f"borg --log-json info --json {path}"
        result_log.message = command

        result = bash.run(command)
        if "stderr" in result:
            self.__process_error(result_log, result["stderr"])

        else:
            info: dict = json.loads(result["stdout"])
            result_log.status = "SUCCESS"
            result_log.set_data(info)

        return result_log

    def __delete_repository(self, path: str) -> BorgdroneEvent:
        result_log = BorgdroneEvent()
        result_log.event = "BorgRunner.delete_repository"

        command = f"borg --log-json delete --force {path}"
        result_log.message = command

        result = bash.run(command)
        if "stderr" in result:
            # Possible:
            # - Repository.DoesNotExist
            self.__process_error(result_log, result["stderr"])

        else:
            result_log.status = "SUCCESS"

        return result_log
