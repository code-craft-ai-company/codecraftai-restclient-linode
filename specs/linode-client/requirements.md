# Requirements

## Introduction

The `linode-client` feature provides a pure-Python REST client for the Linode
(Akamai Connected Cloud) API v4. The API is plain REST over HTTPS with JSON
bodies and a Bearer personal-access token, so this package speaks it directly
rather than depending on the `linode_api4` SDK — keeping the fleet's
pure-Python guarantee.

Three decisions shape the surface. The api groups are named the way the SDK
named them — `linode` (instances), `volumes`, `vpcs`, `networking`,
`object_storage`, `domains`, `profile` — and the collection groups are
callable, so SDK-era call shapes like `client.volumes()` and
`client.linode.instance_create(...)` keep working unchanged. Resources are
active record: a listed resource carries the client and its own collection
path, so `volume.delete()`, `volume.detach()`, and
`instance.resize(new_type=...)` work without the caller tracking which
endpoint produced the object. And collections are always fully walked,
because a silently truncated first page would under-report owned resources —
which on a teardown path means leaked infrastructure.

This client is consumed by `codecraftai-provisioning/venues/linode/`.

---

## Requirements

### Requirement 1: Authenticate With a Personal Access Token

**User Story:** As a venue provisioner, I want the client to carry a Linode
personal access token so that every request is authorised without per-call
handling.

#### Acceptance Criteria

1. WHEN the caller constructs a `LinodeRestClient` with `token=` THE SYSTEM
   SHALL set the `Authorization: Bearer <token>` and
   `Accept: application/json` headers on the session.
2. THE SYSTEM SHALL default the base URL to `LINODE_API_BASE`
   (`https://api.linode.com/v4`), SHALL accept a `base_url=` override, and
   SHALL strip any trailing `/` from it.
3. THE SYSTEM SHALL accept a caller-supplied `session=` object — both the
   test seam and the way a caller supplies custom transport adapters or
   proxies — and SHALL apply the headers to it as well as to one it builds
   itself.

### Requirement 2: Shape and Issue API Requests

**User Story:** As an api group, I want one request primitive with uniform
semantics so that each group is a declaration of its paths rather than a
repetition of HTTP handling.

#### Acceptance Criteria

1. THE SYSTEM SHALL expose `LinodeRestClient.request(method, path, params,
   body, timeout_seconds)` as named-only parameters and SHALL compose the URL
   from the base URL and the supplied path.
2. WHEN a query parameter's value is `None` THE SYSTEM SHALL drop it.
3. WHEN a body is supplied THE SYSTEM SHALL JSON-encode it and set
   `Content-Type: application/json`.
4. WHEN `timeout_seconds` is not supplied THE SYSTEM SHALL apply the client's
   default of `DEFAULT_TIMEOUT_SECONDS` (60.0 seconds).
5. WHEN the response carries no body — as a successful DELETE does — or the
   body does not decode as JSON, THE SYSTEM SHALL return an empty
   `LinodeObject` rather than treating it as a failure.
6. WHEN the decoded body is not a JSON object THE SYSTEM SHALL return it
   wrapped as `LinodeObject({"data": <value>})`.

### Requirement 3: Walk Every Page of a Collection

**User Story:** As a caller listing owned resources, I want every page
followed so that a teardown path never misses infrastructure that exists.

#### Acceptance Criteria

1. THE SYSTEM SHALL expose `paginate(path, params, timeout_seconds)`
   returning the concatenated raw entries from every page.
2. THE SYSTEM SHALL request `page_size=MAX_PAGE_SIZE` (500, the API's cap)
   so that walking a collection costs the fewest round trips.
3. THE SYSTEM SHALL read entries from the response's `data` field and the
   page count from its `pages` field, requesting `page=1`, `page=2`, and so
   on until the current page number reaches the reported total.
4. WHEN the response carries no `data` field THE SYSTEM SHALL stop walking.
5. WHEN `pages` is absent or not coercible to an integer THE SYSTEM SHALL
   treat the collection as a single page rather than raising or looping.
6. THE SYSTEM SHALL merge any caller-supplied params with the paging params
   rather than discarding them.

### Requirement 4: Report Failures With the Offending Field

**User Story:** As a caller, I want a failed request to say which field the
API rejected so that a bad create is diagnosable without reading the raw body.

#### Acceptance Criteria

1. WHEN the response status is outside the 2xx range THE SYSTEM SHALL raise
   `LinodeApiRequestError` carrying `status`, `reason`, and `body`.
2. WHEN the error body carries Linode's `errors` array THE SYSTEM SHALL
   render each entry as `"<field>: <reason>"` when a field is named and as
   the bare reason otherwise, joining the entries with `"; "`.
3. WHEN the body does not decode, is not a JSON object, or carries no
   non-empty `errors` array THE SYSTEM SHALL fall back to the HTTP reason
   phrase.
4. THE error message SHALL name the method, path, status, and reason.

### Requirement 5: Return Attribute-Addressable Objects

**User Story:** As a consumer migrating off the SDK, I want response fields
readable as attributes so that field access does not have to be rewritten.

#### Acceptance Criteria

1. THE SYSTEM SHALL return decoded payloads as `LinodeObject`, a `dict`
   subclass resolving `obj.label` and `obj["label"]` alike.
2. WHEN a field is absent THE SYSTEM SHALL return `None` rather than raising,
   so `getattr(obj, "field", None)` guards behave as they did against the SDK.
3. WHEN an attribute name begins with `_` THE SYSTEM SHALL raise
   `AttributeError` on read rather than resolving it as an API field, and
   SHALL store it as a real instance attribute on write — so copy, pickle,
   and inspection machinery do not see phantom attributes.
4. THE SYSTEM SHALL wrap nested dicts and lists on access via
   `wrap_linode_value`, and SHALL leave an already-wrapped value unchanged.
5. THE SYSTEM SHALL expose `as_dict()` returning the plain wire-shaped
   dictionary.
6. THE SYSTEM SHALL NOT shadow the inherited `dict` methods with payload
   fields, because Linode nests collections under `data` and no payload uses
   those names.

### Requirement 6: Active-Record Resources

**User Story:** As a caller holding a resource I just listed or created, I
want to act on it directly so that I do not have to remember which endpoint
produced it.

#### Acceptance Criteria

1. THE SYSTEM SHALL bind every returned resource to its owning client, its
   collection path, and the field carrying its identifier via
   `LinodeResource.bind`, and `bind` SHALL return `self` so construction can
   chain.
2. THE SYSTEM SHALL expose `resource_path` composing the item path from the
   collection path and the identifier field, which defaults to `id`.
3. THE SYSTEM SHALL expose `delete()` on every resource, issuing a DELETE to
   its own item path.
4. THE SYSTEM SHALL expose `LinodeInstance.resize(new_type,
   allow_auto_disk_resize)`, `.boot()`, and `.shutdown()`, and
   `LinodeVolume.attach(linode_id)`, `.detach()`, `.resize(size)` — each
   POSTing to the corresponding action path under the resource.
5. THE SYSTEM SHALL expose `LinodeVpc.subnet_create(label, ipv4)` and a
   `subnets` property; the property SHALL bind the VPC payload's embedded
   `subnets` array to the VPC's subnet collection so each entry can delete
   itself, and SHALL fetch the collection when no array is embedded. Handing
   back inert dicts would make a caller's `getattr(subnet, "delete", None)`
   find nothing and silently skip the delete.
6. THE SYSTEM SHALL expose `LinodeDomain.record_create(record_type, name,
   target, ttl_sec)` and `.records()`, binding results to the domain's record
   collection. The parameter is `record_type` because the API field `type` is
   a Python builtin and an awkward keyword.
7. THE SYSTEM SHALL build resources through `make_resource`, defaulting to
   `LinodeResource` when no resource class is named.

### Requirement 7: Collection Groups Named as the SDK Named Them

**User Story:** As a caller with existing call sites, I want the group names
and call shapes preserved so that migrating off the SDK does not mean
rewriting every call.

#### Acceptance Criteria

1. THE SYSTEM SHALL expose `linode`, `volumes`, `vpcs`, `networking`,
   `object_storage`, `domains`, and `profile` as public client attributes.
2. THE SYSTEM SHALL provide `CollectionGroupBase` with `list_all(params)`,
   `get(identifier)`, `create(**fields)`, and `delete(identifier)`, each
   returning bound active-record resources where a resource is returned.
3. WHEN `create` is given a field whose value is `None` THE SYSTEM SHALL drop
   it, so an unset optional field is absent rather than explicitly null.
4. THE SYSTEM SHALL make `volumes`, `vpcs`, and `domains` callable so
   `client.volumes()`, `client.vpcs()`, and `client.domains()` list their
   collections.
5. THE SYSTEM SHALL expose `client.linode.instances()`,
   `.instance_create(ltype, region, **fields)`, and
   `.instance_delete(instance_id)` against `/linode/instances`. `ltype` is
   accepted as an alias for the API's `type` field, and a literal `type=`
   keyword SHALL still work.
6. THE SYSTEM SHALL expose `client.networking.firewalls()` and
   `.firewall_create(label, rules, tags, **fields)` against
   `/networking/firewalls`.
7. THE SYSTEM SHALL expose `client.profile.ssh_keys()` and
   `.ssh_key_upload(key, label)` against `/profile/sshkeys`, sending the
   material as the API's `ssh_key` field.
8. THE SYSTEM SHALL expose `client.domains.records(domain_id)` and
   `.record_create(domain_id, **fields)`, and `client.vpcs.subnets(vpc_id)`
   and `.subnet_create(vpc_id, label, ipv4)`.

### Requirement 8: Object-Storage Buckets Addressed by Cluster and Label

**User Story:** As a caller managing buckets, I want them addressed correctly
even though they do not have a numeric id so that bucket teardown works like
every other resource's.

#### Acceptance Criteria

1. THE SYSTEM SHALL address a bucket's item path as
   `/object-storage/buckets/<cluster>/<label>`, falling back to the payload's
   `region` when it carries no `cluster`.
2. THE SYSTEM SHALL bind buckets with `label` as the identifier field rather
   than the shared `id` convention.
3. THE SYSTEM SHALL expose `client.object_storage.buckets()` and
   `.bucket_create(label, cluster_or_region, cluster, region, **fields)`.
4. THE SYSTEM SHALL send `cluster_or_region` as the API's `region` field,
   which is what the current API expects; the explicit `cluster` and
   `region` parameters remain for callers that know which they mean.

### Requirement 9: Client-Level Creates for the Calls Callers Reach For

**User Story:** As a caller creating a volume or a zone, I want the call
where I already look for it so that the group indirection is not in the way.

#### Acceptance Criteria

1. THE SYSTEM SHALL expose `LinodeRestClient.volume_create(label, region,
   size, tags, linode, **fields)` returning a bound `LinodeVolume`.
2. WHEN `linode=` is supplied THE SYSTEM SHALL accept either an instance
   resource — reading its `id`, whether by mapping key or attribute — or a
   bare id, because callers hold the object they just created; the resolved
   value SHALL be sent as `linode_id`.
3. WHEN `linode=` is absent THE SYSTEM SHALL omit `linode_id` from the body.
4. THE SYSTEM SHALL expose `LinodeRestClient.domain_create(domain,
   soa_email, domain_type, **fields)` returning a bound `LinodeDomain`,
   sending `domain_type` as the API's `type` field and defaulting it to
   `master`. `soa_email` is required because the API requires it for a
   master zone.
5. THE SYSTEM SHALL drop `None`-valued keyword fields from both bodies.
