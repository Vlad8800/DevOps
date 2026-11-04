"""Summarize Docker CPU and memory samples captured during hot-shard runs."""

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "docs" / "lab7" / "results"


def summarize(filename):
    nodes = {}
    for line in (RESULTS / filename).read_text(encoding="utf-8").splitlines():
        parts = line.split(",")
        if len(parts) < 4:
            continue
        _, name, cpu, memory = parts[:4]
        try:
            cpu_percent = float(cpu.rstrip("%"))
            memory_mib = float(memory.split("MiB")[0])
        except ValueError:
            continue
        entry = nodes.setdefault(name, {"peak_cpu_percent": 0.0, "peak_memory_mib": 0.0})
        entry["peak_cpu_percent"] = max(entry["peak_cpu_percent"], cpu_percent)
        entry["peak_memory_mib"] = max(entry["peak_memory_mib"], memory_mib)
    return nodes


if __name__ == "__main__":
    result = {"naive": summarize("stats-naive.csv"), "bucket": summarize("stats-bucket.csv")}
    path = RESULTS / "hot-shard-resources.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
