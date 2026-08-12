# GNR Validation Plan & Rollback Criteria

## Metrics to Measure
1. **Memory Peak**: Observe maximum resident set size (RSS) during batch workloads.
2. **Startup Time**: Time to first successful `kirk_healthz` response.
3. **Latency (Single/Batch)**: Round-trip HTTP latency for `kirk_score_random(n=1)` and `kirk_score_random(n=500)`.
4. **Throughput/Concurrency**: Total books processed per second across concurrent client threads.
5. **Instruction Utilization (AVX/AMX)**: Verify the engine utilizes GNR-specific instructions (AVX-512/AMX) if measurable from the host.
6. **Service Health**: 100% success rate on `kirk_healthz`.
7. **Provenance**: The `engine_sha` matches the expected Kavara published manifest.

## Rollback Criteria
If any of the following occur during or after the GNR migration, traffic must be routed back to the stopped `kirk-nitro` instance:
- Health check failure rate > 0%.
- Latency increases by > 20% compared to Nitro baseline.
- `engine_sha` mismatch or attestation failure.
- Out of Memory (OOM) errors under target concurrency.
