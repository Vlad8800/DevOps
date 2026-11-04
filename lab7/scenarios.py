"""Reproducible data generation, hot-shard load and query benchmarks."""

import argparse
import asyncio
import json
import math
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5

import httpx

from lab7.sharding import BUCKET_COUNT, SHARDS, movement_fraction, owner_for_bucket


def event_id(run_id: str, strategy: str, index: int) -> str:
    return str(uuid5(NAMESPACE_DNS, f"trackhub-lab7:{run_id}:{strategy}:{index}"))


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1)], 3)


def summarize(latencies: list[float], elapsed: float, errors: int) -> dict:
    return {
        "requests": len(latencies) + errors,
        "errors": errors,
        "error_rate_percent": round(errors * 100 / (len(latencies) + errors), 2) if latencies or errors else 0,
        "rps": round((len(latencies) + errors) / elapsed, 2) if elapsed else 0,
        "mean_ms": round(statistics.mean(latencies), 3) if latencies else 0,
        "p95_ms": percentile(latencies, 0.95),
        "p99_ms": percentile(latencies, 0.99),
    }


async def run_requests(method: str, url: str, count: int, concurrency: int,
                       body_factory=None, timeout: float = 60) -> dict:
    semaphore = asyncio.Semaphore(concurrency)
    latencies = []
    errors = 0
    async with httpx.AsyncClient(timeout=timeout) as client:
        async def one(index: int):
            nonlocal errors
            async with semaphore:
                start = time.perf_counter()
                try:
                    body = body_factory(index) if body_factory else None
                    response = await client.request(method, url, json=body)
                    if response.status_code >= 400:
                        errors += 1
                    else:
                        latencies.append((time.perf_counter() - start) * 1000)
                except (httpx.HTTPError, ValueError):
                    errors += 1

        started = time.perf_counter()
        await asyncio.gather(*(one(index) for index in range(count)))
        elapsed = time.perf_counter() - started
    return summarize(latencies, elapsed, errors)


def write_json(name: str, data: dict):
    path = Path("/results") / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {path}")


async def seed(args):
    strategy = args.strategy
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + strategy
    endpoint = "/single/events" if strategy == "single" else f"/events?strategy={strategy}"

    def body(index):
        tenant = 2 if index < int(args.count * args.hot_ratio) else 10 + index % 100
        return {"tenant_id": tenant, "event_id": event_id(run_id, strategy, index),
                "run_id": run_id, "payload": f"sample-{index:06d}"}

    metrics = await run_requests("POST", args.base_url + endpoint, args.count, args.concurrency, body)
    result = {"run_id": run_id, "strategy": strategy, "count": args.count,
              "hot_tenant_ratio": args.hot_ratio, "concurrency": args.concurrency, "write_metrics": metrics}
    if strategy != "single":
        async with httpx.AsyncClient() as client:
            response = await client.get(args.base_url + "/stats",
                                        params={"run_id": run_id, "strategy": strategy})
            response.raise_for_status()
            result["distribution"] = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    write_json(f"seed-{run_id}.json", result)


async def benchmark(args):
    strategy = args.strategy
    identifier = event_id(args.run_id, strategy, 0)
    if strategy == "single":
        local = f"/single/events/{identifier}"
    else:
        local = f"/events/2/{identifier}?strategy={strategy}"
    operations = {"shard_local": args.base_url + local}
    if strategy != "single":
        operations["cross_shard"] = (args.base_url + f"/search?q=sample-000000&run_id={args.run_id}"
                                     f"&strategy={strategy}")
    rows = []
    for concurrency in args.concurrency:
        for operation, url in operations.items():
            metrics = await run_requests("GET", url, args.requests, concurrency)
            row = {"topology": strategy, "operation": operation, "concurrency": concurrency, **metrics}
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False))
    saturation = {}
    for operation in operations:
        candidates = [row for row in rows if row["operation"] == operation]
        best = max(candidates, key=lambda row: row["rps"])
        saturation[operation] = {"best_concurrency": best["concurrency"], "peak_rps": best["rps"]}
    result = {"run_id": args.run_id, "rows": rows, "saturation": saturation}
    write_json(f"benchmark-{args.run_id}.json", result)


def reshard(args):
    keys = range(args.keys)
    modulo_moved = sum(key % 2 != key % 3 for key in keys) / args.keys
    buckets_moved = movement_fraction(BUCKET_COUNT, SHARDS, SHARDS + ("shard_c",))
    owners_two = {name: sum(owner_for_bucket(bucket, SHARDS) == name for bucket in range(BUCKET_COUNT))
                  for name in SHARDS}
    owners_three = {name: sum(owner_for_bucket(bucket, SHARDS + ("shard_c",)) == name
                              for bucket in range(BUCKET_COUNT)) for name in SHARDS + ("shard_c",)}
    result = {"keys": args.keys, "buckets": BUCKET_COUNT, "modulo_2_to_3_moved_percent": round(modulo_moved * 100, 2),
              "virtual_buckets_2_to_3_moved_percent": round(buckets_moved * 100, 2),
              "theoretical_new_shard_share_percent": round(100 / 3, 2),
              "two_shard_bucket_owners": owners_two, "three_shard_bucket_owners": owners_three}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    write_json("resharding-model.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    seed_cmd = sub.add_parser("seed")
    seed_cmd.add_argument("--strategy", choices=["single", "naive", "bucket"], required=True)
    seed_cmd.add_argument("--count", type=int, default=500)
    seed_cmd.add_argument("--concurrency", type=int, default=16)
    seed_cmd.add_argument("--hot-ratio", type=float, default=0.9)
    seed_cmd.add_argument("--run-id")
    seed_cmd.add_argument("--base-url", default="http://lab7_api:8000")
    bench_cmd = sub.add_parser("benchmark")
    bench_cmd.add_argument("--strategy", choices=["single", "naive", "bucket"], required=True)
    bench_cmd.add_argument("--run-id", required=True)
    bench_cmd.add_argument("--requests", type=int, default=200)
    bench_cmd.add_argument("--concurrency", type=int, nargs="+", default=[1, 4, 8, 16, 32])
    bench_cmd.add_argument("--base-url", default="http://lab7_api:8000")
    model_cmd = sub.add_parser("reshard")
    model_cmd.add_argument("--keys", type=int, default=10000)
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(seed(args))
    elif args.command == "benchmark":
        asyncio.run(benchmark(args))
    else:
        reshard(args)


if __name__ == "__main__":
    main()
