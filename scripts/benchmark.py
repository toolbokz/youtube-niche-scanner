#!/usr/bin/env python3
"""Performance benchmark script for the Growth Strategist API.

Usage:
    python scripts/benchmark.py [--base-url http://localhost:8000] [--iterations 5]

Measures:
    - Health endpoint latency (target: < 50 ms)
    - Cache stats latency (target: < 100 ms)
    - Dashboard batch latency (target: < 150 ms)
    - Reports list latency (target: < 200 ms)
    - GZip compression ratio
    - Server-Timing header values
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from typing import Any

try:
    import httpx
except ImportError:
    print("Install httpx first:  pip install httpx")
    sys.exit(1)


def _measure(
    client: httpx.Client,
    method: str,
    path: str,
    iterations: int = 5,
    body: dict | None = None,
) -> dict[str, Any]:
    """Hit an endpoint repeatedly and collect timing stats."""
    latencies: list[float] = []
    last_status = 0
    last_size = 0
    server_timing = ""
    compressed_size = 0

    for _ in range(iterations):
        t0 = time.perf_counter()
        if method == "POST":
            resp = client.post(path, json=body)
        else:
            resp = client.get(path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)
        last_status = resp.status_code
        last_size = len(resp.content)
        server_timing = resp.headers.get("Server-Timing", "")
        # Check if gzip was used
        compressed_size = int(resp.headers.get("content-length", last_size))

    return {
        "path": path,
        "method": method,
        "status": last_status,
        "iterations": iterations,
        "min_ms": round(min(latencies), 1),
        "max_ms": round(max(latencies), 1),
        "mean_ms": round(statistics.mean(latencies), 1),
        "median_ms": round(statistics.median(latencies), 1),
        "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 1) if len(latencies) >= 2 else round(max(latencies), 1),
        "response_bytes": last_size,
        "server_timing": server_timing,
    }


def run_benchmarks(base_url: str, iterations: int) -> list[dict[str, Any]]:
    """Run all benchmark suites."""
    results = []

    with httpx.Client(
        base_url=base_url,
        timeout=120,
        headers={"Accept-Encoding": "gzip"},
    ) as client:
        # 1. Health check (should be < 50ms)
        print("  [1/5] Health endpoint...")
        results.append(_measure(client, "GET", "/health", iterations))

        # 2. Cache stats (should be < 100ms)
        print("  [2/5] Cache stats...")
        results.append(_measure(client, "GET", "/cache/stats", iterations))

        # 3. Dashboard batch (should be < 150ms)
        print("  [3/5] Dashboard data (batch)...")
        results.append(_measure(client, "GET", "/dashboard-data", iterations))

        # 4. Reports list (should be < 200ms)
        print("  [4/5] Reports list...")
        results.append(_measure(client, "GET", "/reports", iterations))

        # 5. Full analysis (single iteration — this is expensive)
        print("  [5/5] Full analysis pipeline (1 iteration)...")
        results.append(_measure(
            client,
            "POST",
            "/analyze",
            iterations=1,
            body={"seed_keywords": ["python tutorial"], "top_n": 3, "videos_per_niche": 5},
        ))

    return results


def print_report(results: list[dict[str, Any]]) -> None:
    """Pretty-print benchmark results as a table."""
    targets = {
        "/health": 50,
        "/cache/stats": 100,
        "/dashboard-data": 150,
        "/reports": 200,
        "/analyze": 60_000,  # pipeline is expected to be slow
    }

    print("\n" + "=" * 90)
    print(f"{'Endpoint':<25} {'Method':<7} {'Min':>8} {'Mean':>8} {'P95':>8} {'Max':>8} {'Target':>8} {'Status':>8}")
    print("-" * 90)

    for r in results:
        target = targets.get(r["path"], 0)
        passed = r["mean_ms"] <= target if target else True
        status_icon = "PASS" if passed else "SLOW"
        target_str = f"<{target}ms" if target else "—"

        print(
            f"{r['path']:<25} {r['method']:<7} "
            f"{r['min_ms']:>7.1f} {r['mean_ms']:>7.1f} {r['p95_ms']:>7.1f} {r['max_ms']:>7.1f} "
            f"{target_str:>8} {status_icon:>8}"
        )

    print("=" * 90)

    # Summary
    fast_endpoints = [r for r in results if r["path"] != "/analyze"]
    if fast_endpoints:
        avg_latency = statistics.mean(r["mean_ms"] for r in fast_endpoints)
        print(f"\nAvg read endpoint latency: {avg_latency:.1f} ms")

    # Check /analyze pipeline timing
    analyze = next((r for r in results if r["path"] == "/analyze"), None)
    if analyze and analyze["status"] == 200:
        print(f"Pipeline execution: {analyze['mean_ms']:.0f} ms")
        if analyze.get("server_timing"):
            print(f"Server-Timing: {analyze['server_timing']}")

    # GZip check
    for r in results:
        if r["response_bytes"] > 1000:
            print(f"Response size ({r['path']}): {r['response_bytes']} bytes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Growth Strategist API")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--iterations", type=int, default=5, help="Iterations per endpoint")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    print(f"\nBenchmarking {args.base_url} ({args.iterations} iterations)...\n")

    try:
        results = run_benchmarks(args.base_url, args.iterations)
    except httpx.ConnectError:
        print(f"ERROR: Cannot connect to {args.base_url}. Is the server running?")
        sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results)


if __name__ == "__main__":
    main()
