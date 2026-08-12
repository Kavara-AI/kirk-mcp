#!/usr/bin/env python3
import time
import json
import os
import urllib.request
import urllib.error
import concurrent.futures

ENDPOINT = os.environ.get("KIRK_ENDPOINT", "https://kirk-mcp.kavara.ai/mcp")

def call_tool(name: str, arguments: dict) -> dict:
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
        return duration, json.loads(body)

def main():
    print("--- GNR Validation Harness ---")
    
    # 1. Startup & Health
    try:
        dur, health = call_tool("kirk_healthz", {})
        print(f"[PASS] Health check latency: {dur:.4f}s")
    except Exception as e:
        print(f"[FAIL] Health check: {e}")
        return

    # 2. Single Latency
    dur, res = call_tool("kirk_score_random", {"n": 1, "model_id": "kirk-fy24-log-return-cascade-v1"})
    print(f"[PASS] Single score latency: {dur:.4f}s")

    # 3. Batch Latency
    dur, res = call_tool("kirk_score_random", {"n": 100, "model_id": "kirk-fy24-log-return-cascade-v1"})
    print(f"[PASS] Batch score (100) latency: {dur:.4f}s")

if __name__ == "__main__":
    main()
