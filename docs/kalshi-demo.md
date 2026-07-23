# Kalshi DEMO-only client

This integration is exclusively for the captain's personal Kalshi simulated **DEMO** environment. It must not be configured with, or used to infer anything about, a production account. It is not a Kavara corporate account or identity: Kavara technology is authorized only for this bounded personal evaluation. Personal account data and credentials must remain segregated from corporate identities, credential stores, profiles, and systems. DEMO fills and data are not live-market evidence. The current workflow cannot place or cancel orders: it makes one authenticated, read-only account request and discards the response body.

This is the connectivity/setup stage of **Project Cash in Hand**, whose later personal paper-trading evaluation will test the hypothesis—not promise—that a strategy could contribute toward an aspirational `$500/day` target. Any later evaluation must report net results after fees, spread, slippage, partial fills, and data/compute costs, together with drawdown, capital at risk, liquidity, variance, losing days, and sample size. None of that evaluation or any order workflow is part of this smoke check.

The first and only current objective is to evaluate repeatable net value for the captain's own personal account. Any Kavara productization would require a later, separate authorization and review. This setup grants no authority to sell, market, publish, redistribute, contact providers or customers, manage third-party accounts, trade for others, or present DEMO results as evidence of live profitability. Personal, customer, and corporate accounts, data, credentials, and systems must remain strictly segregated.

## Verified official contract

Verified against Kalshi's official documentation on 2026-03-19:

- [API environments and endpoints](https://docs.kalshi.com/getting_started/api_environments): Predictions Trade API v2; recommended DEMO base URL `https://external-api.demo.kalshi.co/trade-api/v2`; DEMO and production credentials are separate.
- [Authenticated requests](https://docs.kalshi.com/getting_started/quick_start_authenticated_requests): required `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-TIMESTAMP`, and `KALSHI-ACCESS-SIGNATURE` headers; current Unix time in milliseconds; signature payload is `timestamp + HTTP_METHOD + full path without query`; RSA-PSS with SHA-256 and digest-length salt; base64 output.
- [Get Account API Limits](https://docs.kalshi.com/api-reference/account/get-account-api-limits): authenticated read-only `GET /trade-api/v2/account/limits`. This is the narrow account endpoint used by the smoke check. No portfolio, balance, position, fill, order, or cancellation endpoint is accessed.

The client requires all three personal-DEMO configuration values explicitly, uses one exact host allowlist, rejects every conventional `KALSHI_*`, every shared/corporate `KIRK_KALSHI_*`, the corporate MCP credential variables, and every unknown `CASH_IN_HAND_KALSHI_*` variable, and has no default host.

## Secure credential installation

Requirements:

```bash
python3 -m pip install -r requirements-kalshi-demo.txt
```

Create the key only in the captain's existing personal Kalshi **demo** account. Never supply a production or corporate key. From the repository root, perform the required interactive installation directly into the captain's local macOS Keychain:

```bash
python3 -m kirk_mcp.install_kalshi_demo_credentials --private-key-file /absolute/path/to/downloaded-demo.key
```

The command first requires the explicit text confirmation `PERSONAL DEMO`, then prompts invisibly for the DEMO API key ID and transfers the private key file into Keychain through macOS Security.framework without putting either credential value in subprocess arguments or output. It never asks for or stores the captain's exact Kalshi login identifier. It creates only these fixed personal-role entries:

| Keychain field | Identifier |
|---|---|
| account role label (not a login) | `personal-demo-paper` |
| API key ID service | `project-cash-in-hand.kalshi-personal-demo.api-key-id` |
| private key service | `project-cash-in-hand.kalshi-personal-demo.private-key` |

Keep key material outside this repository and remove the downloaded source key securely after installation. Do not put credentials in environment variables, command-line arguments, config files, logs, prompt text, fixtures, or snapshots; enter the API key ID only through the installer's hidden interactive input.

## No-order connectivity/account-status smoke

Run only this explicit DEMO profile, using a clean process environment so corporate credentials are not inherited:

```bash
env -i HOME="$HOME" PATH="$PATH" \
CASH_IN_HAND_KALSHI_ENV=demo \
CASH_IN_HAND_KALSHI_PROFILE=personal-demo-paper \
CASH_IN_HAND_KALSHI_DEMO_BASE_URL=https://external-api.demo.kalshi.co/trade-api/v2 \
python3 -m kirk_mcp.kalshi_demo
```

Success output is labeled `DEMO` and contains only the allowlisted host, fixed method/path, HTTP status, and an authenticated-account summary. Credential values, signatures, response headers, and the account-limits response body are never printed or preserved. Redirects and every other host, path, or method are refused.
