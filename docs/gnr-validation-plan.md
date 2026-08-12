# GNR Validation Plan & Rollback Criteria

## Metrics to Measure
1. **Latency (Single/Batch)**: Round-trip HTTP latency via client.
2. **Concurrency**: Execute N concurrent requests and assert latency constraints.
3. **Service Health**: 100% success rate on `kirk_healthz`.
4. **Provenance**: The `engine_sha` returned in the response matches the expected Kavara published manifest (`f3c5...`).
5. **Host Telemetry**: Memory peak (RSS), throughput, and instruction utilization (AVX/AMX) **cannot be evaluated** via the MCP client interface. These must be verified out-of-band by infrastructure metrics before final right-sizing.

## Executable Gates
The test suite `gnr_validation_harness.py` acts as an executable pass/fail gate. It requires:
- Health check success.
- `engine_sha` exact match.
- Concurrency responses within latency threshold.

## Rollback Criteria
If the harness fails (exits non-zero) after the GNR migration, traffic must be routed back to the stopped `kirk-nitro` instance.
