#!/usr/bin/env python3
"""
Minimal example of calling kirk-mcp directly via HTTP (stdlib only, no MCP client).

For bulk workloads, this is the cost-efficient path — zero LLM tokens per iteration.

Usage:
    export KIRK_CF_ACCESS_CLIENT_ID=...
    export KIRK_CF_ACCESS_CLIENT_SECRET=...
    python3 python_client_example.py

For a fully-featured client (auto-retry, batch chunking, rate-limit handling),
call the kirk_bulk_howto MCP tool from your agent to receive a ~500 LOC stdlib
Python client with typed exceptions and cost telemetry.
"""

import json
import os
import urllib.request
import urllib.error


ENDPOINT = "https://kirk-mcp.kavara.ai/mcp"


def call_tool(name: str, arguments: dict) -> dict:
    """Call an MCP tool via JSON-RPC. Returns the parsed result."""
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
            "Accept": "application/json, text/event-stream",
            "CF-Access-Client-Id": os.environ["KIRK_CF_ACCESS_CLIENT_ID"],
            "CF-Access-Client-Secret": os.environ["KIRK_CF_ACCESS_CLIENT_SECRET"],
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8')}") from e


def main() -> None:
    # 1. Health check — confirm sealed engine sha
    health = call_tool("kirk_healthz", {})
    print("Engine health:", json.dumps(health, indent=2))

    # 2. List available models
    models = call_tool("kirk_list_models", {})
    print("Models:", json.dumps(models, indent=2))

    # 3. Score a random book (fastest smoke test)
    result = call_tool("kirk_score_random", {"n": 1, "model_id": "kirk-qb-trial-v1"})
    print("Random score:", json.dumps(result, indent=2))

    # 4. For bulk scoring, call kirk_bulk_howto to get a proper client
    #    Do NOT loop kirk_score_book from an agent — burns LLM tokens per call.
    #    The howto tool returns a ~500 LOC stdlib client with all the plumbing.
    howto = call_tool("kirk_bulk_howto", {})
    print("\nFor bulk workloads, use the client returned by kirk_bulk_howto.")
    print("Preview of client (first 500 chars):")
    if "result" in howto and "content" in howto["result"]:
        client_source = howto["result"]["content"][0].get("text", "")
        print(client_source[:500])
        print("...")


if __name__ == "__main__":
    main()
