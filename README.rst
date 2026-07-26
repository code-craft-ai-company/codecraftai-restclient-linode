=================================
Code Craft AI - Linode REST client
=================================

A pure-Python client for the Linode (Akamai Cloud) API v4.

The Linode API is plain REST over HTTPS with JSON bodies and a Bearer
personal-access token, so this package speaks it directly rather than
depending on the ``linode_api4`` SDK — keeping the fleet's pure-Python
guarantee.

Design
======

**Api groups mirror the SDK's grouping** — ``linode`` (instances),
``volumes``, ``vpcs``, ``networking``, ``object_storage``, ``domains``,
``profile`` — and the collection groups are callable, so SDK-era call shapes
like ``client.volumes()`` and ``client.linode.instance_create(...)`` keep
working unchanged.

**Resources are active record.** A listed resource carries the client and
its own collection path, so ``volume.delete()``, ``volume.detach()`` and
``instance.resize(new_type=...)`` work without the caller tracking which
endpoint produced the object. That is how callers already work with these
objects, and it is what lets a consumer migrate off the SDK without
rewriting its teardown paths.

**Collections are fully walked.** Linode paginates with ``page``/``pages``;
list calls follow every page. A silently truncated first page would
under-report owned resources, which in a teardown path means leaked
infrastructure.

**Errors name the field.** Linode reports failures as an ``errors`` array
with ``field`` and ``reason``; ``LinodeApiRequestError.reason`` carries the
joined result rather than the bare HTTP phrase.
