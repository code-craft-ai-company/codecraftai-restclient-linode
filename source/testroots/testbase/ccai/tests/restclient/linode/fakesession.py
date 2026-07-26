"""
    .. module:: fakesession
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: A recording fake ``requests.Session`` for the Kubernetes REST
               client tests.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import json

from typing import Any, Dict, List, Optional


class FakeResponse:
    """
        Minimal stand-in for a ``requests.Response``.
    """

    def __init__(self, *, status_code: int = 200,
                 payload: Optional[Any] = None, text: Optional[str] = None,
                 reason: str = "OK") -> None:
        self.status_code = status_code
        self.reason = reason
        if text is not None:
            self.text = text
        elif payload is not None:
            self.text = json.dumps(payload)
        else:
            self.text = ""
        self._payload = payload

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


class FakeSession:
    """
        Records requests and replays queued responses.

        Responses are queued per ``(METHOD, path)`` key, with a default for
        unmatched requests, so a test declares only what it cares about.
    """

    def __init__(self) -> None:
        self.headers: Dict[str, str] = {}
        self.verify: Any = True
        self.cert: Any = None
        self.calls: List[Dict[str, Any]] = []
        self.responses: Dict[str, List[FakeResponse]] = {}
        self.default_response: FakeResponse = FakeResponse(payload={})

    def queue(self, *, method: str, path: str,
              response: FakeResponse) -> None:
        """
            Queue a response for a method/path pair.

            :param method: The HTTP method.
            :param path: The API path (suffix match).
            :param response: The response to return.
        """
        key = "{} {}".format(method.upper(), path)
        self.responses.setdefault(key, []).append(response)
        return

    def queue_page(self, *, path: str, entries, page: int = 1,
                   pages: int = 1) -> None:
        """
            Queue one page of a Linode paginated collection.

            :param path: The collection path.
            :param entries: The page's entries.
            :param page: This page's number.
            :param pages: The total page count.
        """
        payload = {"data": entries, "page": page, "pages": pages,
                   "results": len(entries)}
        self.queue(method="GET", path=path,
                   response=FakeResponse(payload=payload))
        return

    def request(self, method: str, url: str, params=None, data=None,
                headers=None, timeout=None) -> FakeResponse:
        """
            Record and answer a request.
        """
        body = None
        if data is not None:
            body = json.loads(data)

        record = {"method": method, "url": url, "params": params or {},
                  "body": body, "headers": headers or {},
                  "timeout": timeout}
        self.calls.append(record)

        for key, queued in self.responses.items():
            wanted_method, _, wanted_path = key.partition(" ")
            if method.upper() == wanted_method and url.endswith(wanted_path):
                if len(queued) > 0:
                    rtnval = queued.pop(0)
                    return rtnval

        rtnval = self.default_response
        return rtnval
