"""
    .. module:: collectiongroupbase
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`CollectionGroupBase` — shared list/create/get for a
               Linode collection.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.linode.linoderesource import (
    LinodeResource, make_resource
)


class CollectionGroupBase:
    """
        Shared operations over one Linode collection.

        :ivar collection_path: The collection path, e.g. ``/volumes``.
        :ivar resource_class: The active-record class list/create return.
        :ivar identifier_field: The field carrying the resource id.
    """

    collection_path: str = ""
    resource_class: Optional[type] = None
    identifier_field: str = "id"

    def __init__(self, *, client: Any) -> None:
        """
            Construct a CollectionGroupBase.

            :param client: The owning :class:`LinodeRestClient`.
        """
        self._client: Any = client
        return

    @property
    def client(self) -> Any:
        """
            Return the owning client.

            :returns: The :class:`LinodeRestClient`.
        """
        rtnval = self._client
        return rtnval

    def _wrap(self, *, payload: Dict[str, Any]) -> LinodeResource:
        """
            Wrap a raw entry as a bound active-record resource.

            :param payload: The decoded JSON object.

            :returns: The bound resource.
        """
        rtnval = make_resource(payload=payload, client=self._client,
                               collection_path=self.collection_path,
                               resource_class=self.resource_class,
                               identifier_field=self.identifier_field)
        return rtnval

    def list_all(self, *, params: Optional[Dict[str, Any]] = None
                 ) -> List[LinodeResource]:
        """
            List every entry in the collection, following pagination.

            :param params: Optional query parameters.

            :returns: The bound resources.
        """
        entries = self._client.paginate(path=self.collection_path,
                                        params=params)
        rtnval = [self._wrap(payload=entry) for entry in entries]
        return rtnval

    def get(self, *, identifier: Any) -> LinodeResource:
        """
            Read one entry by identifier.

            :param identifier: The resource id (or label, for buckets).

            :returns: The bound resource.
        """
        path = "{}/{}".format(self.collection_path, identifier)
        payload = self._client.request(method="GET", path=path)
        rtnval = self._wrap(payload=payload.as_dict())
        return rtnval

    def create(self, **fields: Any) -> LinodeResource:
        """
            Create an entry in the collection.

            Keyword fields are sent as the JSON body, with ``None`` values
            dropped so an unset optional field is absent rather than
            explicitly null.

            :param fields: The resource fields.

            :returns: The created bound resource.
        """
        body: Dict[str, Any] = {}
        for key, value in fields.items():
            if value is not None:
                body[key] = value

        payload = self._client.request(method="POST",
                                       path=self.collection_path, body=body)
        rtnval = self._wrap(payload=payload.as_dict())
        return rtnval

    def delete(self, *, identifier: Any) -> None:
        """
            Delete an entry by identifier.

            :param identifier: The resource id.

            :returns: ``None``
        """
        path = "{}/{}".format(self.collection_path, identifier)
        self._client.request(method="DELETE", path=path)
        return
