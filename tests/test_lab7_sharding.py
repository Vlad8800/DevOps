from uuid import NAMESPACE_DNS, uuid5

from lab7.sharding import BUCKET_COUNT, SHARDS, movement_fraction, route_event


def test_routes_are_deterministic_and_can_be_recomputed_for_reads():
    identifier = str(uuid5(NAMESPACE_DNS, "example-event"))
    route = route_event(42, identifier, "bucket")
    assert route == route_event(42, identifier, "bucket")
    assert route.shard in SHARDS
    assert 0 <= route.bucket < BUCKET_COUNT


def test_composite_key_distributes_hot_tenant_while_tenant_modulo_does_not():
    identifiers = [str(uuid5(NAMESPACE_DNS, f"hot-event-{index}")) for index in range(1000)]
    naive = {route_event(2, identifier, "naive").shard for identifier in identifiers}
    optimized = [route_event(2, identifier, "bucket").shard for identifier in identifiers]
    assert naive == {"shard_a"}
    assert 350 < optimized.count("shard_a") < 650


def test_new_shard_moves_only_its_virtual_buckets():
    fraction = movement_fraction(BUCKET_COUNT, SHARDS, SHARDS + ("shard_c",))
    assert 0.2 < fraction < 0.5
