# Design

## Overview

`LinodeRestClient` is a pure-Python client for the Linode (Akamai Connected
Cloud) API v4. The API is a bearer-token JSON surface with `page`/`page_size`
paging, so the client speaks it directly with `requests` rather than wrapping
the `linode_api4` SDK.

The package is three layers. `linoderestclient` owns the session, the single
request primitive, error-reason extraction, and pagination. `linoderesource`
holds the active-record object model. `apigroups/` declares the collections,
with `CollectionGroupBase` carrying the verbs that every collection shares.

The organising constraint is migration off the SDK: group names, call shapes,
and object behaviour are chosen so existing call sites keep working, and the
places where that costs something are called out below.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│  codecraftai-provisioning / venues / linode              │
│  (CloudProvisioner lifecycle)                          │
└──────────┬─────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  LinodeRestClient                                      │
│  ─ session + Bearer token                              │
│  ─ request(method, path, params, body)                 │
│  ─ paginate(path, params)  → walks every page          │
│  ─ volume_create / domain_create                       │
│  ─ linode volumes vpcs networking                      │
│    object_storage domains profile                      │
└──────────┬──────────────────────┬──────────────────────┘
           │ returns              │ HTTPS, Bearer token
           ▼                      ▼
┌────────────────────────┐  ┌────────────────────────────┐
│ LinodeResource         │  │  api.linode.com/v4         │
│ bound: client + path   │  └────────────────────────────┘
│ .delete() .detach()    │
│ .resize() .boot()      │
└────────────────────────┘
```

---

## Data Model

`LinodeObject` is a `dict` subclass that is also attribute addressable.
Linode returns snake_case fields, which is already the spelling Python
callers want, so unlike the Kubernetes client there is no camelCase
translation — attribute lookup is a plain key lookup with `None` for a miss.
Names beginning with `_` are excluded from field resolution in both
directions: `__getattr__` raises `AttributeError` for them so copy, pickle,
and inspection machinery do not see phantom attributes, and `__setattr__`
stores them as real instance attributes, which is what makes the active-record
binding below possible on a `dict` subclass.

The inherited `dict` methods are deliberately *not* shadowed by payload
fields. That is the opposite of the Kubernetes client's choice, and the
reason is that Linode nests collections under `data` rather than `items`, so
no payload field collides with a mapping method.

`LinodeResource` extends `LinodeObject` with a `bind(client, collection_path,
identifier_field)` that stores its origin, giving every resource a
`resource_path` and a `delete()`. The subclasses add the actions their kind
supports: `LinodeInstance` (`resize`, `boot`, `shutdown`), `LinodeVolume`
(`attach`, `detach`, `resize`), `LinodeVpc` (`subnet_create` and a `subnets`
property), `LinodeDomain` (`record_create`, `records`), and
`ObjectStorageBucket` — declared in `objectstoragegroup` — which overrides
`resource_path` to `<cluster>/<label>`. `make_resource` is the single
construction point, defaulting to `LinodeResource` and to `id` as the
identifier field.

`LinodeApiRequestError` carries `status`, `reason`, `body`.

---

## Notable Choices

**Active record, on purpose.** A resource holding its own client and path is
unusual for a transport layer, but it is how callers already work with these
objects. Keeping it means `volume.detach()` and `instance.resize(...)` call
sites survive the move off the SDK untouched.

**Nested arrays are bound, not returned raw.** `LinodeVpc.subnets` binds each
entry of the payload's embedded `subnets` array to the VPC's subnet
collection. Returning the raw array would hand back inert dicts, and a caller
doing `getattr(subnet, "delete", None)` would find nothing and silently skip
the delete — leaking subnets on teardown. When no array is embedded the
collection is fetched instead.

**Pagination is not optional.** `paginate` always asks for `page_size=500`
(the API cap) and walks to `pages`. There is no "first page only" mode,
because a truncated list in a teardown path means leaked infrastructure.

**Errors name the field.** Linode reports failures as an `errors` array of
`{field, reason}`. `_extract_error_reason` joins them into
`"field: reason; field: reason"`, which is far more useful than the bare HTTP
phrase, and falls back to that phrase whenever the body is not shaped as
expected.

**Two creates live on the client.** `volume_create` and `domain_create` sit
on `LinodeRestClient` rather than on their groups because that is where
callers reach for them. `volume_create` accepts an instance resource, a bare
dict, or an id for `linode=`, since the caller usually holds the object they
just created.

**Awkward API field names are aliased.** `type` is a Python builtin, so
instances take `ltype=` and domain records take `record_type=`; the literal
`type=` keyword still works through `**fields`. Buckets take
`cluster_or_region=` because Linode addressed buckets by object-storage
cluster historically and by region now.

**Groups differ in shape by design.** `VolumeGroup`, `VpcGroup`, and
`DomainGroup` are callable so `client.volumes()` lists. `InstanceGroup` is
not, because the SDK spelled that call `client.linode.instances()`.
`NetworkingGroup`, `ObjectStorageGroup`, and `ProfileGroup` do not extend
`CollectionGroupBase` at all — their paths are not a single flat collection
with the shared id convention.

---

## Module Layout

```
source/packages/ccai/restclient/linode/
├── __init__.py
├── linoderestclient.py        # LinodeRestClient, LINODE_API_BASE,
│                              #   MAX_PAGE_SIZE, DEFAULT_TIMEOUT_SECONDS
├── linoderesource.py          # LinodeObject, LinodeResource, subclasses,
│                              #   make_resource, wrap_linode_value
├── linodeapierror.py          # LinodeApiRequestError
└── apigroups/
    ├── __init__.py
    ├── collectiongroupbase.py # list_all / get / create / delete
    ├── instancegroup.py       # /linode/instances
    ├── volumegroup.py         # /volumes
    ├── vpcgroup.py            # /vpcs, /vpcs/<id>/subnets
    ├── networkinggroup.py     # /networking/firewalls
    ├── objectstoragegroup.py  # /object-storage/buckets
    ├── domaingroup.py         # /domains, /domains/<id>/records
    └── profilegroup.py        # /profile/sshkeys
```

---

## See Also

- `codecraftai-provisioning/specs/venue-linode/` — the provisioner that
  composes this client.
- `codecraftai-credentials/specs/linode-credentials/` — the credential type
  this client does not yet accept (see the open item in `tasks.md`).
- `codecraftai-restclient-base/specs/restapigroup-enhancements/` — the
  fleet's shared `RestApiGroup` shape.
- `codecraftai-testbase/specs/property-testing/` — `ccai.testbase.properties`,
  the fleet's property-testing library.

---

## Testing Strategy

Tests run under the testbase runner, not pytest:

```
PYTHONPATH="$PWD/source/packages:$PWD/source/testroots/testbase" \
    .venv/bin/testbase testing run --root source/testroots/testbase/ccai \
    --includes="*" --output=./.output
```

`FakeSession` / `FakeResponse` (`fakesession.py`) stand in for
`requests.Session`. `FakeSession` records every call and replays responses
queued per `(METHOD, path-suffix)`, so a test asserts on the URL, query
parameters, body, and headers of every request that was made. `queue_page`
builds a Linode paging envelope (`data`, `page`, `pages`, `results`), which
is what makes multi-page traversal directly testable.

`test_linoderestclient.py` covers the bearer header, per-group paths and call
shapes, multi-page traversal, the maximum page size, `None`-field dropping,
the `type`/`ltype` alias, error-reason extraction from the `errors` array, the
empty-body DELETE, `LinodeObject` attribute behaviour including the
underscore rule, active-record actions on instances and volumes, bucket path
composition, and both binding paths for VPC subnets — embedded and fetched.

No live API is required. Property-based coverage via
`ccai.testbase.properties` is not yet present — see `tasks.md`.
