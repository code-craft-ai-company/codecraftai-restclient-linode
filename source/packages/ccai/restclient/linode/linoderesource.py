"""
    .. module:: linoderesource
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Active-record resource objects returned by the Linode REST
               client.

    The Linode API returns JSON objects with snake_case fields, which is
    already the spelling Python callers want, so a resource is a ``dict``
    that is additionally attribute addressable — ``volume.label`` and
    ``volume["label"]`` both work, and an absent field reads as ``None``
    rather than raising.

    Resources are ACTIVE RECORD: a resource carries the client and its
    collection path, so ``resource.delete()`` works without the caller
    tracking which endpoint the object came from.  That is deliberate — it
    is how callers already work with these objects, and it keeps
    delete/detach/resize call sites unchanged when moving off a vendor SDK.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, Optional


class LinodeObject(dict):
    """
        A ``dict`` of Linode API JSON that is also attribute addressable.

        A missing field reads as ``None`` so ``getattr(obj, "field", None)``
        guards in caller code behave the same way they did against an
        object-model SDK.

        The Linode API uses ``label`` for the human name and ``id`` for the
        identifier; both are ordinary fields here.  ``id`` shadows nothing,
        but the dict methods ``keys`` / ``values`` / ``items`` / ``get`` /
        ``update`` / ``copy`` / ``pop`` / ``clear`` are NOT shadowed by
        fields, because no Linode payload uses those names — unlike the
        Kubernetes list envelope, this API nests collections under ``data``.
    """

    def __getattr__(self, name: str) -> Any:
        """
            Resolve a field by attribute access.

            :param name: The field name.

            :returns: The wrapped field value, or ``None`` when absent.
        """
        if name.startswith("_") is True:
            # Never resolve private/dunder lookups as API fields; that would
            # make copy/pickle/inspect machinery see phantom attributes.
            raise AttributeError(name)

        if name in self:
            rtnval = wrap_linode_value(self[name])
            return rtnval

        rtnval = None
        return rtnval

    def __setattr__(self, name: str, value: Any) -> None:
        """
            Set a field by attribute assignment.

            :param name: The field name.
            :param value: The value to store.

            :returns: ``None``
        """
        if name.startswith("_") is True:
            object.__setattr__(self, name, value)
            return
        self[name] = value
        return

    def as_dict(self) -> Dict[str, Any]:
        """
            Return the underlying plain dictionary.

            :returns: The wire-shaped dictionary.
        """
        rtnval = dict(self)
        return rtnval


def wrap_linode_value(value: Any) -> Any:
    """
        Wrap a decoded JSON value so nested objects stay attribute
        addressable.

        :param value: The decoded JSON value.

        :returns: A :class:`LinodeObject` for dicts, a list of wrapped
            values for lists, or the value unchanged.
    """
    if isinstance(value, LinodeObject) is True:
        rtnval = value
        return rtnval
    if isinstance(value, dict) is True:
        rtnval = LinodeObject(value)
        return rtnval
    if isinstance(value, list) is True:
        rtnval = [wrap_linode_value(item) for item in value]
        return rtnval
    rtnval = value
    return rtnval


class LinodeResource(LinodeObject):
    """
        A Linode API object that knows how to delete itself.

        :ivar _client: The owning :class:`LinodeRestClient`.
        :ivar _collection_path: The collection path the object came from,
            e.g. ``/volumes``.
        :ivar _identifier_field: The field carrying the resource id — ``id``
            for most kinds, ``label`` for object-storage buckets.
    """

    def bind(self, *, client: Any, collection_path: str,
             identifier_field: str = "id") -> "LinodeResource":
        """
            Bind this resource to the client and path that produced it.

            :param client: The owning :class:`LinodeRestClient`.
            :param collection_path: The collection path.
            :param identifier_field: The field carrying the identifier.

            :returns: ``self``, for call chaining at construction.
        """
        self._client = client
        self._collection_path = collection_path
        self._identifier_field = identifier_field
        rtnval = self
        return rtnval

    @property
    def resource_path(self) -> str:
        """
            Return this resource's item path.

            :returns: The item path, e.g. ``/volumes/12345``.
        """
        identifier = self.get(self._identifier_field, None)
        rtnval = "{}/{}".format(self._collection_path, identifier)
        return rtnval

    def delete(self) -> None:
        """
            Delete this resource.

            :returns: ``None``
        """
        self._client.request(method="DELETE", path=self.resource_path)
        return


class LinodeInstance(LinodeResource):
    """
        A Linode compute instance.
    """

    def resize(self, *, new_type: str,
               allow_auto_disk_resize: bool = True) -> None:
        """
            Resize this instance to a new plan type.

            The API shuts the instance down, migrates it, and boots it
            again; the call returns once accepted, not once complete.

            :param new_type: The target Linode type id.
            :param allow_auto_disk_resize: Whether the API may grow the
                primary disk to fill the new plan.

            :returns: ``None``
        """
        body = {"type": new_type,
                "allow_auto_disk_resize": allow_auto_disk_resize}
        self._client.request(method="POST",
                             path="{}/resize".format(self.resource_path),
                             body=body)
        return

    def boot(self) -> None:
        """
            Boot this instance.

            :returns: ``None``
        """
        self._client.request(method="POST",
                             path="{}/boot".format(self.resource_path))
        return

    def shutdown(self) -> None:
        """
            Shut this instance down.

            :returns: ``None``
        """
        self._client.request(method="POST",
                             path="{}/shutdown".format(self.resource_path))
        return


class LinodeVolume(LinodeResource):
    """
        A Linode block-storage volume.
    """

    def detach(self) -> None:
        """
            Detach this volume from whatever instance holds it.

            :returns: ``None``
        """
        self._client.request(method="POST",
                             path="{}/detach".format(self.resource_path))
        return

    def attach(self, *, linode_id: int) -> None:
        """
            Attach this volume to an instance.

            :param linode_id: The target instance id.

            :returns: ``None``
        """
        self._client.request(method="POST",
                             path="{}/attach".format(self.resource_path),
                             body={"linode_id": linode_id})
        return

    def resize(self, *, size: int) -> None:
        """
            Grow this volume.

            :param size: The new size in GB.

            :returns: ``None``
        """
        self._client.request(method="POST",
                             path="{}/resize".format(self.resource_path),
                             body={"size": size})
        return


class LinodeVpc(LinodeResource):
    """
        A Linode VPC, which owns its subnets.
    """

    def subnet_create(self, *, label: str, ipv4: str) -> "LinodeResource":
        """
            Create a subnet in this VPC.

            :param label: The subnet label.
            :param ipv4: The subnet CIDR.

            :returns: The created subnet, bound to this VPC's subnet
                collection so it can delete itself.
        """
        path = "{}/subnets".format(self.resource_path)
        payload = self._client.request(method="POST", path=path,
                                       body={"label": label, "ipv4": ipv4})
        rtnval = make_resource(payload=payload.as_dict(),
                               client=self._client, collection_path=path)
        return rtnval

    @property
    def subnets(self) -> Any:
        """
            Return this VPC's subnets as deletable resources.

            The API embeds a ``subnets`` array in the VPC payload.  Returning
            it raw would hand back inert dicts, and a caller doing
            ``getattr(subnet, "delete", None)`` would find nothing and
            silently skip the delete — leaking subnets on teardown.  So each
            entry is bound to this VPC's subnet collection.  When the payload
            carries no array the collection is fetched.

            :returns: The subnets, as active-record resources.
        """
        path = "{}/subnets".format(self.resource_path)

        embedded = self.get("subnets", None)
        if embedded is None:
            embedded = self._client.paginate(path=path)

        rtnval = [make_resource(payload=dict(entry), client=self._client,
                                collection_path=path)
                  for entry in embedded]
        return rtnval


class LinodeDomain(LinodeResource):
    """
        A Linode DNS domain.
    """

    def record_create(self, *, record_type: str, name: str, target: str,
                      ttl_sec: Optional[int] = None) -> "LinodeResource":
        """
            Create a record in this domain.

            The API field is ``type``; the parameter is ``record_type``
            because that is what callers already pass (``type`` is a Python
            builtin and an awkward keyword).

            :param record_type: The record type, e.g. ``A`` or ``CNAME``.
            :param name: The record name.
            :param target: The record target.
            :param ttl_sec: Optional TTL in seconds.

            :returns: The created record, bound to this domain's record
                collection.
        """
        path = "{}/records".format(self.resource_path)
        body: Dict[str, Any] = {"type": record_type, "name": name,
                                "target": target}
        if ttl_sec is not None:
            body["ttl_sec"] = ttl_sec
        payload = self._client.request(method="POST", path=path, body=body)
        rtnval = make_resource(payload=payload.as_dict(),
                               client=self._client, collection_path=path)
        return rtnval

    def records(self) -> Any:
        """
            List this domain's records.

            :returns: The records, as active-record resources.
        """
        path = "{}/records".format(self.resource_path)
        entries = self._client.paginate(path=path)
        rtnval = [make_resource(payload=entry, client=self._client,
                                collection_path=path)
                  for entry in entries]
        return rtnval


def make_resource(*, payload: Dict[str, Any], client: Any,
                  collection_path: str,
                  resource_class: Optional[type] = None,
                  identifier_field: str = "id") -> LinodeResource:
    """
        Build a bound resource of the appropriate class.

        :param payload: The decoded JSON object.
        :param client: The owning client.
        :param collection_path: The collection path.
        :param resource_class: The resource class to build; defaults to
            :class:`LinodeResource`.
        :param identifier_field: The field carrying the identifier.

        :returns: The bound resource.
    """
    target_class = resource_class
    if target_class is None:
        target_class = LinodeResource

    resource = target_class(payload)
    rtnval = resource.bind(client=client, collection_path=collection_path,
                           identifier_field=identifier_field)
    return rtnval
