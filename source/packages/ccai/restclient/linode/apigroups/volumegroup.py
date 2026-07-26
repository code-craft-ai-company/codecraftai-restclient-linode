"""
    .. module:: volumegroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`VolumeGroup` — Linode block-storage volumes.

    Reached as ``client.volumes``.  The group is CALLABLE so the SDK-era
    shape ``client.volumes()`` lists volumes.

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
    LinodeResource, LinodeVolume
)


class VolumeGroup(CollectionGroupBase):
    """
        Block-storage volume operations.
    """

    collection_path: str = "/volumes"
    resource_class: Optional[type] = LinodeVolume

    def __call__(self, *, params: Optional[Dict[str, Any]] = None
                 ) -> List[LinodeResource]:
        """
            List every volume.

            :param params: Optional query parameters.

            :returns: The volumes, as active-record resources.
        """
        rtnval = self.list_all(params=params)
        return rtnval
