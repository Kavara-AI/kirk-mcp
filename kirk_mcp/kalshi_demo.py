"""Strictly DEMO-only Kalshi authentication and account-status smoke check.

Official contract verified 2026-03-19:
- environments/API v2: https://docs.kalshi.com/getting_started/api_environments
- signing/headers: https://docs.kalshi.com/getting_started/quick_start_authenticated_requests
- read-only account endpoint: https://docs.kalshi.com/api-reference/account/get-account-api-limits

This module deliberately has no order, cancellation, portfolio, or generic-request API.
"""

from __future__ import annotations

import argparse
import base64
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

DEMO_ENVIRONMENT = "demo"
DEMO_PROFILE = "personal-demo-paper"
DEMO_BASE_URL = "https://external-api.demo.kalshi.co/trade-api/v2"
DEMO_HOST = "external-api.demo.kalshi.co"
ACCOUNT_LIMITS_PATH = "/trade-api/v2/account/limits"
ACCOUNT_LIMITS_URL = DEMO_BASE_URL + "/account/limits"
ACCOUNT_LIMITS_METHOD = "GET"

ENVIRONMENT_VARIABLE = "CASH_IN_HAND_KALSHI_ENV"
PROFILE_VARIABLE = "CASH_IN_HAND_KALSHI_PROFILE"
BASE_URL_VARIABLE = "CASH_IN_HAND_KALSHI_DEMO_BASE_URL"
_ALLOWED_CONFIGURATION_VARIABLES = frozenset(
    {ENVIRONMENT_VARIABLE, PROFILE_VARIABLE, BASE_URL_VARIABLE}
)
_CORPORATE_CREDENTIAL_VARIABLES = frozenset(
    {"KIRK_CF_ACCESS_CLIENT_ID", "KIRK_CF_ACCESS_CLIENT_SECRET"}
)

# This is a fixed role label, never the captain's exact Kalshi login identifier.
KEYCHAIN_ACCOUNT = "personal-demo-paper"
KEYCHAIN_API_KEY_SERVICE = "project-cash-in-hand.kalshi-personal-demo.api-key-id"
KEYCHAIN_PRIVATE_KEY_SERVICE = "project-cash-in-hand.kalshi-personal-demo.private-key"


class DemoKalshiError(Exception):
    """Base class for errors whose messages are safe for operator output."""


class ConfigurationError(DemoKalshiError):
    """The explicit DEMO-only configuration gate was not satisfied."""


class CredentialStoreError(DemoKalshiError):
    """Credentials could not be loaded without exposing credential contents."""


class ConnectivityError(DemoKalshiError):
    """The read-only DEMO connectivity check failed."""


@dataclass(frozen=True)
class DemoConfig:
    environment: str
    profile: str
    base_url: str

    @classmethod
    def from_environment(cls, environment: Optional[Mapping[str, str]] = None) -> "DemoConfig":
        env = os.environ if environment is None else environment
        _reject_credential_and_ambiguous_variables(env)

        if env.get(ENVIRONMENT_VARIABLE) != DEMO_ENVIRONMENT:
            raise ConfigurationError(
                "DEMO refused: CASH_IN_HAND_KALSHI_ENV must be explicitly set to demo"
            )
        if env.get(PROFILE_VARIABLE) != DEMO_PROFILE:
            raise ConfigurationError(
                "DEMO refused: CASH_IN_HAND_KALSHI_PROFILE must be explicitly set to personal-demo-paper"
            )
        if BASE_URL_VARIABLE not in env:
            raise ConfigurationError(
                "DEMO refused: CASH_IN_HAND_KALSHI_DEMO_BASE_URL is required; no host fallback exists"
            )
        if env[BASE_URL_VARIABLE] != DEMO_BASE_URL:
            raise ConfigurationError(
                "DEMO refused: base URL is not the single allowlisted official DEMO API v2 URL"
            )

        return cls(
            environment=DEMO_ENVIRONMENT,
            profile=DEMO_PROFILE,
            base_url=DEMO_BASE_URL,
        )


def _reject_credential_and_ambiguous_variables(env: Mapping[str, str]) -> None:
    for name in env:
        # Credentials are never accepted from environment variables. This also
        # prevents accidental reuse of shared/corporate KIRK_KALSHI_* configuration.
        if (
            name.startswith("KALSHI_")
            or name.startswith("KIRK_KALSHI_")
            or name in _CORPORATE_CREDENTIAL_VARIABLES
        ):
            raise ConfigurationError(
                "DEMO refused: shared, corporate, live, or conventional Kalshi environment variables are prohibited; use the fixed personal-DEMO Keychain entries"
            )
        if name.startswith("CASH_IN_HAND_KALSHI_") and name not in _ALLOWED_CONFIGURATION_VARIABLES:
            raise ConfigurationError(
                "DEMO refused: unrecognized CASH_IN_HAND_KALSHI_* variable makes the environment ambiguous"
            )


@dataclass(frozen=True)
class DemoCredentials:
    key_id: str
    private_key: rsa.RSAPrivateKey


class MacOSKeychainCredentialStore:
    """Read the two fixed DEMO entries from the macOS login Keychain."""

    security_executable = "/usr/bin/security"

    def load(self) -> DemoCredentials:
        key_id_bytes = self._read_password(KEYCHAIN_API_KEY_SERVICE)
        private_key_pem = self._read_password(KEYCHAIN_PRIVATE_KEY_SERVICE)

        try:
            key_id = key_id_bytes.decode("utf-8").strip()
            private_key = serialization.load_pem_private_key(private_key_pem, password=None)
        except (UnicodeDecodeError, TypeError, ValueError):
            raise CredentialStoreError(
                "DEMO credential entries are invalid; credential contents suppressed"
            )
        if not key_id or not isinstance(private_key, rsa.RSAPrivateKey):
            raise CredentialStoreError(
                "DEMO credential entries are invalid; credential contents suppressed"
            )
        return DemoCredentials(key_id=key_id, private_key=private_key)

    def _read_password(self, service: str) -> bytes:
        if sys.platform != "darwin":
            raise CredentialStoreError(
                "DEMO credentials require the approved macOS Keychain integration"
            )
        try:
            completed = subprocess.run(
                [
                    self.security_executable,
                    "find-generic-password",
                    "-a",
                    KEYCHAIN_ACCOUNT,
                    "-s",
                    service,
                    "-w",
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            raise CredentialStoreError(
                "DEMO credential lookup failed; credential contents suppressed"
            )
        if completed.returncode != 0 or not completed.stdout:
            raise CredentialStoreError(
                "DEMO credential lookup failed; install the documented fixed Keychain entries"
            )
        # `security -w` appends one output newline. Removing only that delimiter
        # preserves PEM formatting while keeping the raw value out of diagnostics.
        return completed.stdout[:-1] if completed.stdout.endswith(b"\n") else completed.stdout


def signing_message(timestamp_ms: str, method: str, path: str) -> bytes:
    """Build Kalshi's timestamp + method + path payload (query omitted)."""
    if not timestamp_ms.isdecimal():
        raise ValueError("timestamp_ms must be decimal milliseconds")
    if method != method.upper() or not method:
        raise ValueError("HTTP method must be non-empty uppercase text")
    path_without_query = path.split("?", 1)[0]
    if not path_without_query.startswith("/trade-api/v2/"):
        raise ValueError("signed path must be an absolute Trade API v2 path")
    return (timestamp_ms + method + path_without_query).encode("utf-8")


def sign_request(
    private_key: rsa.RSAPrivateKey,
    timestamp_ms: str,
    method: str,
    path: str,
) -> str:
    """Create the documented base64 RSA-PSS/SHA-256 signature."""
    signature = private_key.sign(
        signing_message(timestamp_ms, method, path),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        raise ConnectivityError("DEMO connectivity check refused an HTTP redirect")


class DemoAccountStatusTransport:
    """Transport fixed to exactly one HTTPS GET; response bodies are never read."""

    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(_RejectRedirects())

    def __call__(self, request: urllib.request.Request, timeout: float) -> int:
        if request.full_url != ACCOUNT_LIMITS_URL or request.get_method() != ACCOUNT_LIMITS_METHOD:
            raise ConnectivityError("DEMO smoke transport refused a non-allowlisted request")
        try:
            with self._opener.open(request, timeout=timeout) as response:
                return int(response.status)
        except ConnectivityError:
            raise
        except urllib.error.HTTPError as error:
            # Do not read or include the response body or headers.
            raise ConnectivityError(
                "DEMO account-status check failed with HTTP status %d; response discarded"
                % error.code
            )
        except (urllib.error.URLError, OSError, ValueError):
            raise ConnectivityError(
                "DEMO account-status connectivity failed; details and response suppressed"
            )


@dataclass(frozen=True)
class DemoSmokeResult:
    http_status: int


class DemoAccountStatusSmoke:
    """No-order workflow exposing only GET /account/limits."""

    def __init__(
        self,
        config: DemoConfig,
        credentials: DemoCredentials,
        transport: Optional[Callable[[urllib.request.Request, float], int]] = None,
        clock_ms: Optional[Callable[[], int]] = None,
        timeout: float = 10.0,
    ) -> None:
        self._config = config
        self._credentials = credentials
        self._transport = transport or DemoAccountStatusTransport()
        self._clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._timeout = timeout

    def run(self) -> DemoSmokeResult:
        # Recheck immutable values at the network boundary: no host/profile fallback
        # can be introduced by constructing DemoConfig manually.
        if (
            self._config.environment != DEMO_ENVIRONMENT
            or self._config.profile != DEMO_PROFILE
            or self._config.base_url != DEMO_BASE_URL
        ):
            raise ConfigurationError("DEMO refused: configuration failed the network-boundary gate")

        timestamp_ms = str(self._clock_ms())
        signature = sign_request(
            self._credentials.private_key,
            timestamp_ms,
            ACCOUNT_LIMITS_METHOD,
            ACCOUNT_LIMITS_PATH,
        )
        request = urllib.request.Request(
            ACCOUNT_LIMITS_URL,
            method=ACCOUNT_LIMITS_METHOD,
            headers={
                "KALSHI-ACCESS-KEY": self._credentials.key_id,
                "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
                "KALSHI-ACCESS-SIGNATURE": signature,
                "Accept": "application/json",
            },
        )
        try:
            status = self._transport(request, self._timeout)
        except DemoKalshiError:
            raise
        except Exception:
            # Injected/custom transports cannot leak request headers through CLI output.
            raise ConnectivityError(
                "DEMO account-status connectivity failed; details and response suppressed"
            )
        if status != 200:
            raise ConnectivityError(
                "DEMO account-status check returned a non-success status; response discarded"
            )
        return DemoSmokeResult(http_status=status)


def format_smoke_result(result: DemoSmokeResult) -> str:
    """Return an allowlisted projection; no response or credential value is accepted."""
    return "\n".join(
        [
            "DEMO Kalshi connectivity/account status: OK",
            "environment: PERSONAL DEMO (paper trading only; not live-market evidence)",
            "host: " + DEMO_HOST,
            "request: GET " + ACCOUNT_LIMITS_PATH,
            "http_status: %d" % result.http_status,
            "account_status: authenticated account API limits accessible",
            "response_body: discarded",
        ]
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="No-order Kalshi DEMO authenticated account-status smoke check"
    )
    parser.parse_args(argv)
    try:
        config = DemoConfig.from_environment()
        credentials = MacOSKeychainCredentialStore().load()
        result = DemoAccountStatusSmoke(config, credentials).run()
    except DemoKalshiError as error:
        print("DEMO Kalshi connectivity/account status: FAILED", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1
    print(format_smoke_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
