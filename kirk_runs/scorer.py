"""Call the sealed HTTP API for catalog lookup and scoring.

The published model package scores through a local core, which this service
does not import. Scoring here is only ``POST`` of the public score route.
"""

import json
import uuid
import urllib.error
import urllib.request

from kirk_runs.contract import (
    CATALOG_PATH,
    MAX_BODY_BYTES,
    SCORE_PATH,
    SEALED_API_ORIGIN,
)
from kirk_runs.errors import RunsError


class ScoreResult(object):
    def __init__(self, release_id, value):
        self.release_id = release_id
        self.value = value


class SealedScorer(object):
    def __init__(self, api_key, base_url=SEALED_API_ORIGIN, timeout=40):
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def catalog_model_ids(self):
        payload = self._request("GET", CATALOG_PATH, None, None)
        return _model_ids(payload)

    def score(self, model_id, item):
        if not isinstance(item, dict):
            raise RunsError("binding_refused", 422, {"field": "inputs"})
        body = dict(item)
        supplied = body.get("model_id")
        if supplied is not None and supplied != model_id:
            raise RunsError("binding_refused", 422, {"field": "model_id"})
        body["model_id"] = model_id
        encoded = json.dumps(
            body, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        if len(encoded) > MAX_BODY_BYTES:
            raise RunsError("request_too_large", 413)
        payload = self._request("POST", SCORE_PATH, encoded, str(uuid.uuid4()))
        return _score_result(payload)

    def _request(self, method, path, encoded, idempotency_key):
        headers = {
            "Accept": "application/json",
            "X-Kavara-Key": self.api_key,
        }
        if encoded is not None:
            headers["Content-Type"] = "application/json"
            headers["Idempotency-Key"] = idempotency_key
        request = urllib.request.Request(
            self.base_url + path,
            data=encoded,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as error:
            raise RunsError("score_rejected", 502, {"upstream_status": error.code})
        except urllib.error.URLError:
            raise RunsError("origin_unavailable", 502)
        if status != 200:
            raise RunsError("score_rejected", 502, {"upstream_status": status})
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            raise RunsError("unbound_result", 502)
        if (
            not isinstance(payload, dict)
            or "result" not in payload
            or len(payload) != 1
        ):
            raise RunsError("unbound_result", 502)
        return payload["result"]


def _model_ids(result):
    if isinstance(result, dict):
        entries = result.get("models")
    else:
        entries = result
    if not isinstance(entries, list) or not entries:
        raise RunsError("unbound_result", 502)
    model_ids = []
    for entry in entries:
        if isinstance(entry, str):
            model_ids.append(entry)
        elif isinstance(entry, dict) and isinstance(entry.get("model_id"), str):
            model_ids.append(entry["model_id"])
        else:
            raise RunsError("unbound_result", 502)
    return model_ids


def _score_result(result):
    if not isinstance(result, dict):
        raise RunsError("unbound_result", 502)
    release_id = result.get("release_id")
    if not isinstance(release_id, str) or not release_id:
        raise RunsError("unbound_result", 502)
    value = result.get("output", None)
    if "output" in result and not _json_value(value):
        raise RunsError("unbound_result", 502)
    return ScoreResult(release_id, value if "output" in result else None)


def _json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _json_value(item) for key, item in value.items()
        )
    return False
