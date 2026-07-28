"""
    .. module:: test_linoderestclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Tests for the Linode REST client — auth, request shaping,
               pagination, error extraction, and the active-record surface
               the provisioning venue relies on.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from ccai import testbase

from ccai.restclient.linode.linodeapierror import LinodeApiRequestError
from ccai.restclient.linode.linoderesource import (
    LinodeInstance, LinodeObject, LinodeVolume, LinodeVpc
)
from ccai.restclient.linode.linoderestclient import (
    LinodeRestClient, MAX_PAGE_SIZE
)

from ccai.tests.restclient.linode.fakesession import (
    FakeResponse, FakeSession
)


def _client(session=None):
    if session is None:
        session = FakeSession()
    rtnval = LinodeRestClient(token="tkn-123", session=session)
    return rtnval


def test_token_becomes_a_bearer_header():
    """
        The token is sent as an Authorization header.
    """
    session = FakeSession()
    _client(session=session)
    assert session.headers["Authorization"] == "Bearer tkn-123"
    return


def test_instances_are_listed_from_the_instance_path():
    """
        client.linode.instances() reads /linode/instances.
    """
    session = FakeSession()
    session.queue_page(path="/linode/instances",
                       entries=[{"id": 1, "label": "vm-a"}])
    client = _client(session=session)

    instances = client.linode.instances()

    assert len(instances) == 1
    assert instances[0].label == "vm-a"
    assert session.calls[-1]["url"].endswith("/linode/instances")
    return


def test_volumes_group_is_callable():
    """
        client.volumes() lists volumes — the SDK-era call shape.
    """
    session = FakeSession()
    session.queue_page(path="/volumes", entries=[{"id": 9, "label": "v1"}])
    client = _client(session=session)

    volumes = client.volumes()

    assert len(volumes) == 1
    assert isinstance(volumes[0], LinodeVolume)
    return


def test_vpcs_group_is_callable_and_creates():
    """
        client.vpcs() lists while client.vpcs.create() creates.
    """
    session = FakeSession()
    session.queue_page(path="/vpcs", entries=[{"id": 3, "label": "net"}])
    session.queue(method="POST", path="/vpcs",
                  response=FakeResponse(payload={"id": 4,
                                                 "label": "made"}))
    client = _client(session=session)

    listed = client.vpcs()
    created = client.vpcs.create(label="made", region="us-east")

    assert listed[0].label == "net"
    assert created.id == 4
    assert session.calls[-1]["body"] == {"label": "made",
                                         "region": "us-east"}
    return


def test_pagination_follows_every_page():
    """
        A multi-page collection is walked to the end.

        Under-reporting a collection would mean a teardown path missing
        owned resources, so this is load-bearing rather than cosmetic.
    """
    session = FakeSession()
    session.queue_page(path="/volumes", entries=[{"id": 1}], page=1,
                       pages=3)
    session.queue_page(path="/volumes", entries=[{"id": 2}], page=2,
                       pages=3)
    session.queue_page(path="/volumes", entries=[{"id": 3}], page=3,
                       pages=3)
    client = _client(session=session)

    volumes = client.volumes()

    assert [v.id for v in volumes] == [1, 2, 3]
    assert len(session.calls) == 3
    return


def test_pagination_requests_the_maximum_page_size():
    """
        Collections are walked with the largest page the API allows, to
        minimise round trips.
    """
    session = FakeSession()
    session.queue_page(path="/volumes", entries=[])
    client = _client(session=session)

    client.volumes()

    assert session.calls[-1]["params"]["page_size"] == MAX_PAGE_SIZE
    return


def test_none_valued_create_fields_are_dropped():
    """
        An unset optional field is absent from the body rather than sent as
        an explicit null, which the API would reject.
    """
    session = FakeSession()
    session.queue(method="POST", path="/vpcs",
                  response=FakeResponse(payload={"id": 1}))
    client = _client(session=session)

    client.vpcs.create(label="net", region=None)

    assert session.calls[-1]["body"] == {"label": "net"}
    return


def test_instance_create_maps_the_type_alias():
    """
        instance_create accepts ltype= and sends it as the API's 'type'.
    """
    session = FakeSession()
    session.queue(method="POST", path="/linode/instances",
                  response=FakeResponse(payload={"id": 7}))
    client = _client(session=session)

    client.linode.instance_create(ltype="g6-standard-2", region="us-east",
                                  label="vm")

    body = session.calls[-1]["body"]
    assert body["type"] == "g6-standard-2"
    assert body["region"] == "us-east"
    return


def test_firewall_create_sends_rules_and_tags():
    """
        Firewall creation carries its rule document and tags.
    """
    session = FakeSession()
    session.queue(method="POST", path="/networking/firewalls",
                  response=FakeResponse(payload={"id": 11}))
    client = _client(session=session)

    rules = {"inbound": [], "outbound": []}
    client.networking.firewall_create(label="fw", rules=rules,
                                      tags=["owner:ccai"])

    body = session.calls[-1]["body"]
    assert body["rules"] == rules
    assert body["tags"] == ["owner:ccai"]
    return


def test_ssh_key_upload_uses_the_api_field_name():
    """
        The API field is ssh_key, though callers pass key=.
    """
    session = FakeSession()
    session.queue(method="POST", path="/profile/sshkeys",
                  response=FakeResponse(payload={"id": 2}))
    client = _client(session=session)

    client.profile.ssh_key_upload(key="ssh-ed25519 AAA", label="kp")

    body = session.calls[-1]["body"]
    assert body["ssh_key"] == "ssh-ed25519 AAA"
    assert body["label"] == "kp"
    return


def test_resource_delete_targets_its_own_item_path():
    """
        A listed resource deletes itself — the active-record contract the
        venue's teardown depends on.
    """
    session = FakeSession()
    session.queue_page(path="/volumes", entries=[{"id": 42, "label": "v"}])
    client = _client(session=session)

    volume = client.volumes()[0]
    volume.delete()

    call = session.calls[-1]
    assert call["method"] == "DELETE"
    assert call["url"].endswith("/volumes/42")
    return


def test_volume_detach_posts_to_the_detach_action():
    """
        volume.detach() posts to the volume's detach action.
    """
    session = FakeSession()
    session.queue_page(path="/volumes", entries=[{"id": 42}])
    client = _client(session=session)

    client.volumes()[0].detach()

    call = session.calls[-1]
    assert call["method"] == "POST"
    assert call["url"].endswith("/volumes/42/detach")
    return


def test_instance_resize_posts_the_new_type():
    """
        instance.resize(new_type=...) posts the target plan.
    """
    session = FakeSession()
    session.queue_page(path="/linode/instances", entries=[{"id": 5}])
    client = _client(session=session)

    client.linode.instances()[0].resize(new_type="g6-standard-4")

    call = session.calls[-1]
    assert call["url"].endswith("/linode/instances/5/resize")
    assert call["body"]["type"] == "g6-standard-4"
    return


def test_bucket_path_uses_cluster_and_label():
    """
        Buckets are addressed by cluster/label, not a numeric id, so a
        bucket must delete itself at the right path.
    """
    session = FakeSession()
    session.queue_page(path="/object-storage/buckets",
                       entries=[{"label": "assets",
                                 "cluster": "us-east-1"}])
    client = _client(session=session)

    bucket = client.object_storage.buckets()[0]
    bucket.delete()

    assert session.calls[-1]["url"].endswith(
        "/object-storage/buckets/us-east-1/assets")
    return


def test_vpc_subnets_are_nested_and_deletable():
    """
        Subnets bind to their VPC's subnet collection.
    """
    session = FakeSession()
    session.queue_page(path="/vpcs/3/subnets", entries=[{"id": 8}])
    client = _client(session=session)

    subnet = client.vpcs.subnets(vpc_id=3)[0]
    subnet.delete()

    assert session.calls[-1]["url"].endswith("/vpcs/3/subnets/8")
    return


def test_error_reason_comes_from_the_errors_array():
    """
        Linode reports failures in an errors array; the message names the
        offending field, which is far more useful than the HTTP phrase.
    """
    session = FakeSession()
    session.queue(method="POST", path="/vpcs",
                  response=FakeResponse(
                      status_code=400, reason="Bad Request",
                      payload={"errors": [{"field": "label",
                                           "reason": "Label must be unique"}]}))
    client = _client(session=session)

    with testbase.raises(LinodeApiRequestError) as caught:
        client.vpcs.create(label="dupe")

    error = caught.value
    assert error.status == 400
    assert "label" in error.reason
    assert "unique" in error.reason
    return


def test_empty_delete_response_is_not_an_error():
    """
        Linode returns an empty body for deletes.
    """
    session = FakeSession()
    session.queue(method="DELETE", path="/volumes/1",
                  response=FakeResponse(status_code=200, text=""))
    client = _client(session=session)

    result = client.volumes.delete(identifier=1)
    assert result is None
    return


def test_missing_field_reads_as_none():
    """
        An absent field reads as None so getattr guards in the venue keep
        working.
    """
    obj = LinodeObject({"label": "x"})
    assert obj.region is None
    assert obj.label == "x"
    return


def test_private_attribute_lookup_does_not_become_a_field():
    """
        Dunder/private lookups must raise AttributeError rather than
        resolving to None, or copy/inspect machinery sees phantom
        attributes.
    """
    obj = LinodeObject({"label": "x"})
    with testbase.raises(AttributeError):
        obj.__deepcopy__
    return


def test_nested_objects_stay_attribute_addressable():
    """
        Nested payloads keep attribute access.
    """
    session = FakeSession()
    session.queue_page(path="/linode/instances",
                       entries=[{"id": 1,
                                 "specs": {"vcpus": 4, "memory": 8192}}])
    client = _client(session=session)

    instance = client.linode.instances()[0]
    assert instance.specs.vcpus == 4
    return


def test_instances_are_active_record_instances():
    """
        The instance group returns LinodeInstance, so resize/boot exist.
    """
    session = FakeSession()
    session.queue_page(path="/linode/instances", entries=[{"id": 1}])
    client = _client(session=session)

    instance = client.linode.instances()[0]
    assert isinstance(instance, LinodeInstance)
    assert callable(instance.resize)
    return


def test_domains_group_lists_and_creates_records():
    """
        Domains list, and records nest under their domain.
    """
    session = FakeSession()
    session.queue_page(path="/domains", entries=[{"id": 6,
                                                  "domain": "ex.com"}])
    session.queue(method="POST", path="/domains/6/records",
                  response=FakeResponse(payload={"id": 77}))
    client = _client(session=session)

    domains = client.domains()
    record = client.domains.record_create(domain_id=6, type="A",
                                          name="www", target="1.2.3.4")

    assert domains[0].domain == "ex.com"
    assert record.id == 77
    assert session.calls[-1]["body"]["type"] == "A"
    return


def test_client_level_volume_create_accepts_an_instance_handle():
    """
        volume_create's linode= takes the instance OBJECT callers already
        hold, and sends its id as linode_id.
    """
    session = FakeSession()
    session.queue_page(path="/linode/instances", entries=[{"id": 55}])
    session.queue(method="POST", path="/volumes",
                  response=FakeResponse(payload={"id": 90}))
    client = _client(session=session)

    instance = client.linode.instances()[0]
    created = client.volume_create(label="data", region="us-east", size=20,
                                   tags=["owner:ccai"], linode=instance)

    body = session.calls[-1]["body"]
    assert body["linode_id"] == 55
    assert body["size"] == 20
    assert isinstance(created, LinodeVolume)
    return


def test_client_level_volume_create_accepts_a_bare_id():
    """
        A bare id works too, so callers are not forced to hold an object.
    """
    session = FakeSession()
    session.queue(method="POST", path="/volumes",
                  response=FakeResponse(payload={"id": 91}))
    client = _client(session=session)

    client.volume_create(label="data", linode=77)

    assert session.calls[-1]["body"]["linode_id"] == 77
    return


def test_volume_create_omits_attachment_when_absent():
    """
        An unattached volume must not send linode_id at all.
    """
    session = FakeSession()
    session.queue(method="POST", path="/volumes",
                  response=FakeResponse(payload={"id": 92}))
    client = _client(session=session)

    client.volume_create(label="data", region="us-east", size=10)

    assert "linode_id" not in session.calls[-1]["body"]
    return


def test_client_level_domain_create_sends_the_required_soa():
    """
        A master zone requires an SOA contact; the type defaults to master.
    """
    session = FakeSession()
    session.queue(method="POST", path="/domains",
                  response=FakeResponse(payload={"id": 30,
                                                 "domain": "ex.com"}))
    client = _client(session=session)

    domain = client.domain_create(domain="ex.com",
                                  soa_email="admin@ex.com")

    body = session.calls[-1]["body"]
    assert body["domain"] == "ex.com"
    assert body["soa_email"] == "admin@ex.com"
    assert body["type"] == "master"
    assert domain.id == 30
    return


def test_created_domain_can_create_records_on_itself():
    """
        The venue calls domain.record_create(record_type=...) on the object
        it just created, so the created domain must be active record and map
        record_type onto the API's 'type'.
    """
    session = FakeSession()
    session.queue(method="POST", path="/domains",
                  response=FakeResponse(payload={"id": 31}))
    session.queue(method="POST", path="/domains/31/records",
                  response=FakeResponse(payload={"id": 300}))
    client = _client(session=session)

    domain = client.domain_create(domain="ex.com", soa_email="a@ex.com")
    record = domain.record_create(record_type="A", name="www",
                                  target="1.2.3.4", ttl_sec=300)

    call = session.calls[-1]
    assert call["url"].endswith("/domains/31/records")
    assert call["body"]["type"] == "A"
    assert call["body"]["ttl_sec"] == 300
    assert record.id == 300
    return


def test_listed_domain_is_also_active_record():
    """
        A domain found by the reader (via client.domains()) must carry
        record_create too — apply uses whichever it gets.
    """
    session = FakeSession()
    session.queue_page(path="/domains", entries=[{"id": 32,
                                                  "domain": "ex.com"}])
    session.queue(method="POST", path="/domains/32/records",
                  response=FakeResponse(payload={"id": 301}))
    client = _client(session=session)

    domain = client.domains()[0]
    domain.record_create(record_type="CNAME", name="alias",
                         target="ex.com")

    assert session.calls[-1]["url"].endswith("/domains/32/records")
    return


def test_vpcs_come_back_as_vpc_resources():
    """
        Listed and created VPCs carry the VPC verbs.

        The provisioning venue calls subnet_create on whatever the vpcs group
        hands back.  A plain LinodeResource has no such method, so binding the
        VPC resource class is what makes the venue work against the live API —
        and nothing else in this suite pins it.
    """
    session = FakeSession()
    session.queue_page(path="/vpcs", entries=[{"id": 3, "label": "net"}])
    session.queue(method="POST", path="/vpcs",
                  response=FakeResponse(payload={"id": 4, "label": "made"}))
    client = _client(session=session)

    listed = client.vpcs()
    created = client.vpcs.create(label="made", region="us-east")

    assert isinstance(listed[0], LinodeVpc) is True
    assert isinstance(created, LinodeVpc) is True
    assert callable(created.subnet_create) is True
    return


def test_vpc_subnet_create_posts_under_the_vpc():
    session = FakeSession()
    session.queue(method="POST", path="/vpcs/3/subnets",
                  response=FakeResponse(payload={"id": 11,
                                                 "label": "sub-a"}))
    client = _client(session=session)
    vpc = LinodeVpc({"id": 3, "label": "net"}).bind(
        client=client, collection_path="/vpcs")

    subnet = vpc.subnet_create(label="sub-a", ipv4="10.0.1.0/24")

    assert session.calls[-1]["body"] == {"label": "sub-a",
                                         "ipv4": "10.0.1.0/24"}
    assert subnet.id == 11
    # The subnet must be able to delete itself, or teardown leaks it.
    assert subnet.resource_path == "/vpcs/3/subnets/11"
    return


def test_vpc_subnets_bind_the_embedded_array():
    """
        Subnets embedded in a VPC payload come back deletable.

        Returning the raw array would hand back inert dicts, and a caller
        doing getattr(subnet, "delete", None) would find nothing and silently
        skip the delete — leaking subnets on teardown.
    """
    client = _client()
    vpc = LinodeVpc({"id": 3, "label": "net",
                     "subnets": [{"id": 11, "label": "sub-a"},
                                 {"id": 12, "label": "sub-b"}]}).bind(
        client=client, collection_path="/vpcs")

    subnets = vpc.subnets

    assert [entry.id for entry in subnets] == [11, 12]
    for entry in subnets:
        assert callable(entry.delete) is True
    assert subnets[0].resource_path == "/vpcs/3/subnets/11"
    return


def test_vpc_subnets_are_fetched_when_not_embedded():
    session = FakeSession()
    session.queue_page(path="/vpcs/3/subnets",
                       entries=[{"id": 21, "label": "fetched"}])
    client = _client(session=session)
    vpc = LinodeVpc({"id": 3, "label": "net"}).bind(
        client=client, collection_path="/vpcs")

    subnets = vpc.subnets

    assert [entry.id for entry in subnets] == [21]
    return


def test_bucket_create_sends_cluster_or_region_as_region():
    """
        The unified cluster_or_region spelling is sent as region.

        Linode addressed buckets by object-storage cluster historically and by
        region in the current API; callers pass one value without caring which
        era it came from.
    """
    session = FakeSession()
    session.queue(method="POST", path="/object-storage/buckets",
                  response=FakeResponse(payload={"label": "b1",
                                                 "region": "us-east"}))
    client = _client(session=session)

    client.object_storage.bucket_create(label="b1",
                                        cluster_or_region="us-east")

    body = session.calls[-1]["body"]
    assert body["region"] == "us-east"
    assert body["label"] == "b1"
    assert "cluster_or_region" not in body
    return
