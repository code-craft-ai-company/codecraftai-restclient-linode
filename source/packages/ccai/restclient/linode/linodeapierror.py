"""
    .. module:: linodeapierror
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`LinodeApiRequestError` — the transport-level error
               raised for a non-success Linode API response.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Optional


class LinodeApiRequestError(Exception):
    """
        Raised when the Linode API returns a non-success status.

        :ivar status: The HTTP status code.
        :ivar reason: The reason, extracted from the API's ``errors`` array
            when present so the message names the offending field.
        :ivar body: The raw response body text.
    """

    def __init__(self, message: str, *, status: int = 0,
                 reason: str = "", body: Optional[str] = None) -> None:
        """
            Construct a LinodeApiRequestError.

            :param message: The human-readable error message.
            :param status: The HTTP status code.
            :param reason: The extracted reason.
            :param body: The raw response body.
        """
        super().__init__(message)
        self.status: int = status
        self.reason: str = reason
        self.body: Optional[str] = body
        return
