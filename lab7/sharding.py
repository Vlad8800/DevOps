"""Deterministic routing for the TrackHub event dataset."""

from dataclasses import dataclass
from hashlib import sha256

BUCKET_COUNT = 128
SHARDS = ("shard_a", "shard_b")


def digest_int(value: str) -> int:
    return int.from_bytes(sha256(value.encode("utf-8")).digest(), "big")


def bucket_for(tenant_id: int, event_id: str) -> int:
    return digest_int(f"{tenant_id}:{event_id}") % BUCKET_COUNT


def owner_for_bucket(bucket: int, shards: tuple[str, ...] = SHARDS) -> str:
    if not shards:
        raise ValueError("At least one shard is required")
    return max(shards, key=lambda shard: digest_int(f"bucket:{bucket}:shard:{shard}"))


@dataclass(frozen=True)
class Route:
    shard: str
    bucket: int | None
    counter_key: str


def route_event(tenant_id: int, event_id: str, strategy: str) -> Route:
    if tenant_id < 0:
        raise ValueError("tenant_id must be nonnegative")
    if strategy == "naive":
        shard = SHARDS[tenant_id % len(SHARDS)]
        return Route(shard, None, f"tenant:{tenant_id}")
    if strategy == "bucket":
        bucket = bucket_for(tenant_id, event_id)
        return Route(owner_for_bucket(bucket), bucket, f"bucket:{bucket}")
    raise ValueError(f"Unknown strategy: {strategy}")


def movement_fraction(bucket_count: int, old: tuple[str, ...], new: tuple[str, ...]) -> float:
    return sum(owner_for_bucket(bucket, old) != owner_for_bucket(bucket, new)
               for bucket in range(bucket_count)) / bucket_count
