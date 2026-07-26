"""
load_test.py
Simple concurrent load test for the /predict endpoint.
No compiled dependencies (unlike locust's gevent requirement) --
uses only requests + concurrent.futures, both pure Python / already installed.

Usage:
    python load_test.py --users 10 --requests 20
"""
import argparse
import codecs
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

API_URL = "http://127.0.0.1:5000/predict"
SAMPLE_FILE = "sample_request.json"


def load_sample_payload():
    with codecs.open(SAMPLE_FILE, "r", "utf-16") as f:
        return json.load(f)


def send_one_request(payload):
    t0 = time.perf_counter()
    try:
        r = requests.post(API_URL, json=payload, timeout=10)
        ok = r.status_code == 200
    except Exception:
        ok = False
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return ok, elapsed_ms


def run_load_test(concurrent_users, requests_per_user):
    payload = load_sample_payload()
    total_requests = concurrent_users * requests_per_user
    print(f"Running {total_requests} requests ({concurrent_users} concurrent users x {requests_per_user} each)...")

    latencies = []
    failures = 0
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [
            executor.submit(send_one_request, payload)
            for _ in range(total_requests)
        ]
        for future in as_completed(futures):
            ok, elapsed_ms = future.result()
            if ok:
                latencies.append(elapsed_ms)
            else:
                failures += 1

    total_time = time.perf_counter() - start
    latencies.sort()

    print("\n" + "=" * 50)
    print("LOAD TEST RESULTS")
    print("=" * 50)
    print(f"Concurrent users:      {concurrent_users}")
    print(f"Total requests:        {total_requests}")
    print(f"Successful:            {len(latencies)}")
    print(f"Failed:                {failures}")
    print(f"Total wall time:       {total_time:.2f}s")
    print(f"Throughput:            {total_requests / total_time:.2f} req/s")
    if latencies:
        print(f"Mean latency:          {statistics.mean(latencies):.2f} ms")
        print(f"Median latency:        {statistics.median(latencies):.2f} ms")
        print(f"p95 latency:           {latencies[int(len(latencies) * 0.95)]:.2f} ms")
        print(f"p99 latency:           {latencies[int(len(latencies) * 0.99)]:.2f} ms")
        print(f"Max latency:           {max(latencies):.2f} ms")

    return {
        "concurrent_users": concurrent_users,
        "total_requests": total_requests,
        "failures": failures,
        "throughput_rps": total_requests / total_time,
        "mean_latency_ms": statistics.mean(latencies) if latencies else None,
        "p95_latency_ms": latencies[int(len(latencies) * 0.95)] if latencies else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=10, help="concurrent users")
    parser.add_argument("--requests", type=int, default=20, help="requests per user")
    args = parser.parse_args()
    run_load_test(args.users, args.requests)
