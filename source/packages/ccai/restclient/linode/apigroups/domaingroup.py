"""
    .. module:: domaingroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`DomainGroup` — Linode DNS domains and records.

    Reached as ``client.domains``; the group is CALLABLE so
    ``client.domains()`` lists domains.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.linode.apigroups.collectiongroupbase import (
    CollectionGroupBase
)
from ccai.restclient.linode.linoderesource import (
    LinodeDomain, LinodeResource, make_resource
)


class DomainGroup(CollectionGroupBase):
    """
        DNS domain operations.
    """

    collection_path: str = "/domains"
    resource_class: Optional[type] = LinodeDomain

    def __call__(self, *, params: Optional[Dict[str, Any]] = None
                 ) -> List[LinodeResource]:
        """
            List every domain.

            :param params: Optional query parameters.

            :returns: The domains, as active-record resources.
        """
        rtnval = self.list_all(params=params)
        return rtnval

    def records(self, *, domain_id: Any) -> List[LinodeResource]:
        """
            List a domain's records.

            :param domain_id: The owning domain id.

            :returns: The records, as active-record resources.
        """
        path = "{}/{}/records".format(self.collection_path, domain_id)
        entries = self._client.paginate(path=path)
        rtnval = [make_resource(payload=entry, client=self._client,
                                collection_path=path)
                  for entry in entries]
        return rtnval

    def record_create(self, *, domain_id: Any, **fields: Any
                      ) -> LinodeResource:
        """
            Create a record in a domain.

            :param domain_id: The owning domain id.
            :param fields: The record fields (type, name, target, ttl_sec).

            :returns: The created record.
        """
        path = "{}/{}/records".format(self.collection_path, domain_id)
        body: Dict[str, Any] = {}
        for key, value in fields.items():
            if value is not None:
                body[key] = value
        payload = self._client.request(method="POST", path=path, body=body)
        rtnval = make_resource(payload=payload.as_dict(),
                               client=self._client, collection_path=path)
        return rtnval
