"""Versioned run binding in front of the public HTTP API."""

from kirk_runs.contract import CONTRACT_VERSION
from kirk_runs.service import RunService

__all__ = ["CONTRACT_VERSION", "RunService"]
