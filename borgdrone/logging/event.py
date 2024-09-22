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
        self.status: str = "FAILURE"
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

        self.error_message = "Failed to find repository."
        self.message = f"Failed to find {object_name}."

        log.error(self.error_message)
        return self

    def return_success(self, message: str) -> "BorgdroneEvent":
        """Helper function

        Set the status to SUCCESS and the message to the given message
        logs the message and returns the instance

        Arguments:
            message -- Success message

        Returns:
            self
        """
        self.status = "SUCCESS"
        self.message = message

        if not self.event:
            self.event = "BorgdroneEvent.success_message"

        log.success_event(self.message)
        return self

    def return_failure(self, message: str) -> "BorgdroneEvent":
        """Helper function

        Set the status to FAILURE and the message to the given message
        logs the message and returns the instance

        Do not use for BorgRunner errors, those should be passed to the user directly.

        Arguments:
            message -- Failure message

        Returns:
            self
        """
        self.status = "FAILURE"
        self.error_message = message

        if not self.event:
            self.event = "BorgdroneEvent.failure_message"

        log.error_event(self.error_message)
        return self
