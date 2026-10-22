"""Explicit v1 route contract for a run and its binding."""

import re

CONTRACT_VERSION = "v1"

# Cadence and loader values this route can run exactly as submitted.
# Any other value is refused rather than rewritten.
ACCEPTED_CADENCE = frozenset({"ordered"})
ACCEPTED_LOADER = frozenset({"inline"})

MODEL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
RELEASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

PUBLIC_API_ORIGIN = "https://api.kavara.ai"
CATALOG_PATH = "/v1/models"
SCORE_PATH = "/v1/score-book"

# Published customer REST body limit.
MAX_BODY_BYTES = 256 * 1024

ROUTES = (
    ("POST", "/v1/runs"),
    ("POST", "/v1/runs/{run_id}/execution"),
    ("GET", "/v1/runs/{run_id}"),
    ("POST", "/v1/runs/{run_id}/stamp"),
)
