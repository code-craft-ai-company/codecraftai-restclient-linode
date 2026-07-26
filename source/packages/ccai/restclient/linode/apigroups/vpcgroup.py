"""
    .. module:: vpcgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`VpcGroup` — Linode VPCs and their subnets.

    Reached as ``client.vpcs``.  The group is CALLABLE so ``client.vpcs()``
    lists VPCs while ``client.vpcs.create(...)`` creates one — both SDK-era
    shapes.

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
    LinodeResource, make_resource
)


class VpcGroup(CollectionGroupBase):
    """
        VPC operations.
    """

    collection_path: str = "/vpcs"

    def __call__(self, *, params: Optional[Dict[str, Any]] = None
                 ) -> List[LinodeResource]:
        """
            List every VPC.

            :param params: Optional query parameters.

            :returns: The VPCs, as active-record resources.
        """
        rtnval = self.list_all(params=params)
        return rtnval

    def subnets(self, *, vpc_id: Any) -> List[LinodeResource]:
        """
            List a VPC's subnets.

            Subnets are nested under their VPC, so each is bound to that
            VPC's subnet collection and can delete itself.

            :param vpc_id: The owning VPC id.

            :returns: The subnets, as active-record resources.
        """
        path = "{}/{}/subnets".format(self.collection_path, vpc_id)
        entries = self._client.paginate(path=path)
        rtnval = [make_resource(payload=entry, client=self._client,
                                collection_path=path)
                  for entry in entries]
        return rtnval

    def subnet_create(self, *, vpc_id: Any, label: str,
                      ipv4: str) -> LinodeResource:
        """
            Create a subnet in a VPC.

            :param vpc_id: The owning VPC id.
            :param label: The subnet label.
            :param ipv4: The subnet CIDR.

            :returns: The created subnet.
        """
        path = "{}/{}/subnets".format(self.collection_path, vpc_id)
        payload = self._client.request(method="POST", path=path,
                                       body={"label": label, "ipv4": ipv4})
        rtnval = make_resource(payload=payload.as_dict(),
                               client=self._client, collection_path=path)
        return rtnval
