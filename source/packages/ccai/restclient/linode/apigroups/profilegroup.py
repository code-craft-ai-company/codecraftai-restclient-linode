"""
    .. module:: profilegroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`ProfileGroup` — the authenticated user's profile,
               used here for SSH keys.

    Reached as ``client.profile``, preserving the SDK-era shapes
    ``client.profile.ssh_keys()`` and
    ``client.profile.ssh_key_upload(...)``.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.linode.linoderesource import (
    LinodeResource, make_resource
)


SSH_KEYS_PATH = "/profile/sshkeys"


class ProfileGroup:
    """
        Profile operations.
    """

    def __init__(self, *, client: Any) -> None:
        """
            Construct a ProfileGroup.

            :param client: The owning :class:`LinodeRestClient`.
        """
        self._client: Any = client
        return

    def ssh_keys(self, *, params: Optional[Dict[str, Any]] = None
                 ) -> List[LinodeResource]:
        """
            List the profile's SSH keys.

            :param params: Optional query parameters.

            :returns: The SSH keys, as active-record resources.
        """
        entries = self._client.paginate(path=SSH_KEYS_PATH, params=params)
        rtnval = [make_resource(payload=entry, client=self._client,
                                collection_path=SSH_KEYS_PATH)
                  for entry in entries]
        return rtnval

    def ssh_key_upload(self, *, key: str, label: str) -> LinodeResource:
        """
            Upload an SSH public key to the profile.

            :param key: The public key material.
            :param label: The key label.

            :returns: The created SSH key.
        """
        payload = self._client.request(method="POST", path=SSH_KEYS_PATH,
                                       body={"ssh_key": key,
                                             "label": label})
        rtnval = make_resource(payload=payload.as_dict(),
                               client=self._client,
                               collection_path=SSH_KEYS_PATH)
        return rtnval
