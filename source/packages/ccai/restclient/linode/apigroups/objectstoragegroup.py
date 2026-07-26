"""
    .. module:: objectstoragegroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`ObjectStorageGroup` — Linode object-storage buckets.

    Reached as ``client.object_storage``, preserving the SDK-era shapes
    ``client.object_storage.buckets()`` and
    ``client.object_storage.bucket_create(...)``.

    Buckets are addressed by ``<cluster>/<label>`` rather than a numeric id,
    so bucket resources bind their own item path instead of using the shared
    id convention.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.linode.linoderesource import LinodeResource


BUCKETS_PATH = "/object-storage/buckets"


class ObjectStorageBucket(LinodeResource):
    """
        An object-storage bucket, addressed by cluster and label.
    """

    @property
    def resource_path(self) -> str:
        """
            Return this bucket's item path.

            :returns: ``/object-storage/buckets/<cluster>/<label>``.
        """
        cluster = self.get("cluster", None)
        if cluster is None:
            cluster = self.get("region", None)
        rtnval = "{}/{}/{}".format(BUCKETS_PATH, cluster,
                                   self.get("label", None))
        return rtnval


class ObjectStorageGroup:
    """
        Object-storage bucket operations.
    """

    def __init__(self, *, client: Any) -> None:
        """
            Construct an ObjectStorageGroup.

            :param client: The owning :class:`LinodeRestClient`.
        """
        self._client: Any = client
        return

    def _wrap(self, *, payload: Dict[str, Any]) -> ObjectStorageBucket:
        """
            Wrap a raw bucket entry as a bound resource.

            :param payload: The decoded JSON object.

            :returns: The bound bucket.
        """
        bucket = ObjectStorageBucket(payload)
        rtnval = bucket.bind(client=self._client,
                             collection_path=BUCKETS_PATH,
                             identifier_field="label")
        return rtnval

    def buckets(self, *, params: Optional[Dict[str, Any]] = None
                ) -> List[ObjectStorageBucket]:
        """
            List every bucket.

            :param params: Optional query parameters.

            :returns: The buckets, as active-record resources.
        """
        entries = self._client.paginate(path=BUCKETS_PATH, params=params)
        rtnval = [self._wrap(payload=entry) for entry in entries]
        return rtnval

    def bucket_create(self, *, label: str,
                      cluster_or_region: Optional[str] = None,
                      cluster: Optional[str] = None,
                      region: Optional[str] = None, **fields: Any
                      ) -> ObjectStorageBucket:
        """
            Create a bucket.

            Linode addressed buckets by object-storage ``cluster``
            historically and by ``region`` in the current API.
            ``cluster_or_region`` is the unified spelling callers use; it is
            sent as ``region``, which the current API expects.  The explicit
            ``cluster`` / ``region`` parameters remain for callers that know
            which they mean.

            :param label: The bucket label.
            :param cluster_or_region: The cluster or region id.
            :param cluster: The object-storage cluster id (legacy).
            :param region: The region id.
            :param fields: Remaining bucket fields (acl, cors_enabled...).

            :returns: The created bucket.
        """
        body: Dict[str, Any] = {"label": label}
        if cluster_or_region is not None:
            body["region"] = cluster_or_region
        if cluster is not None:
            body["cluster"] = cluster
        if region is not None:
            body["region"] = region
        for key, value in fields.items():
            if value is not None:
                body[key] = value

        payload = self._client.request(method="POST", path=BUCKETS_PATH,
                                       body=body)
        rtnval = self._wrap(payload=payload.as_dict())
        return rtnval
