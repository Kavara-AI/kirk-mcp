"""Submit, execute, retrieve, and stamp one run."""

import copy
import math
import threading
import uuid

from kirk_runs.binding import assert_same_inputs, inputs_digest, stamp_references
from kirk_runs.contract import (
    ACCEPTED_CADENCE,
    ACCEPTED_LOADER,
    CONTRACT_VERSION,
    MODEL_ID_PATTERN,
    RELEASE_ID_PATTERN,
)
from kirk_runs.errors import RunsError

_SUBMIT_FIELDS = frozenset({"release_id", "configuration", "inputs"})
_CONFIG_FIELDS = frozenset({"cadence", "loader", "model_id"})
_TERMINAL = frozenset({"succeeded", "failed", "partial", "refused"})


class RunService(object):
    def __init__(self, scorer):
        self._scorer = scorer
        self._runs = {}
        self._lock = threading.Lock()
        self._guards = {}

    def submit(self, body):
        with self._lock:
            run = _admit(body)
            self._runs[run["run_id"]] = run
            return _public_view(run)

    def execute(self, run_id):
        with self._guard(run_id):
            with self._lock:
                run = self._require(run_id)
                if run["status"] == "succeeded":
                    return _public_view(run)
                if run["status"] in _TERMINAL:
                    raise _stored_error(run)
                release_id = run["release_id"]
                model_id = run["configuration"]["model_id"]
                inputs = run["inputs"]
                run["computing_release_ids"] = []
                run["alignment"] = None
                run["error"] = None
            try:
                model_ids = self._scorer.catalog_model_ids()
            except RunsError as exc:
                raise self._settle(run, "failed", exc.public_error())
            except Exception:
                raise self._settle(run, "failed", {"code": "origin_unavailable"})
            if model_id not in model_ids:
                raise self._settle(
                    run,
                    "refused",
                    {"code": "binding_refused", "field": "model_id"},
                )
            held = []
            release_ids = []
            for item in inputs:
                try:
                    result = self._scorer.score(model_id, item)
                except RunsError as exc:
                    status = "partial" if held else "failed"
                    raise self._settle(run, status, exc.public_error())
                except Exception:
                    status = "partial" if held else "failed"
                    raise self._settle(run, status, {"code": "origin_unavailable"})
                release_ids.append(result.release_id)
                try:
                    stamp_references(release_id, release_ids)
                except RunsError as exc:
                    raise self._settle(
                        run,
                        "failed",
                        exc.public_error(),
                        computing_release_ids=release_ids,
                    )
                held.append(result)
            with self._lock:
                run["computing_release_ids"] = release_ids
                run["alignment"] = [
                    _alignment(index, item.value) for index, item in enumerate(held)
                ]
                run["status"] = "succeeded"
                run["error"] = None
                return _public_view(run)

    def _guard(self, run_id):
        with self._lock:
            self._require(run_id)
            guard = self._guards.get(run_id)
            if guard is None:
                guard = threading.Lock()
                self._guards[run_id] = guard
            return guard

    def _settle(self, run, status, error, computing_release_ids=None):
        with self._lock:
            run["status"] = status
            run["error"] = error
            run["alignment"] = None
            run["computing_release_ids"] = list(computing_release_ids or [])
            return _stored_error(run)

    def retrieve(self, run_id):
        with self._lock:
            run = self._require(run_id)
            view = _public_view(run)
            if run["status"] == "submitted" or run["status"] == "succeeded":
                return view
            raise _stored_error(run)

    def stamp(self, run_id, body):
        with self._lock:
            if body is None:
                body = {}
            if not isinstance(body, dict) or set(body) - {"inputs"}:
                raise RunsError("invalid_request", 400)
            run = self._require(run_id)
            if run["status"] in _TERMINAL and run["status"] != "succeeded":
                raise _stored_error(run)
            if not run["computing_release_ids"]:
                raise RunsError(
                    "not_executed",
                    409,
                    view=_stamp_refusal(run, {"code": "not_executed"}),
                )
            # Reference agreement is decided here, even when input order also disagrees.
            try:
                stamp_references(run["release_id"], run["computing_release_ids"])
            except RunsError as exc:
                raise RunsError(
                    exc.code,
                    exc.http_status,
                    exc.detail,
                    view=_stamp_refusal(run, exc.public_error()),
                )
            if run["status"] != "succeeded":
                raise _stored_error(run)
            if "inputs" in body:
                try:
                    _reject_nonfinite(body["inputs"], "inputs")
                    assert_same_inputs(run["inputs_digest"], body["inputs"])
                except RunsError as exc:
                    raise RunsError(
                        exc.code,
                        exc.http_status,
                        exc.detail,
                        view=_stamp_refusal(run, exc.public_error()),
                    )
            return _public_view(run)

    def _require(self, run_id):
        run = self._runs.get(run_id)
        if run is None:
            raise RunsError("run_not_found", 404)
        return run


def _admit(body):
    if not isinstance(body, dict) or set(body) != _SUBMIT_FIELDS:
        field = "body"
        if isinstance(body, dict):
            missing = _SUBMIT_FIELDS - set(body)
            extra = set(body) - _SUBMIT_FIELDS
            field = sorted(missing or extra)[0]
        raise RunsError("binding_refused", 422, {"field": field})
    release_id = body["release_id"]
    if (
        not isinstance(release_id, str)
        or RELEASE_ID_PATTERN.fullmatch(release_id) is None
    ):
        raise RunsError("binding_refused", 422, {"field": "release_id"})
    configuration = _admit_configuration(body["configuration"])
    inputs = body["inputs"]
    if not isinstance(inputs, list) or not inputs:
        raise RunsError("binding_refused", 422, {"field": "inputs"})
    copied_inputs = copy.deepcopy(inputs)
    _reject_nonfinite(copied_inputs, "inputs")
    for item in copied_inputs:
        if not isinstance(item, dict):
            raise RunsError("binding_refused", 422, {"field": "inputs"})
        supplied = item.get("model_id")
        if supplied is not None and supplied != configuration["model_id"]:
            raise RunsError("binding_refused", 422, {"field": "model_id"})
    return {
        "run_id": str(uuid.uuid4()),
        "release_id": release_id,
        "configuration": configuration,
        "inputs": copied_inputs,
        "inputs_digest": inputs_digest(copied_inputs),
        "status": "submitted",
        "error": None,
        "alignment": None,
        "computing_release_ids": [],
    }


def _admit_configuration(payload):
    if not isinstance(payload, dict):
        raise RunsError("binding_refused", 422, {"field": "configuration"})
    if set(payload) != _CONFIG_FIELDS:
        missing = _CONFIG_FIELDS - set(payload)
        extra = set(payload) - _CONFIG_FIELDS
        field = sorted(missing or extra)[0]
        raise RunsError("binding_refused", 422, {"field": field})
    cadence = payload["cadence"]
    loader = payload["loader"]
    model_id = payload["model_id"]
    if not isinstance(cadence, str) or cadence not in ACCEPTED_CADENCE:
        raise RunsError("binding_refused", 422, {"field": "cadence"})
    if not isinstance(loader, str) or loader not in ACCEPTED_LOADER:
        raise RunsError("binding_refused", 422, {"field": "loader"})
    if not isinstance(model_id, str) or MODEL_ID_PATTERN.fullmatch(model_id) is None:
        raise RunsError("binding_refused", 422, {"field": "model_id"})
    return {"cadence": cadence, "loader": loader, "model_id": model_id}


def _alignment(index, value):
    entry = {"output_index": index, "input_index": index}
    if value is not None:
        entry["value"] = value
    return entry


def _public_view(run):
    reveal = run["status"] == "succeeded"
    body = {
        "contract_version": CONTRACT_VERSION,
        "run_id": run["run_id"],
        "status": run["status"],
        "complete": reveal,
        "binding": {
            "release_id": run["release_id"],
            "configuration": copy.deepcopy(run["configuration"]),
            "inputs_digest": run["inputs_digest"],
            "output_alignment": copy.deepcopy(run["alignment"]) if reveal else None,
        },
    }
    if run["error"] and not reveal:
        body["error"] = copy.deepcopy(run["error"])
    return body


def _reject_nonfinite(value, field):
    if isinstance(value, float) and not math.isfinite(value):
        raise RunsError("binding_refused", 422, {"field": field})
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise RunsError("binding_refused", 422, {"field": field})
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite(key, field)
            _reject_nonfinite(item, field)
    elif isinstance(value, list):
        for item in value:
            _reject_nonfinite(item, field)


def _stamp_refusal(run, error):
    return {
        "contract_version": CONTRACT_VERSION,
        "run_id": run["run_id"],
        "status": run["status"],
        "complete": False,
        "error": copy.deepcopy(error),
        "binding": {
            "release_id": run["release_id"],
            "configuration": copy.deepcopy(run["configuration"]),
            "inputs_digest": run["inputs_digest"],
            "output_alignment": None,
        },
    }


def _stored_error(run):
    error = run["error"] or {"code": "score_rejected"}
    return RunsError(error["code"], _http_status(run), error, view=_public_view(run))


def _http_status(run):
    code = (run["error"] or {}).get("code")
    if code in {"reference_mismatch", "not_executed"}:
        return 409
    if (
        run["status"] == "refused"
        or code == "binding_refused"
        or code == "inputs_digest_mismatch"
    ):
        return 422
    if code == "request_denied":
        return 403
    if code == "rate_limited":
        return 429
    if code == "request_too_large":
        return 413
    return 502
