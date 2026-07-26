"""
    .. module:: instancegroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`InstanceGroup` — Linode compute instances.

    Reached as ``client.linode`` so the SDK-era call shapes
    ``client.linode.instances()`` and ``client.linode.instance_create(...)``
    keep working.

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
    LinodeInstance, LinodeResource
)


class InstanceGroup(CollectionGroupBase):
    """
        Compute-instance operations.
    """

    collection_path: str = "/linode/instances"
    resource_class: Optional[type] = LinodeInstance

    def instances(self, *, params: Optional[Dict[str, Any]] = None
                  ) -> List[LinodeResource]:
        """
            List every instance.

            :param params: Optional query parameters.

            :returns: The instances, as active-record resources.
        """
        rtnval = self.list_all(params=params)
        return rtnval

    def instance_create(self, *, ltype: Optional[str] = None,
                        region: Optional[str] = None, **fields: Any
                        ) -> LinodeResource:
        """
            Create an instance.

            The API field is ``type``, which is a Python builtin and an
            awkward keyword; ``ltype`` is accepted as an alias and a literal
            ``type=`` keyword still works for call sites that pass it.

            :param ltype: The Linode plan type id.
            :param region: The region id.
            :param fields: Remaining instance fields (label, image,
                authorized_keys, root_pass, tags, private_ip, metadata...).

            :returns: The created instance.
        """
        body: Dict[str, Any] = dict(fields)
        if ltype is not None:
            body["type"] = ltype
        if region is not None:
            body["region"] = region
        rtnval = self.create(**body)
        return rtnval

    def instance_delete(self, *, instance_id: Any) -> None:
        """
            Delete an instance by id.

            :param instance_id: The instance id.

            :returns: ``None``
        """
        self.delete(identifier=instance_id)
        return
