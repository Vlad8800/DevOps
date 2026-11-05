"""Generate TrackHub HTTP traffic from inside or outside the cluster."""

import argparse
import concurrent.futures
import time
import urllib.error
import urllib.request


def request_once(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except (OSError, TimeoutError):
        return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://trackhub.trackhub.svc.cluster.local:8000/api/tasks")
    parser.add_argument("--duration", type=int, default=180)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    deadline = time.monotonic() + args.duration
    next_report = time.monotonic() + 5
    totals: dict[int, int] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        while time.monotonic() < deadline:
            for status in pool.map(request_once, [args.url] * args.workers):
                totals[status] = totals.get(status, 0) + 1
            if time.monotonic() >= next_report:
                print(f"requests={sum(totals.values())} statuses={totals}", flush=True)
                next_report += 5
    print(f"finished: requests={sum(totals.values())} statuses={totals}", flush=True)


if __name__ == "__main__":
    main()
