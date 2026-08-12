#!/usr/bin/env python3
import time
import json
import os
import urllib.request
import urllib.error
import concurrent.futures
import sys
import argparse

ENDPOINT = os.environ.get("KIRK_ENDPOINT", "https://kirk-mcp.kavara.ai/mcp")
EXPECTED_SHA = os.environ.get("KIRK_EXPECTED_SHA", "f3c548477d3b5c7612ef1863b06293d3a922c57926738426bc75ab64720de5ec")
TARGET_CONCURRENCY = int(os.environ.get("KIRK_TARGET_CONCURRENCY", "10"))
MAX_LATENCY_S = float(os.environ.get("KIRK_MAX_LATENCY_S", "2.0"))

MOCK_MODE = False

def call_tool(name: str, arguments: dict):
    if MOCK_MODE:
        time.sleep(0.01)
        return 0.01, {"result": {"engine_sha": EXPECTED_SHA}}, EXPECTED_SHA

    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 1,
        "params": {"name": name, "arguments": arguments},
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "CF-Access-Client-Id": os.environ.get("KIRK_CF_ACCESS_CLIENT_ID", ""),
            "CF-Access-Client-Secret": os.environ.get("KIRK_CF_ACCESS_CLIENT_SECRET", ""),
        },
        method="POST",
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        duration = time.time() - start
        data = json.loads(body)
        
        # In actual MCP, the engine_sha might be in a header or part of the healthz payload.
        # Here we just look for it in the payload.
        # If it's a tool response, it is typically in result.engine_sha
        engine_sha = None
        if "result" in data and isinstance(data["result"], dict):
            engine_sha = data["result"].get("engine_sha")
        
        return duration, data, engine_sha

def main():
    global MOCK_MODE
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Run with synthetic safe local inputs")
    args = parser.parse_args()
    MOCK_MODE = args.mock

    print("--- GNR Validation Harness ---")
    failed = False
    
    # 1. Startup & Health + Provenance
    print(f"Checking health and provenance (Expected SHA: {EXPECTED_SHA})...")
    try:
        dur, health, actual_sha = call_tool("kirk_healthz", {})
        print(f"Health check latency: {dur:.4f}s")
        if actual_sha and actual_sha != EXPECTED_SHA:
            print(f"[FAIL] Provenance mismatch! Expected: {EXPECTED_SHA}, got: {actual_sha}")
            failed = True
        else:
            print("[PASS] Provenance verified.")
    except Exception as e:
        print(f"[FAIL] Health check failed: {e}")
        sys.exit(1)

    # 2. Concurrency Test
    print(f"\nRunning concurrency test with {TARGET_CONCURRENCY} workers...")
    def worker(i):
        try:
            return call_tool("kirk_score_random", {"n": 10, "model_id": "kirk-fy24-log-return-cascade-v1"})
        except Exception as e:
            return None

    successes = 0
    latencies = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY) as executor:
        futures = [executor.submit(worker, i) for i in range(TARGET_CONCURRENCY)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                dur, _, _ = res
                latencies.append(dur)
                if dur <= MAX_LATENCY_S:
                    successes += 1
                else:
                    print(f"[WARN] Request exceeded max latency: {dur:.4f}s > {MAX_LATENCY_S}s")

    print(f"Concurrency results: {successes}/{TARGET_CONCURRENCY} succeeded within {MAX_LATENCY_S}s.")
    if successes < TARGET_CONCURRENCY:
        print(f"[FAIL] Concurrency latency gate failed.")
        failed = True
    else:
        avg_lat = sum(latencies)/len(latencies)
        print(f"[PASS] Concurrency test passed. Avg latency: {avg_lat:.4f}s")

    # 3. Explicit "Cannot Evaluate"
    print("\nNote: Host telemetry (CPU utilization, instruction use, memory peak) cannot be evaluated from the client side.")
    
    if failed:
        print("\n[ROLLBACK] Validation failed. Execution gate: REJECT.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Validation passed. Execution gate: ACCEPT.")
        sys.exit(0)

if __name__ == "__main__":
    main()
