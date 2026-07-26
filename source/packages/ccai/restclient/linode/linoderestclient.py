"""
    .. module:: linoderestclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`LinodeRestClient` — a pure-Python client for the
               Linode (Akamai Cloud) API v4.

    The Linode API is plain REST over HTTPS with JSON bodies and a Bearer
    personal-access token, so this client speaks it directly rather than
    depending on the ``linode_api4`` SDK.

    The api groups mirror the SDK's grouping — ``linode`` (instances),
    ``volumes``, ``vpcs``, ``networking``, ``object_storage``, ``domains``,
    ``profile`` — so call sites written against the SDK keep their shape.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import json
import os

from typing import Any, Dict, List, Optional

import requests

from ccai.restclient.linode.linodeapierror import LinodeApiRequestError
from ccai.restclient.linode.linoderesource import (
    LinodeObject, wrap_linode_value
)


LINODE_API_BASE = "https://api.linode.com/v4"

DEFAULT_TIMEOUT_SECONDS = 60.0

# The API caps page size at 500; asking for the maximum minimises the
# number of round trips when walking a collection.
MAX_PAGE_SIZE = 500


class LinodeRestClient:
    """
        REST client for the Linode API v4.

        The api groups are reached through public attributes named to match
        the SDK's: ``linode``, ``volumes``, ``vpcs``, ``networking``,
        ``object_storage``, ``domains``, ``profile``, ``regions``,
        ``types``.
    """

    def __init__(self, *, token: str, base_url: str = LINODE_API_BASE,
                 session: Optional[Any] = None,
                 timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
                 ) -> None:
        """
            Construct a LinodeRestClient.

            :param token: The Linode personal access token.
            :param base_url: The API base URL.
            :param session: Optional pre-built ``requests.Session`` — the
                test seam and the way a caller supplies custom transport
                adapters or proxies.
            :param timeout_seconds: The default per-request timeout.
        """
        self._token: str = token
        self._base_url: str = base_url.rstrip("/")
        self._timeout_seconds: float = timeout_seconds

        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()

        self._session.headers.update({
            "Authorization": "Bearer {}".format(token),
            "Accept": "application/json",
        })

        from ccai.restclient.linode.apigroups.instancegroup import (
            InstanceGroup
        )
        from ccai.restclient.linode.apigroups.volumegroup import VolumeGroup
        from ccai.restclient.linode.apigroups.vpcgroup import VpcGroup
        from ccai.restclient.linode.apigroups.networkinggroup import (
            NetworkingGroup
        )
        from ccai.restclient.linode.apigroups.objectstoragegroup import (
            ObjectStorageGroup
        )
        from ccai.restclient.linode.apigroups.domaingroup import DomainGroup
        from ccai.restclient.linode.apigroups.profilegroup import (
            ProfileGroup
        )

        self.linode: InstanceGroup = InstanceGroup(client=self)
        self.volumes: VolumeGroup = VolumeGroup(client=self)
        self.vpcs: VpcGroup = VpcGroup(client=self)
        self.networking: NetworkingGroup = NetworkingGroup(client=self)
        self.object_storage: ObjectStorageGroup = ObjectStorageGroup(
            client=self)
        self.domains: DomainGroup = DomainGroup(client=self)
        self.profile: ProfileGroup = ProfileGroup(client=self)
        return

    @property
    def base_url(self) -> str:
        """
            Return the API base URL.

            :returns: The base URL.
        """
        rtnval = self._base_url
        return rtnval

    def request(self, *, method: str, path: str,
                params: Optional[Dict[str, Any]] = None,
                body: Optional[Dict[str, Any]] = None,
                timeout_seconds: Optional[float] = None) -> LinodeObject:
        """
            Perform one API request and return the decoded body.

            :param method: The HTTP method.
            :param path: The API path, beginning with ``/``.
            :param params: Optional query parameters; ``None`` values are
                dropped.
            :param body: Optional JSON request body.
            :param timeout_seconds: Optional per-request timeout override.

            :returns: The decoded response as a :class:`LinodeObject`; an
                empty one when the response carries no body (deletes).

            :raises: :class:`LinodeApiRequestError` on a non-success status.
        """
        url = "{}{}".format(self._base_url, path)

        query: Dict[str, Any] = {}
        if params is not None:
            for key, value in params.items():
                if value is not None:
                    query[key] = value

        headers: Dict[str, str] = {}
        payload = None
        if body is not None:
            payload = json.dumps(body)
            headers["Content-Type"] = "application/json"

        timeout = timeout_seconds
        if timeout is None:
            timeout = self._timeout_seconds

        response = self._session.request(method, url, params=query,
                                         data=payload, headers=headers,
                                         timeout=timeout)

        status = getattr(response, "status_code", 0)

        if status < 200 or status >= 300:
            text = getattr(response, "text", "")
            reason = self._extract_error_reason(response=response,
                                               fallback=getattr(
                                                   response, "reason", ""))
            err_msg_lines = ["The Linode API request failed."]
            err_msg_lines.append("METHOD: {}".format(method))
            err_msg_lines.append("PATH: {}".format(path))
            err_msg_lines.append("STATUS: {}".format(status))
            err_msg_lines.append("REASON: {}".format(reason))
            err_msg = os.linesep.join(err_msg_lines)
            raise LinodeApiRequestError(err_msg, status=status,
                                        reason=reason, body=text)

        text = getattr(response, "text", "")
        if text is None or len(text.strip()) == 0:
            rtnval = LinodeObject()
            return rtnval

        try:
            decoded = response.json()
        except Exception:
            rtnval = LinodeObject()
            return rtnval

        wrapped = wrap_linode_value(decoded)
        if isinstance(wrapped, LinodeObject) is True:
            rtnval = wrapped
            return rtnval

        rtnval = LinodeObject({"data": wrapped})
        return rtnval

    def volume_create(self, *, label: str, region: Optional[str] = None,
                      size: Optional[int] = None,
                      tags: Optional[List[str]] = None,
                      linode: Optional[Any] = None,
                      **fields: Any) -> Any:
        """
            Create a block-storage volume.

            This lives on the client rather than the volumes group because
            that is where callers reach for it.

            :param label: The volume label.
            :param region: The region id.
            :param size: The size in GB.
            :param tags: Optional tags.
            :param linode: Optional instance to attach to — accepts an
                instance RESOURCE (whose id is read) or a bare id, because
                callers hold the object they just created.
            :param fields: Remaining volume fields.

            :returns: The created volume, as an active-record resource.
        """
        body: Dict[str, Any] = {"label": label}
        if region is not None:
            body["region"] = region
        if size is not None:
            body["size"] = size
        if tags is not None:
            body["tags"] = tags
        if linode is not None:
            linode_id = linode
            if isinstance(linode, dict) is True:
                linode_id = linode.get("id", None)
            elif hasattr(linode, "id") is True:
                linode_id = linode.id
            if linode_id is not None:
                body["linode_id"] = linode_id
        for key, value in fields.items():
            if value is not None:
                body[key] = value

        payload = self.request(method="POST", path="/volumes", body=body)

        from ccai.restclient.linode.linoderesource import (
            LinodeVolume, make_resource
        )
        rtnval = make_resource(payload=payload.as_dict(), client=self,
                               collection_path="/volumes",
                               resource_class=LinodeVolume)
        return rtnval

    def domain_create(self, *, domain: str, soa_email: str,
                      domain_type: str = "master", **fields: Any) -> Any:
        """
            Create a DNS domain.

            :param domain: The zone name.
            :param soa_email: The SOA contact address, which the API
                requires for a master zone.
            :param domain_type: The zone type; ``master`` by default.
            :param fields: Remaining domain fields.

            :returns: The created domain, as an active-record resource
                carrying ``record_create``.
        """
        body: Dict[str, Any] = {"domain": domain, "soa_email": soa_email,
                                "type": domain_type}
        for key, value in fields.items():
            if value is not None:
                body[key] = value

        payload = self.request(method="POST", path="/domains", body=body)

        from ccai.restclient.linode.linoderesource import (
            LinodeDomain, make_resource
        )
        rtnval = make_resource(payload=payload.as_dict(), client=self,
                               collection_path="/domains",
                               resource_class=LinodeDomain)
        return rtnval

    def _extract_error_reason(self, *, response: Any,
                              fallback: str) -> str:
        """
            Pull a human-readable reason out of a Linode error body.

            Linode reports failures as ``{"errors": [{"reason": ...,
            "field": ...}]}``; joining the reasons is far more useful than
            the bare HTTP phrase.

            :param response: The failed response.
            :param fallback: The reason to use when the body is unhelpful.

            :returns: The extracted reason.
        """
        try:
            decoded = response.json()
        except Exception:
            rtnval = fallback
            return rtnval

        if isinstance(decoded, dict) is False:
            rtnval = fallback
            return rtnval

        errors = decoded.get("errors", None)
        if errors is None or len(errors) == 0:
            rtnval = fallback
            return rtnval

        parts: List[str] = []
        for entry in errors:
            if isinstance(entry, dict) is False:
                parts.append(str(entry))
                continue
            reason = entry.get("reason", "")
            field = entry.get("field", None)
            if field is not None:
                parts.append("{}: {}".format(field, reason))
            else:
                parts.append(str(reason))

        rtnval = "; ".join(parts)
        return rtnval

    def paginate(self, *, path: str,
                 params: Optional[Dict[str, Any]] = None,
                 timeout_seconds: Optional[float] = None
                 ) -> List[Dict[str, Any]]:
        """
            Walk every page of a collection and return the concatenated
            entries.

            Linode paginates with ``page`` / ``pages`` and nests entries
            under ``data``.  Callers listing a collection expect ALL of it —
            a silently truncated first page would under-report owned
            resources, which for a teardown path means leaked infrastructure.

            :param path: The collection path.
            :param params: Optional query parameters.
            :param timeout_seconds: Optional per-request timeout override.

            :returns: The concatenated raw entries from every page.
        """
        collected: List[Dict[str, Any]] = []

        page_params: Dict[str, Any] = {}
        if params is not None:
            page_params.update(params)
        page_params["page_size"] = MAX_PAGE_SIZE

        page_number = 1
        while True:
            page_params["page"] = page_number
            payload = self.request(method="GET", path=path,
                                   params=page_params,
                                   timeout_seconds=timeout_seconds)

            entries = payload.get("data", None)
            if entries is None:
                break
            collected.extend(entries)

            total_pages = payload.get("pages", 1)
            try:
                total_pages = int(total_pages)
            except (TypeError, ValueError):
                total_pages = 1

            if page_number >= total_pages:
                break
            page_number = page_number + 1

        rtnval = collected
        return rtnval
