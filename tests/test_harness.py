import pytest
import os
import sys
import subprocess

HARNESS_PATH = os.path.join(os.path.dirname(__file__), "gnr_validation_harness.py")


def test_harness_mock_success():
    """Test that the harness passes in mock mode with correct defaults."""
    env = os.environ.copy()
    res = subprocess.run(
        [sys.executable, HARNESS_PATH, "--mock"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "[SUCCESS] Validation passed." in res.stdout


def test_harness_mock_sha_mismatch():
    """Test that the harness fails when expected SHA mismatches mock SHA."""
    env = os.environ.copy()
    env["KIRK_EXPECTED_SHA"] = "invalid-sha-1234"
    res = subprocess.run(
        [sys.executable, HARNESS_PATH, "--mock"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "Provenance mismatch!" in res.stdout
    assert "[ROLLBACK] Validation failed." in res.stdout


def test_harness_mock_latency_failure():
    """Test that the harness fails if the latency threshold is too low."""
    env = os.environ.copy()
    env["KIRK_MAX_LATENCY_S"] = "0.001"  # Mock has 0.01s sleep, so this should fail
    res = subprocess.run(
        [sys.executable, HARNESS_PATH, "--mock"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "[FAIL] Concurrency latency gate failed." in res.stdout
    assert "[ROLLBACK] Validation failed." in res.stdout
