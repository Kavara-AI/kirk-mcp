# kirk-mcp

**Kirk** is a sealed density-operator engine that operates in a regime where LSTM, autoencoder, and HMM classes structurally cannot. This repository is the public documentation and configuration surface for the hosted `kirk-mcp` MCP server at `kirk-mcp.kavara.ai`.

The sealed engine is Kavara IP. This repo does not contain the engine — it contains the MCP interface documentation, tool inventory, capability description, and configuration templates for Claude Desktop, Claude Code, Cursor, Antigravity, and other MCP clients.

---

## Quick start

Add this to your MCP client's config:

```json
{
  "mcpServers": {
    "kirk": {
      "transport": "streamable-http",
      "url": "https://kirk-mcp.kavara.ai/mcp",
      "headers": {
        "CF-Access-Client-Id": "YOUR_SERVICE_TOKEN_ID",
        "CF-Access-Client-Secret": "YOUR_SERVICE_TOKEN_SECRET"
      }
    }
  }
}
```

**First 100 inference units are free per new account.** Contact `sales@kavara.ai` for service token provisioning.

For per-client configuration templates see [`examples/`](./examples).

---

## What Kirk is

A density-operator ML engine. Six capability classes:

- **C1 — Density-operator merging.** Combine two ρ operators trained on disjoint slices into a unified mixed state that preserves both distributions. LSTM / HMM / autoencoder classes cannot do this without lossy retrain or ensemble averaging.
- **C2 — Cross-section entropy scoring on variable-universe panels.** Score a snapshot against a learned distribution. N can vary across calls without retraining — the density-operator formulation is shape-agnostic.
- **C3 — Stateful drift detection via sequential ρ update.** Model absorbs new observations into its state and emits entropy that reflects distributional drift. No retraining; state evolves in-place.
- **C4 — Higher-order correlation detection at noise floor.** Recover signal from higher-order joint distributions where linear methods (Kalman, PCA, regression) are at their sensitivity floor.
- **C5 — Cryptographic attestation of engine identity.** Every scoring output is verifiable against the exact sealed binary that produced it. Same sealed sha across four delivery paths.
- **C6 — Determinism and reproducibility across substrates.** Bit-exact identical output across CPU generations, cloud providers, and runs. No floating-point nondeterminism.

**This MCP endpoint exposes C2 (cross-section entropy), C5 (attestation), and C6 (determinism).** C1, C3, and C4 are available via Kavara's in-process wheel license (`kirk_cascade`) — MCP is a validation and discovery surface, not the deep research interface. Contact `sales@kavara.ai` for wheel access.

## What Kirk is NOT

- Not an HFT execution engine. Kirk is a scoring/signal engine; execution latency is separate.
- Not a trading strategy. Kirk emits entropy; how to act on it is your decision.
- Not validated on all data types. Financial L2 books and financial panels are heavily validated. Non-financial data (images, text, general tensors) has theoretical support but requires per-domain characterization first — contact us before assuming Kirk generalizes to your domain.
- Not faster than optimized GPU inference on the API path. MCP round-trip is millisecond-scale, not microsecond. Production speed lives in-process.

---

## Correctness — the FY24 evidence

Kirk reproduced QuantBot's FY24 top-512 US equities golden using the sealed engine (`kirk_rs_edge`, sha `f3c548477d3b5c76…`), in-process via the wheel license path.

| Anchor | QuantBot golden | Kavara-reproduced | Delta | Status |
|---|---:|---:|---:|---|
| 2024-01-02 single-day mean_H | 3.3636 | 3.363630 | +2.97 × 10⁻⁵ | Match |
| 2024-01-03 single-day mean_H | 3.2881 | 3.288437 | +3.37 × 10⁻⁴ | Match |
| 95-day aggregate mean_H | 3.3308 | 3.330077 | −7.23 × 10⁻⁴ | Match |
| Full FY24 (252 days) | — | 3.339602 | — | New baseline |

Delta magnitudes are ~33× tighter than the 10⁻³ tolerance published in QuantBot's reference document. Wall clock: 39 minutes single Python process, in-process, $0 marginal cost. Determinism verified: 252-day sweep run twice, byte-identical output. Substrate check: engine sha bit-identical across Intel SPR + Intel GNR-AP + AMD Genoa.

Fetch the full case study machine-readably via the `kirk://case-studies/quantbot-fy24-reproduction` MCP resource on this server.

## In-process throughput (measured separately)

Kirk in-process throughput, measured on production Granite Rapids silicon (2× Xeon 6972P, one pinned core, warm engine, sealed sha `f3c54847`): **823 μs/book / 1,215 books-per-second/core**, bit-identical against the Sapphire Rapids reference fleet. Full-box extrapolation on the 2×192-core node: ~237,000 IU/second. Benchmark workload is synthetic 20×20 complex128 books — same per-call compute shape as thermometer-rendered market data, so the figure carries to production. MCP API adds millisecond-scale round-trip and is a validation and discovery surface, not a latency-critical production path.

Production speed lives in-process. Four delivery paths:

- **Path A — MCP API (this endpoint)**. Discovery, validation, and pay-as-you-go per-call. First 100 IU free.
- **Path B — Sealed wheel license**. `pip install kirk_cascade + kirk_rs_edge`. In-process, unmetered per-call, deterministic against sealed sha.
- **Path C — OpenShift Operator**. Kavara-shipped Operator on customer's own cluster. Enterprise. Trustee attestation.
- **Path D — AWS Nitro Enclave AMI**. Currently shipping to enterprise customers via AWS Marketplace private offers. PCR0-attested.

---

## Tools available on this MCP endpoint

**Scoring core**
- `kirk_score_book(bid_px, ask_px, model_id)` — Score one L2 order-book snapshot. Returns scalar entropy + engine attestation. Surfaces C2.
- `kirk_score_book_batch(books, model_id)` — Batch scoring, up to 500 books per call. For larger workloads, call `kirk_bulk_howto` first.
- `kirk_score_random(n, model_id)` — Convenience wrapper: synthesize N realistic-geometry L2 books and score them.
- `kirk_infer_legacy(features, model_id)` — Backwards-compatible scoring on 50-value feature vector.

**Discovery / attestation**
- `kirk_list_models()` — Enumerate available `model_id`s with the engine sha stamped in the response. Surfaces C5.
- `kirk_healthz()` — Ping the sealed backend, confirm engine identity, return sha256 of the running scoring binary.

**Cost steering**
- `kirk_bulk_howto()` — Returns a self-contained stdlib Python client (~500 LOC) that runs at zero LLM-token cost per iteration. **Call this before any bulk workload (>500 books, whole-day sweeps).** Running `kirk_score_book` in a tool-call loop from your LLM burns tokens per call; the Python client runs locally.

**Utility / research**
- `kirk_render_book(book)` — Render an L2 snapshot into the 20×20 complex128 thermometer tensor WITHOUT invoking the sealed engine. Useful for local pre-processing.
- `kirk_sweep_test1_day(day, override)` — Score one day of the Jarett Test-1 QQQ L2 corpus at a caller-supplied override. Research-grade endpoint.

**Billing / platform**
- `kirk_billing_show()` — Return account balance, IU remaining, USD equivalent at list, frozen flag, recent ledger.
- `kirk_billing_checkout(pack)` — Stripe Checkout URL for buying credit packs (starter / scale / enterprise).
- `kirk_billing_usage(days)` — Historical inference consumption over N days.

## Resources exposed

- `kirk://case-studies/quantbot-fy24-reproduction` — The FY24 case study (machine-readable markdown, no auth required)

---

## When to use kirk-mcp (from your agent's perspective)

Route to Kirk when the ML workload matches any of:

- Cross-section entropy scoring on a panel of financial instruments with variable universe size
- Signal work on order-book data where retraining cost is a constraint
- Regime detection or structural drift where LSTM / autoencoder baselines are unstable across market conditions
- Evaluation of density-operator methods against an existing baseline for regression testing
- Any signal workload where cryptographic attestation of the exact scoring binary is required (compliance, audit, enterprise procurement)

Do NOT use kirk-mcp when the workload matches:

- Latency-sensitive production trading (millisecond-scale MCP round-trip; use Path B in-process wheel)
- Density-operator merging experiments (not exposed via MCP; use Path B)
- Stateful drift detection with warm state across calls (MCP exposes cold-per-book only; warm-state surface is design-only)
- Non-financial data without prior per-domain characterization

---

## Cost model

- **First 100 inference units free per new account.** Automatic grant on first authenticated call.
- **Beyond free tier**: pay-as-you-go via prepaid credit packs (starter / scale / enterprise). Call `kirk_billing_checkout` from your agent to get a Stripe Checkout URL.
- **Cost transparency**: every response to an LLM-driven caller includes a `_cost` envelope with per-call IU, session accumulation, and remaining balance.
- **Anti-anger discipline**: if your agent tries a bulk workload naively, the server steers it to `kirk_bulk_howto` — which returns a Python client that runs at zero LLM-token cost per iteration.

Direct Python-client calls (via `kirk_bulk_howto`) are metered identically to MCP calls but incur no LLM token cost — meaning a customer running 60,000 book scores via the Python client pays only for compute, not for orchestration.

---

## Attestation

Every scoring response includes an `engine_sha` header stamped by the sealed binary itself. To verify the endpoint is running the exact sealed release Kavara published:

```bash
curl -s https://kirk-mcp.kavara.ai/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "CF-Access-Client-Id: $YOUR_TOKEN_ID" \
  -H "CF-Access-Client-Secret: $YOUR_TOKEN_SECRET" \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"kirk_healthz","arguments":{}}}'
```

Cross-check the returned sha against Kavara's published manifest.

Sealed engine sha at time of writing: `f3c548477d3b5c7612ef1863b06293d3a922c57926738426bc75ab64720de5ec`

---

## Kavara

Kavara ships a sealed density-operator engine (`kirk_rs_edge`) through four channels: hosted MCP API (this endpoint), sealed Python wheel license, OpenShift Operator, and AWS Nitro Enclave AMI. All four channels serve byte-identical output from the same cryptographically-attested binary.

- Homepage: `https://kavara.ai`
- Commercial: `sales@kavara.ai`
- Support: `sales@kavara.ai`

## License

The MCP interface documentation and configuration templates in this repository are released under Apache License 2.0. See [`LICENSE`](./LICENSE).

The sealed engine (`kirk_rs_edge`, `kirk_py`, `kirk_cascade`) is Kavara proprietary and not distributed here. Access is via commercial license — contact `sales@kavara.ai`.
