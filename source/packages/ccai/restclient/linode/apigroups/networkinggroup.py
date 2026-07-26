"""
    .. module:: networkinggroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`NetworkingGroup` — Linode cloud firewalls.

    Reached as ``client.networking``, preserving the SDK-era shapes
    ``client.networking.firewalls()`` and
    ``client.networking.firewall_create(...)``.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.linode.linoderesource import (
    LinodeResource, make_resource
)


FIREWALLS_PATH = "/networking/firewalls"


class NetworkingGroup:
    """
        Cloud-firewall operations.
    """

    def __init__(self, *, client: Any) -> None:
        """
            Construct a NetworkingGroup.

            :param client: The owning :class:`LinodeRestClient`.
        """
        self._client: Any = client
        return

    def firewalls(self, *, params: Optional[Dict[str, Any]] = None
                  ) -> List[LinodeResource]:
        """
            List every cloud firewall.

            :param params: Optional query parameters.

            :returns: The firewalls, as active-record resources.
        """
        entries = self._client.paginate(path=FIREWALLS_PATH, params=params)
        rtnval = [make_resource(payload=entry, client=self._client,
                                collection_path=FIREWALLS_PATH)
                  for entry in entries]
        return rtnval

    def firewall_create(self, *, label: str,
                        rules: Optional[Dict[str, Any]] = None,
                        tags: Optional[List[str]] = None,
                        **fields: Any) -> LinodeResource:
        """
            Create a cloud firewall.

            :param label: The firewall label.
            :param rules: The inbound/outbound rule document.
            :param tags: Optional tags.
            :param fields: Remaining firewall fields (devices...).

            :returns: The created firewall.
        """
        body: Dict[str, Any] = {"label": label}
        if rules is not None:
            body["rules"] = rules
        if tags is not None:
            body["tags"] = tags
        for key, value in fields.items():
            if value is not None:
                body[key] = value

        payload = self._client.request(method="POST", path=FIREWALLS_PATH,
                                       body=body)
        rtnval = make_resource(payload=payload.as_dict(),
                               client=self._client,
                               collection_path=FIREWALLS_PATH)
        return rtnval
