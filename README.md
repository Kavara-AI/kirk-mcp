# kirk-mcp

**Ulysses** is an algorithmic primitive for computing the complete pairwise structure of a system — every variable against every other, all at once — unsupervised, real-time, on a CPU.

**Kirk** is the first algorithm on Ulysses. It signals the moment structure breaks.

**Borg** is the second algorithm on Ulysses. Radio-frequency spectrum anomaly detection.

This repository is the public documentation and configuration surface for the hosted `kirk-mcp` MCP server at `kirk-mcp.kavara.ai` — where Kirk is exposed as a set of MCP tools for validation and discovery use cases.

> **The Kalman filter for the non-Gaussian, non-stationary world.**

The Kalman filter is a special case: linear, Gaussian. Ulysses closes the full-joint intractability that stopped the Boltzmann-machine family, in polynomial time, and Kirk applies that primitive to non-stationary streams. Not a foundation model — the Kalman filter's category, not GPT's. The IP is the math.

---

## Quick start

**Fastest path: [paste this into your assistant](./SETUP.md)** and it will configure
your client for you — Grok, Claude, Cursor, Copilot Chat, or any other MCP client.

To configure by hand instead, read on.

You need a credential. Kavara issues one of two kinds — **use whichever you were given**:

| You were given | Use this |
| --- | --- |
| A URL like `https://kirk-mcp.kavara.ai/mcp/k_...` | **Personal key.** Works as a URL *or* as a header. |
| A client ID and secret pair | **Service token.** Header only. |

Most clients are configured with a personal key. It is the same key either way —
as a header it stays out of shell history, process listings and request logs, so
prefer the header form wherever your client supports headers.

**Personal key, as a header** (recommended):

```json
{
  "mcpServers": {
    "kirk": {
      "url": "https://kirk-mcp.kavara.ai/mcp",
      "headers": {
        "Authorization": "Bearer k_YOUR_PERSONAL_KEY"
      }
    }
  }
}
```

**Personal key, as a URL** — for clients that accept only a URL (the Claude Desktop
and claude.ai connector dialogs, for example):

```json
{
  "mcpServers": {
    "kirk": {
      "url": "https://kirk-mcp.kavara.ai/mcp/k_YOUR_PERSONAL_KEY"
    }
  }
}
```

**Service token**, if that is what you hold:

```json
{
  "mcpServers": {
    "kirk": {
      "url": "https://kirk-mcp.kavara.ai/mcp",
      "headers": {
        "CF-Access-Client-Id": "YOUR_SERVICE_TOKEN_ID",
        "CF-Access-Client-Secret": "YOUR_SERVICE_TOKEN_SECRET"
      }
    }
  }
}
```

Command-line clients that take flags rather than JSON, such as Claude Code:

```sh
claude mcp add --transport http kirk https://kirk-mcp.kavara.ai/mcp \
  -H "Authorization: Bearer k_YOUR_PERSONAL_KEY"
```

**First 100 inference units are free per new account.** Contact `sales@kavara.ai`
to be issued a credential.

### Check it worked

Ask your client to call `kirk_verify_engine`. It costs nothing and returns
`status: ok` plus the engine sha. Record that sha alongside any result you keep —
results from different engine builds are not interchangeable.

If a call fails, see [troubleshooting](#troubleshooting) before changing your
credential; the most common failure is not a credential problem.

For per-client templates see [`examples/`](./examples): Claude Desktop, Claude Code,
Cursor, VS Code, Grok, a generic streamable-HTTP client, and a Python client.

### Troubleshooting

- **A 403 that looks like an authentication failure.** Often it is the
  `User-Agent`. Cloudflare rejects some default client agents on this zone with a
  1010 "browser signature banned" error that arrives as a 403. Set an explicit
  `User-Agent` before you start debugging credentials.
- **`URL key ... is unknown`.** The key was mistyped, or it has been revoked.
  Keys are per person and are not shared; ask for a new one.
- **A 402.** The account balance is exhausted. Call `kirk_billing_show`.
- **A model listed by `kirk_list_models` that errors when called.** The catalogue
  lists registered models; it is not a liveness check. Please report it.

## What most machine learning does today, and what Kirk does instead

Almost all of AI is supervised: predict a target Y from inputs X. It's powerful, but it needs a target — someone has to define and label Y — and it only sees the slice you framed, not the structure you didn't think to ask about.

What actually drives market regimes, trips alarms, and breaks systems lives in **how all the variables relate to each other** — the joint structure of the whole system. That structure is unlabeled, it shifts over time, and "Y given X" is blind to it.

Kirk answers the question nobody's model is answering:

> "Is the structure of this system still normal — and if not, where did it break?"

Kirk maintains a continuously-updated model of what "normal" looks like across every-pairwise interaction. Read any relationship straight off it, including the classic Y-given-X. When structure breaks, Kirk fires. When it holds, Kirk sits flat.

**Additive, not substitutive.** Keep your models — Kirk aims them. An attention layer that tells the rest of your stack where to look.

---

## Why nobody else keeps the whole graph

Keeping the exact full joint costs O(2ⁿ) — intractable beyond toy sizes. The classical world restricts the graph or samples and hopes. Ulysses computes the exact full joint in a deterministic O(n³) per sample, paid once per incoming sample, independent of history length.

| n | Ulysses — n³ / sample | Boltzmann (exact) — 2ⁿ |
|---:|---:|---:|
| 30 | 27,000 | 1,073,741,824 |
| 64 | 262,144 | 18,400,000,000,000,000,000 |
| 100 | 1,000,000 | 1.3 × 10³⁰ |

At n=100: a million ops vs more terms than atoms in the room. Polynomial means it runs anywhere.

---

## Between a Kalman filter and a GPU deep net

Measured on the production engine — one dual-socket Xeon box, 192 cores, no GPU:

- **2.66M model updates / second** (cascade layer 1: 402k/s; cascade layer 2: 66.7k/s)
- **6m 38s for a full year** of S&P-500 minute bars, 10-seed ensemble (~14.7 CPU-hours of work, one box, no GPU)
- **O(n³) per sample, not O(2ⁿ)** — polynomial, scales to thousands of models
- Runs inside confidential (Intel TDX / AWS Nitro / AMD SEV) enclaves — your data never leaves your environment, and the engine never leaves ours

---

## What you get from this MCP endpoint

Kirk exposes six capability classes. Three are directly accessible via this MCP endpoint:

- **C2 — Cross-section structural scoring on variable-universe panels.** Score a snapshot against a learned normal and emit a scalar. N can vary across calls without retraining — the primitive is shape-agnostic.
- **C5 — Cryptographic attestation of engine identity.** Every scoring output is verifiable against the exact sealed binary that produced it.
- **C6 — Determinism across substrates.** Bit-exact identical output across Intel Sapphire Rapids, Intel Granite Rapids, and AMD Genoa. No floating-point nondeterminism.

Three more capabilities live in the in-process wheel license (Path B) — not exposed via MCP today:

- **C1 — Structural merging.** Combine two learned "normals" from disjoint slices into a unified picture, preserving the joint spectrum.
- **C3 — Stateful drift detection.** Model absorbs new observations into its state and emits signal that reflects distributional drift. No retraining; state evolves in-place.
- **C4 — Higher-order correlation detection at noise floor.** Signal from higher-order joint distributions where Kalman filters, PCA, and linear regression are at their sensitivity floor. Independently verified by a quant firm at ~16× the linear baseline.

Contact `sales@kavara.ai` for wheel access if C1/C3/C4 apply to your workload.

## What Kirk is NOT

- **Not a foundation model.** No pretraining corpus, no weights. The IP is the math.
- **Not a trading strategy.** Kirk emits structural change signal; how to act on it is your decision.
- **Not an HFT execution engine.** MCP round-trip is millisecond-scale. Production speed lives in-process (Path B/C/D below).
- **Not validated on every data type.** Heavy validation on financial L2 books and financial panels. RF spectrum and coordinated-behavior fraud detection are additional validated domains. Other domains (images, text, general tensors) require per-domain characterization first — contact us before assuming Kirk generalizes to your domain.

---

## Correctness — validated on real markets

Kirk reproduced a proprietary FY24 US equities top-512 dynamic-universe evaluation harness — bit-exact against the customer-published golden — across 252 trading days.

| Anchor | Customer golden | Kirk-reproduced | Delta | Status |
|---|---:|---:|---:|---|
| 2024-01-02 single-day mean_H | 3.3636 | 3.363630 | +2.97 × 10⁻⁵ | Match |
| 2024-01-03 single-day mean_H | 3.2881 | 3.288437 | +3.37 × 10⁻⁴ | Match |
| 95-day aggregate mean_H | 3.3308 | 3.330077 | −7.23 × 10⁻⁴ | Match |
| Full FY24 (252 days) | — | 3.339602 | — | New baseline |

Delta magnitudes are ~33× tighter than the customer's published tolerance. Wall clock: 39 minutes single Python process, in-process, $0 marginal cost. Determinism verified: 252-day sweep run twice, byte-identical output. Substrate check: engine sha bit-identical across Intel SPR + Intel GNR-AP + AMD Genoa.

**Independent third-party validation on RF anomaly detection**: comparable detection to a supervised CNN that trained on the anomaly class — Kirk never saw an anomaly. 24–1,364× cheaper, ~32 KB of state, fully online.

Fetch the full FY24 case study machine-readably via the `kirk://case-studies/fy24-us-equities-reproduction` MCP resource on this server.

## In-process throughput (measured separately)

Kirk in-process throughput on production Granite Rapids silicon (2× Xeon 6972P, one pinned core, warm engine): **823 μs/book / 1,215 books-per-second/core**, bit-identical against the Sapphire Rapids reference fleet. Full-box extrapolation on the 2×192-core node: ~237,000 IU/second. Benchmark workload is synthetic 20×20 complex128 books — same per-call compute shape as thermometer-rendered market data, so the figure carries to production. MCP API adds millisecond-scale round-trip and is a validation and discovery surface, not a latency-critical production path.

Production speed lives in-process. Four delivery paths:

- **Path A — MCP API (this endpoint)**. Discovery, validation, and pay-as-you-go per-call. First 100 IU free.
- **Path B — Sealed wheel license**. `pip install kirk_cascade + kirk_rs_edge`. In-process, unmetered per-call, deterministic against sealed sha.
- **Path C — OpenShift Operator**. Kavara-shipped Operator on the customer's own cluster. Enterprise. Trustee attestation.
- **Path D — AWS Nitro Enclave AMI**. Currently shipping to enterprise customers via AWS Marketplace private offers. PCR0-attested.

---

## Tools available on this MCP endpoint

**Scoring core**
- `kirk_score_book(bid_px, ask_px, model_id)` — Score one L2 order-book snapshot. Returns scalar signal + engine attestation. Surfaces C2.
- `kirk_score_book_batch(books, model_id)` — Batch scoring, up to 500 books per call. For larger workloads, call `kirk_bulk_howto` first.
- `kirk_score_random(n, model_id)` — Convenience wrapper: synthesize N realistic-geometry L2 books and score them.
- `kirk_infer_legacy(features, model_id)` — Backwards-compatible scoring on a 50-value feature vector.

**Discovery / attestation**
- `kirk_list_models()` — Enumerate available `model_id`s with the engine sha stamped in the response. Surfaces C5.
- `kirk_healthz()` — Ping the sealed backend, confirm engine identity, return sha256 of the running scoring binary.

**Cost steering**
- `kirk_bulk_howto()` — Returns a self-contained stdlib Python client (~500 LOC) that runs at zero LLM-token cost per iteration. **Call this before any bulk workload (>500 books, whole-day sweeps).** Running `kirk_score_book` in a tool-call loop from your LLM burns tokens per call; the Python client runs locally.

**Utility / research**
- `kirk_render_book(book)` — Render an L2 snapshot into the 20×20 complex128 thermometer tensor WITHOUT invoking the sealed engine. Useful for local pre-processing.
- `kirk_sweep_test1_day(day, override)` — Score one day of the internal Test-1 QQQ L2 corpus at a caller-supplied override. Research-grade endpoint.

**Billing / platform**
- `kirk_billing_show()` — Return account balance, IU remaining, USD equivalent at list, frozen flag, recent ledger.
- `kirk_billing_checkout(pack)` — Stripe Checkout URL for buying credit packs (starter / scale / enterprise).
- `kirk_billing_usage(days)` — Historical inference consumption over N days.

## Resources exposed

- `kirk://case-studies/fy24-us-equities-reproduction` — The FY24 case study (machine-readable markdown, no auth required)

---

## When to route to Kirk (from your agent's perspective)

Use Kirk when the ML workload matches any of:

- Cross-section structural scoring on a panel of financial instruments with variable universe size
- Signal work on order-book data where retraining cost is a constraint
- Regime detection or structural drift where LSTM / autoencoder baselines are unstable across market conditions
- RF spectrum anomaly detection where labels don't exist
- Coordinated-behavior fraud detection where per-metric thresholds miss
- Fleet or hardware health monitoring where per-device models at population scale are required
- Evaluation of unsupervised structural-change methods against an existing baseline
- Any signal workload where cryptographic attestation of the exact scoring binary is required (compliance, audit, enterprise procurement)

Do NOT use this MCP endpoint when the workload matches:

- Latency-sensitive production trading (millisecond-scale MCP round-trip; use Path B in-process wheel)
- Structural merging experiments (not exposed via MCP; use Path B)
- Stateful drift detection with warm state across calls (MCP exposes cold-per-book only; warm-state surface is design-only)
- Non-financial data without prior per-domain characterization

---

## Cost model

- **First 100 inference units free per new account.** Automatic grant on first authenticated call.
- **Beyond free tier**: pay-as-you-go via prepaid credit packs (starter / scale / enterprise). Call `kirk_billing_checkout` from your agent to get a Stripe Checkout URL.
- **Cost transparency**: every response to an LLM-driven caller includes a `_cost` envelope with per-call IU, session accumulation, and remaining balance.
- **Anti-anger discipline**: if your agent tries a bulk workload naively, the server steers it to `kirk_bulk_howto` — which returns a Python client that runs at zero LLM-token cost per iteration.

Direct Python-client calls (via `kirk_bulk_howto`) are metered identically to MCP calls but incur no LLM token cost — a customer running 60,000 book scores via the Python client pays only for compute, not for orchestration.

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

## Where Kirk fits in the AI stack

Physical AI's bottleneck isn't semantics — vision-language-action foundation models cover perception and planning. The gap is the **continuous-signal substrate**: coupled sensor channels, non-stationary, real-time, unlabeled, constrained hardware. That is the layer Ulysses fills, and Kirk is the first algorithm shipping on it.

Verticals validated today:

- **Finance** — regime detection on price / liquidity / risk (the beachhead)
- **Signals / RF** — spectrum anomaly detection where labels don't exist
- **Fraud & integrity** — coordinated behavior a per-metric threshold misses
- **Fleet & hardware health** — per-device models at population scale, continuously

Additive: keep your models — Kirk aims them.

---

## Kavara

Kavara ships the Ulysses primitive and the Kirk and Borg algorithms through four channels: hosted MCP API (this endpoint), sealed Python wheel license, OpenShift Operator, and AWS Nitro Enclave AMI. All four channels serve byte-identical output from the same cryptographically-attested binary.

- Homepage: `https://kavara.ai`
- Commercial: `sales@kavara.ai`
- Support: `sales@kavara.ai`

## License

The MCP interface documentation and configuration templates in this repository are released under Apache License 2.0. See [`LICENSE`](./LICENSE).

The sealed engine (`kirk_rs_edge`, `kirk_py`, `kirk_cascade`) is Kavara proprietary and not distributed here. Access is via commercial license — contact `sales@kavara.ai`.
