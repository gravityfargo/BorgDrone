from typing import Generic, Optional, TypeVar

from borgdrone.logging import logger as log

T = TypeVar("T")


class BorgdroneEvent(Generic[T]):
    """
    The generic type is for the data attribute.

    Return value usage:
        func() -> BorgdroneEvent[Dict[str, str]]


    """

    def __init__(self):
        self.status: str = "NOSTATUS"
        # SUCCESS, FAILURE

        self.message: Optional[str]
        self.error_message: str = ""
        # for toasts and logs

        self.event: Optional[str]
        # for self.borgdrone_return()
        #
        # extension to Borg's Message IDs
        # will have the suffix of SUCCESS or FAILURE
        # ClassName.method_name
        #
        # "RepositoryManager.import_repo.SUCCESS"

        self.error_code: Optional[str] = None
        # for self.borgdrone_return()
        #
        # only to be set in .borg.runner.BorgRunner.__process_error()
        # Borg's Message IDs
        # https://borgbackup.readthedocs.io/en/stable/internals/frontends.html#message-ids
        #
        # "Repository.ParentPathDoesNotExist"

        self.data: Optional[T] = None

    def borgdrone_return(self):

        if self.error_code:
            return self.error_code

        ret = f"{self.event}.{self.status}"
        return ret

    def set_data(self, value: T):
        """Set the value of data."""
        self.data = value

    def get_data(self) -> Optional[T]:
        """Return the data as its original type."""
        return self.data

    def not_found_message(self, object_name: str) -> "BorgdroneEvent":
        self.status = "FAILURE"
        if not self.event:
            self.event = "BorgdroneEvent.not_found_message"

        self.error_message = f"Failed to find {object_name}."

        log.error_event(self.error_message)
        return self

    def return_success(self, success_message: Optional[str] = None, debug: bool = False) -> "BorgdroneEvent":
        self.status = "SUCCESS"

        if success_message:
            self.message = success_message

        if not self.event:
            self.event = "BorgdroneEvent.success_message"

        if debug:
            log.debug_event(self.message, "green")
        else:
            log.success_event(self.message)

        return self

    def return_failure(self, error_message: Optional[str] = None, debug: bool = False) -> "BorgdroneEvent":
        self.status = "FAILURE"

        if error_message:
            self.error_message = error_message

        if not self.event:
            self.event = "BorgdroneEvent.failure_message"

        if debug:
            log.debug_event(self.error_message, "red")
        else:
            log.error_event(self.error_message)

        return self

    def return_debug_success(self, success_message: Optional[str] = None) -> "BorgdroneEvent":
        self.return_success(success_message, debug=True)
        return self

    def return_debug_failure(self, error_message: Optional[str] = None) -> "BorgdroneEvent":
        self.return_failure(error_message, debug=True)
        return self
