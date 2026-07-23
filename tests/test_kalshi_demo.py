from __future__ import annotations

import base64
import unittest
from typing import Dict, List, Tuple
from urllib.request import Request

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from kirk_mcp.kalshi_demo import (
    ACCOUNT_LIMITS_METHOD,
    ACCOUNT_LIMITS_PATH,
    ACCOUNT_LIMITS_URL,
    BASE_URL_VARIABLE,
    DEMO_BASE_URL,
    DEMO_ENVIRONMENT,
    DEMO_PROFILE,
    ENVIRONMENT_VARIABLE,
    PROFILE_VARIABLE,
    ConfigurationError,
    ConnectivityError,
    DemoAccountStatusSmoke,
    DemoConfig,
    DemoCredentials,
    DemoSmokeResult,
    format_smoke_result,
    sign_request,
    signing_message,
)


def valid_environment() -> Dict[str, str]:
    return {
        ENVIRONMENT_VARIABLE: DEMO_ENVIRONMENT,
        PROFILE_VARIABLE: DEMO_PROFILE,
        BASE_URL_VARIABLE: DEMO_BASE_URL,
    }


class DemoConfigurationTests(unittest.TestCase):
    def test_accepts_only_explicit_official_demo_configuration(self) -> None:
        self.assertEqual(
            DemoConfig.from_environment(valid_environment()),
            DemoConfig(DEMO_ENVIRONMENT, DEMO_PROFILE, DEMO_BASE_URL),
        )

    def test_rejects_production_and_live_hosts(self) -> None:
        for host in (
            "https://external-api.kalshi.com/trade-api/v2",
            "https://api.elections.kalshi.com/trade-api/v2",
            "https://kalshi.com/trade-api/v2",
        ):
            with self.subTest(host=host), self.assertRaises(ConfigurationError):
                env = valid_environment()
                env[BASE_URL_VARIABLE] = host
                DemoConfig.from_environment(env)

    def test_rejects_supported_but_non_allowlisted_demo_host(self) -> None:
        env = valid_environment()
        env[BASE_URL_VARIABLE] = "https://demo-api.kalshi.co/trade-api/v2"
        with self.assertRaises(ConfigurationError):
            DemoConfig.from_environment(env)

    def test_rejects_missing_or_ambiguous_environment_and_profile(self) -> None:
        cases = []
        for missing in (ENVIRONMENT_VARIABLE, PROFILE_VARIABLE):
            env = valid_environment()
            del env[missing]
            cases.append(env)
        for name, value in (
            (ENVIRONMENT_VARIABLE, "DEMO"),
            (ENVIRONMENT_VARIABLE, "production"),
            (PROFILE_VARIABLE, "default"),
            (PROFILE_VARIABLE, "live"),
        ):
            env = valid_environment()
            env[name] = value
            cases.append(env)
        for env in cases:
            with self.subTest(env=env), self.assertRaises(ConfigurationError):
                DemoConfig.from_environment(env)

    def test_missing_host_has_no_default_or_production_fallback(self) -> None:
        env = valid_environment()
        del env[BASE_URL_VARIABLE]
        with self.assertRaisesRegex(ConfigurationError, "no host fallback"):
            DemoConfig.from_environment(env)

    def test_rejects_live_credential_variable_names_and_unknown_profile_variables(self) -> None:
        for name in (
            "KALSHI_API_KEY_ID",
            "KALSHI_PRIVATE_KEY",
            "KALSHI_PROD_API_KEY",
            "KIRK_KALSHI_LIVE_PROFILE",
            "KIRK_CF_ACCESS_CLIENT_ID",
            "KIRK_CF_ACCESS_CLIENT_SECRET",
        ):
            with self.subTest(name=name), self.assertRaises(ConfigurationError):
                env = valid_environment()
                env[name] = "not-a-real-secret"
                DemoConfig.from_environment(env)


class SigningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def test_message_uses_millisecond_timestamp_upper_method_full_v2_path_without_query(self) -> None:
        self.assertEqual(
            signing_message(
                "1703123456789",
                "GET",
                ACCOUNT_LIMITS_PATH + "?ignored=yes",
            ),
            b"1703123456789GET/trade-api/v2/account/limits",
        )

    def test_signature_is_base64_rsa_pss_sha256_with_digest_length_salt(self) -> None:
        timestamp = "1703123456789"
        encoded = sign_request(
            self.private_key,
            timestamp,
            ACCOUNT_LIMITS_METHOD,
            ACCOUNT_LIMITS_PATH,
        )
        signature = base64.b64decode(encoded, validate=True)
        self.private_key.public_key().verify(
            signature,
            signing_message(timestamp, ACCOUNT_LIMITS_METHOD, ACCOUNT_LIMITS_PATH),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        with self.assertRaises(InvalidSignature):
            self.private_key.public_key().verify(
                signature,
                b"1703123456789POST/trade-api/v2/account/limits",
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )


class SmokeWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.credentials = DemoCredentials(
            key_id="sensitive-demo-key-id",
            private_key=self.private_key,
        )
        self.config = DemoConfig.from_environment(valid_environment())

    def test_uses_only_intended_read_only_account_endpoint_and_method(self) -> None:
        calls: List[Tuple[Request, float]] = []

        def transport(request: Request, timeout: float) -> int:
            calls.append((request, timeout))
            return 200

        result = DemoAccountStatusSmoke(
            self.config,
            self.credentials,
            transport=transport,
            clock_ms=lambda: 1703123456789,
        ).run()

        self.assertEqual(result, DemoSmokeResult(http_status=200))
        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        self.assertEqual(request.full_url, ACCOUNT_LIMITS_URL)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(timeout, 10.0)
        self.assertNotIn("portfolio", request.full_url)
        self.assertNotIn("order", request.full_url)
        self.assertEqual(request.headers["Kalshi-access-timestamp"], "1703123456789")

    def test_output_is_demo_labeled_allowlist_and_redacts_all_sensitive_values(self) -> None:
        output = format_smoke_result(DemoSmokeResult(http_status=200))
        self.assertIn("DEMO", output)
        self.assertIn("response_body: discarded", output)
        for sensitive in (
            self.credentials.key_id,
            "KALSHI-ACCESS-SIGNATURE",
            "private key",
            "usage_tier",
            "bucket_capacity",
        ):
            self.assertNotIn(sensitive, output)

    def test_custom_transport_exception_cannot_leak_secret_or_response(self) -> None:
        def bad_transport(request: Request, timeout: float) -> int:
            raise RuntimeError(
                self.credentials.key_id + " raw-private-response usage_tier=expert"
            )

        with self.assertRaises(ConnectivityError) as caught:
            DemoAccountStatusSmoke(
                self.config,
                self.credentials,
                transport=bad_transport,
            ).run()
        message = str(caught.exception)
        self.assertNotIn(self.credentials.key_id, message)
        self.assertNotIn("raw-private-response", message)
        self.assertNotIn("expert", message)

    def test_network_boundary_rejects_manually_constructed_live_config(self) -> None:
        live = DemoConfig(
            DEMO_ENVIRONMENT,
            DEMO_PROFILE,
            "https://external-api.kalshi.com/trade-api/v2",
        )
        called = False

        def transport(request: Request, timeout: float) -> int:
            nonlocal called
            called = True
            return 200

        with self.assertRaises(ConfigurationError):
            DemoAccountStatusSmoke(live, self.credentials, transport=transport).run()
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
