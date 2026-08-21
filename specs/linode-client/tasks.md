# Implementation Plan — Linode Client

## Package Skeleton

- [x] 1. Create `source/packages/ccai/restclient/linode/` with the `apigroups/` subpackage.
- [x] 2. Declare the `requests` runtime dependency in `pyproject.toml`.

## Client Core

- [x] 3. Implement `LinodeRestClient(token=, base_url=, session=, timeout_seconds=)` with `LINODE_API_BASE`, `MAX_PAGE_SIZE = 500`, and `DEFAULT_TIMEOUT_SECONDS = 60.0`.
- [x] 4. Apply the `Authorization: Bearer` and `Accept` headers to the session, whether built or supplied.
- [x] 5. Expose the `base_url` property with any trailing `/` stripped.
- [x] 6. Implement `request()` with `None`-valued query parameters dropped and a JSON body encoded with `Content-Type: application/json`.
- [x] 7. Return an empty `LinodeObject` for an empty or undecodable body; wrap a non-object body as `{"data": ...}`.
- [x] 8. Implement `_extract_error_reason` joining the API's `errors` array as `"field: reason"`, falling back to the HTTP reason phrase.
- [x] 9. Raise `LinodeApiRequestError` on non-2xx, naming the method, path, status, and extracted reason.
- [x] 10. Implement `paginate()` walking `page` to `pages` at `page_size=MAX_PAGE_SIZE`, merging caller params, stopping on a missing `data` field and on a non-integer `pages`.
- [x] 11. Implement client-level `volume_create()`, resolving `linode=` from a resource, a dict, or a bare id into `linode_id`.
- [x] 12. Implement client-level `domain_create()` sending `domain_type` as `type` with a `master` default.

## Resource Model

- [x] 13. Implement `LinodeObject` with attribute access, `None` for a missing field, and `as_dict()`.
- [x] 14. Exclude underscore-prefixed names from field resolution — `AttributeError` on read, real instance attribute on write.
- [x] 15. Implement `wrap_linode_value` wrapping nested dicts and lists, and passing an already-wrapped value through.
- [x] 16. Implement `LinodeResource.bind()` returning `self`, plus `resource_path` and `delete()`.
- [x] 17. Implement `LinodeInstance.resize()`, `.boot()`, `.shutdown()`.
- [x] 18. Implement `LinodeVolume.attach()`, `.detach()`, `.resize()`.
- [x] 19. Implement `LinodeVpc.subnet_create()` and the `subnets` property, binding the embedded array and fetching the collection when it is absent.
- [x] 20. Implement `LinodeDomain.record_create()` and `.records()`, aliasing the API's `type` field as `record_type`.
- [x] 21. Implement `make_resource()` as the single construction point, defaulting to `LinodeResource` and `id`.

## Errors

- [x] 22. Implement `LinodeApiRequestError` with `status` / `reason` / `body`.

## API Groups

- [x] 23. Implement `CollectionGroupBase` with `list_all` / `get` / `create` / `delete`, dropping `None`-valued create fields.
- [x] 24. Implement `InstanceGroup` (`/linode/instances`) with `instances()`, `instance_create()` accepting the `ltype` alias, and `instance_delete()`.
- [x] 25. Implement `VolumeGroup` (`/volumes`), callable for listing.
- [x] 26. Implement `VpcGroup` (`/vpcs`), callable for listing, with `subnets()` and `subnet_create()`.
- [x] 27. Implement `DomainGroup` (`/domains`), callable for listing, with `records()` and `record_create()`.
- [x] 28. Implement `NetworkingGroup` with `firewalls()` and `firewall_create()` against `/networking/firewalls`.
- [x] 29. Implement `ObjectStorageGroup` with `buckets()` and `bucket_create()`, and `ObjectStorageBucket` addressing `<cluster>/<label>` with a `region` fallback.
- [x] 30. Implement `ProfileGroup` with `ssh_keys()` and `ssh_key_upload()` against `/profile/sshkeys`.

## Tests

- [x] 31. Implement `FakeSession` / `FakeResponse` with `queue()` and `queue_page()` for the Linode paging envelope.
- [x] 32. Transport tests: bearer header, `None`-field dropping, error-reason extraction, empty-body DELETE.
- [x] 33. Paging tests: multi-page traversal and the maximum page size.
- [x] 34. Group tests: per-group paths, callable groups, the `ltype` alias, firewall and SSH-key bodies, bucket path composition.
- [x] 35. Resource tests: self-delete, volume detach, instance resize, both VPC subnet binding paths, nested attribute addressability, the underscore rule.
- [x] 36. Client-level create tests: volume attachment from a resource, from a bare id, and omitted; domain create and record creation on the returned domain.
- [x] 37. Migrate the suite from pytest to testbase — `testbase.raises`, `testbase.parametrize`, standard-library replacements for `monkeypatch` and `tmp_path`.

## Open

- [ ] 38. Accept a typed credential instead of a raw token. The repository standard is that credentials enter as typed objects from `codecraftai-credentials` and that raw key material is never on the API surface; `LinodeRestClient` takes `token: str`. `codecraftai-credentials/specs/linode-credentials/` already defines the type.
- [ ] 39. Reconcile with the repository coding standard that every behaviour-bearing method takes a named-only `aspects` parameter. The client exposes `timeout_seconds` instead and has no aspects type, so retry, backoff, and logging policy are not caller-controlled.
- [ ] 40. Reconcile the declared dependencies with the imports. `pyproject.toml` requires `codecraftai-restclient-base`, `codecraftai-credentials`, and `codecraftai-errors`, but the package imports none of them — nothing derives from `RestClientBase` and no `ccai.errors` exception type is raised. Either adopt them or drop the dependencies.
- [ ] 41. Implement or remove the `regions` and `types` groups. The `LinodeRestClient` class docstring lists them among the public attributes, but neither is constructed in `__init__` and no group module exists, so `client.regions` raises `AttributeError`. Region and plan-type lookup is unavailable.
- [ ] 42. Add image support. There is no images group, so a custom image cannot be listed, created, or deleted through this client — only referenced by id when creating an instance.
- [ ] 43. Add a way to wait on long-running work. Linode reports progress through `/account/events` and resource `status` fields; nothing here polls, so `instance.resize()` returns on acceptance and the caller has no supported way to learn when it finished. This is where an `ITaskHandle` implementation would attach.
- [ ] 44. Extend instance coverage. Disks, configs, backups, IP addresses, and the `/linode/instances/<id>/firewalls` view are not reachable.
- [ ] 45. Add property-based tests with `ccai.testbase.properties` — the strongest candidate is `paginate` totality: for any sequence of mock pages, the concatenation must contain every entry exactly once, in order. The `hypothesis` library is not used; the fleet ships its own.
- [ ] 46. Remove the unused `requests-mock` dev dependency, or use it. The suite is built entirely on `FakeSession`.
