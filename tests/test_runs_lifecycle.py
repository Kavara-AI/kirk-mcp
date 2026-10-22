"""Run lifecycle against a mock public HTTP API and the recorded fixture."""

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import urllib.error
import urllib.request

from kirk_runs.binding import assert_same_inputs, inputs_digest, stamp_references
from kirk_runs.contract import MAX_BODY_BYTES, PUBLIC_API_ORIGIN
from kirk_runs.errors import RunsError
from kirk_runs.http_api import handler_for
from kirk_runs.scorer import ApiScorer
from kirk_runs.service import RunService

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "run_lifecycle.json").read_text(
        encoding="utf-8"
    )
)
API_KEY = "k_" + ("0" * 32)
_IDEMPOTENCY = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_BINDING_KEYS = {"release_id", "configuration", "inputs_digest", "output_alignment"}


def _recorded_digest():
    return inputs_digest(FIXTURE["inputs"])


def test_digest_matches_recorded_fixture():
    recorded = _recorded_digest()
    assert_same_inputs(recorded, FIXTURE["inputs"])
    with pytest.raises(RunsError) as reorder:
        assert_same_inputs(recorded, list(reversed(FIXTURE["inputs"])))
    assert reorder.value.code == "inputs_digest_mismatch"


def test_stamp_and_reordered_inputs_fail_distinctly():
    stamp_references(FIXTURE["release_id"], [FIXTURE["release_id"]])
    with pytest.raises(RunsError) as mismatch:
        stamp_references(FIXTURE["release_id"], ["rel-other"])
    with pytest.raises(RunsError) as reorder:
        assert_same_inputs(_recorded_digest(), list(reversed(FIXTURE["inputs"])))
    assert mismatch.value.code == "reference_mismatch"
    assert reorder.value.code == "inputs_digest_mismatch"
    assert mismatch.value.code != reorder.value.code
    assert mismatch.value.detail["probed_release_id"] == FIXTURE["release_id"]
    assert mismatch.value.detail["computing_release_id"] == "rel-other"


def test_default_scorer_origin_is_the_public_api():
    scorer = ApiScorer(API_KEY)
    assert scorer.base_url == PUBLIC_API_ORIGIN


def test_recorded_fixture_follows_lifecycle_and_reproduces_its_reference(case_factory):
    case = case_factory()
    submitted = case.request("POST", "/v1/runs", _submission())
    assert submitted.status == 201
    assert submitted.headers["X-Contract-Version"] == "v1"
    _assert_binding(submitted.body, complete=False, status="submitted")
    assert submitted.body["binding"]["output_alignment"] is None

    executed = case.request("POST", "/v1/runs/%s/execution" % submitted.body["run_id"])
    assert executed.status == 200
    _assert_succeeded(executed.body)

    retrieved = case.request("GET", "/v1/runs/%s" % submitted.body["run_id"])
    assert retrieved.status == 200
    assert retrieved.body == executed.body

    again = case.request("POST", "/v1/runs/%s/execution" % submitted.body["run_id"])
    assert again.body == executed.body
    score_calls = [
        call for call in case.upstream.calls if call["path"] == "/v1/score-book"
    ]
    assert len(score_calls) == len(FIXTURE["inputs"])
    assert [call["path"] for call in case.upstream.calls] == [
        "/v1/models",
        "/v1/score-book",
        "/v1/score-book",
    ]
    assert [call["body_without_model"] for call in score_calls] == FIXTURE["inputs"]
    assert len({call["idempotency_key"] for call in score_calls}) == len(score_calls)
    for call in score_calls:
        assert call["api_key"] == API_KEY
        assert _IDEMPOTENCY.fullmatch(call["idempotency_key"])
    catalog_calls = [
        call for call in case.upstream.calls if call["path"] == "/v1/models"
    ]
    assert catalog_calls[0]["idempotency_key"] is None


def test_wrong_reference_and_reordered_inputs_fail_distinctly(case_factory):
    good = case_factory()
    created = good.request("POST", "/v1/runs", _submission())
    assert (
        good.request("POST", "/v1/runs/%s/execution" % created.body["run_id"]).status
        == 200
    )
    reordered = good.request(
        "POST",
        "/v1/runs/%s/stamp" % created.body["run_id"],
        {"inputs": list(reversed(FIXTURE["inputs"]))},
    )
    assert reordered.status == 422
    assert reordered.body["error"]["code"] == "inputs_digest_mismatch"
    assert reordered.body["status"] == "succeeded"
    assert reordered.body["complete"] is False
    assert reordered.body["binding"]["output_alignment"] is None
    still = good.request("GET", "/v1/runs/%s" % created.body["run_id"])
    assert still.status == 200
    assert still.body["complete"] is True
    assert still.body["binding"]["inputs_digest"] == _recorded_digest()

    wrong = case_factory(computing_release_id="rel-other")
    wrong_run = wrong.request("POST", "/v1/runs", _submission())
    refused = wrong.request("POST", "/v1/runs/%s/execution" % wrong_run.body["run_id"])
    assert refused.status == 409
    assert refused.body["error"]["code"] == "reference_mismatch"
    assert refused.body["error"]["probed_release_id"] == FIXTURE["release_id"]
    assert refused.body["error"]["computing_release_id"] == "rel-other"
    assert refused.body["complete"] is False
    assert refused.body["status"] == "failed"
    assert refused.body["binding"]["output_alignment"] is None
    assert refused.body["binding"]["release_id"] == FIXTURE["release_id"]
    assert "out-1" not in json.dumps(refused.body)
    assert [call["path"] for call in wrong.upstream.calls] == [
        "/v1/models",
        "/v1/score-book",
    ]

    stamped = wrong.request(
        "POST",
        "/v1/runs/%s/stamp" % wrong_run.body["run_id"],
        {"inputs": list(reversed(FIXTURE["inputs"]))},
    )
    assert stamped.status == 409
    assert stamped.body["error"]["code"] == "reference_mismatch"
    assert stamped.body["error"]["code"] != reordered.body["error"]["code"]
    assert stamped.body["complete"] is False
    assert stamped.body["binding"]["output_alignment"] is None


def test_partial_score_does_not_look_complete(case_factory):
    case = case_factory(fail_at=1)
    created = case.request("POST", "/v1/runs", _submission())
    failed = case.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert failed.status == 502
    assert failed.body["status"] == "partial"
    assert failed.body["complete"] is False
    assert failed.body["binding"]["output_alignment"] is None
    assert "out-1" not in json.dumps(failed.body)
    retrieved = case.request("GET", "/v1/runs/%s" % created.body["run_id"])
    assert retrieved.status == 502
    assert retrieved.body["complete"] is False
    assert "out-1" not in json.dumps(retrieved.body)


def test_rejected_cadence_loader_and_model_do_not_score(case_factory):
    case = case_factory()
    cadence = _submission()
    cadence["configuration"] = dict(cadence["configuration"], cadence="batched")
    refused = case.request("POST", "/v1/runs", cadence)
    assert refused.status == 422
    assert refused.body["complete"] is False
    assert refused.body["error"] == {"code": "binding_refused", "field": "cadence"}

    loader = _submission()
    loader["configuration"] = dict(loader["configuration"], loader="remote")
    refused = case.request("POST", "/v1/runs", loader)
    assert refused.body["error"]["field"] == "loader"

    case.upstream.model_ids = ["model-other"]
    created = case.request("POST", "/v1/runs", _submission())
    assert created.status == 201
    executed = case.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert executed.status == 422
    assert executed.body["error"] == {"code": "binding_refused", "field": "model_id"}
    assert executed.body["complete"] is False
    assert executed.body["binding"]["configuration"] == FIXTURE["configuration"]
    assert executed.body["binding"]["output_alignment"] is None
    assert [call["path"] for call in case.upstream.calls] == ["/v1/models"]


def test_timeout_on_second_input_fails_the_run(case_factory):
    case = case_factory(hang_at=1, timeout=0.4)
    created = case.request("POST", "/v1/runs", _submission())
    failed = case.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert failed.status == 502
    assert failed.body["error"]["code"] == "origin_unavailable"
    assert failed.body["status"] == "partial"
    assert failed.body["complete"] is False
    assert failed.body["binding"]["output_alignment"] is None
    assert "out-1" not in json.dumps(failed.body)
    assert _score_calls(case) == len(FIXTURE["inputs"])


def test_nonfinite_input_is_refused_at_submit(case_factory):
    case = case_factory()
    for value in (float("nan"), float("inf"), float("-inf")):
        payload = _submission()
        payload["inputs"] = [{"marker": value}]
        refused = case.request("POST", "/v1/runs", payload)
        assert refused.status == 422
        assert refused.body["complete"] is False
        assert refused.body["error"] == {"code": "binding_refused", "field": "inputs"}
    assert case.upstream.calls == []


def test_stamp_after_failure_is_not_http_200(case_factory):
    case = case_factory(hang_at=1, timeout=0.4)
    created = case.request("POST", "/v1/runs", _submission())
    failed = case.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert failed.status == 502
    stamped = case.request("POST", "/v1/runs/%s/stamp" % created.body["run_id"], {})
    assert stamped.status == 502
    assert stamped.body["complete"] is False
    assert stamped.body["error"]["code"] == "origin_unavailable"
    assert stamped.body["status"] == "partial"
    assert stamped.body["binding"]["output_alignment"] is None


def test_reexecute_after_failure_does_not_append(case_factory):
    case = case_factory(hang_at=1, timeout=0.4)
    created = case.request("POST", "/v1/runs", _submission())
    failed = case.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert failed.status == 502
    scored = _score_calls(case)
    assert scored == len(FIXTURE["inputs"])
    again = case.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert again.status == 502
    assert again.body["status"] == "partial"
    assert again.body["complete"] is False
    assert again.body["binding"]["output_alignment"] is None
    assert _score_calls(case) == scored


def test_second_execute_of_completed_run_does_not_rescore(case_factory):
    case = case_factory()
    created = case.request("POST", "/v1/runs", _submission())
    first = case.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert first.status == 200
    scored = _score_calls(case)
    assert scored == len(FIXTURE["inputs"])
    second = case.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert second.status == 200
    assert second.body == first.body
    assert _score_calls(case) == scored


def test_oversized_body_returns_413(case_factory):
    case = case_factory()
    payload = _submission()
    payload["inputs"] = [{"marker": "x" * (MAX_BODY_BYTES + 1)}]
    refused = case.request("POST", "/v1/runs", payload)
    assert refused.status == 413
    assert refused.body["complete"] is False
    assert refused.body["error"]["code"] == "request_too_large"
    assert case.upstream.calls == []


def test_empty_inputs_return_422(case_factory):
    case = case_factory()
    payload = _submission()
    payload["inputs"] = []
    refused = case.request("POST", "/v1/runs", payload)
    assert refused.status == 422
    assert refused.body["complete"] is False
    assert refused.body["error"] == {"code": "binding_refused", "field": "inputs"}
    assert case.upstream.calls == []


def test_upstream_denial_and_rate_limit_are_distinct(case_factory):
    denied = case_factory(reject_status=401)
    created = denied.request("POST", "/v1/runs", _submission())
    response = denied.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert response.status == 403
    assert response.body["error"]["code"] == "request_denied"
    assert response.body["complete"] is False
    assert response.body["status"] == "failed"

    forbidden = case_factory(reject_status=403)
    created = forbidden.request("POST", "/v1/runs", _submission())
    response = forbidden.request(
        "POST", "/v1/runs/%s/execution" % created.body["run_id"]
    )
    assert response.status == 403
    assert response.body["error"]["code"] == "request_denied"

    limited = case_factory(reject_status=429)
    created = limited.request("POST", "/v1/runs", _submission())
    response = limited.request("POST", "/v1/runs/%s/execution" % created.body["run_id"])
    assert response.status == 429
    assert response.body["error"]["code"] == "rate_limited"
    assert response.body["complete"] is False
    assert response.body["status"] == "failed"


def test_unversioned_route_is_refused(case_factory):
    case = case_factory()
    response = case.request("POST", "/runs", _submission())
    assert response.status == 404
    assert response.body["error"]["code"] == "route_not_versioned"
    assert response.body["contract_version"] == "v1"
    assert response.headers["X-Contract-Version"] == "v1"
    assert case.upstream.calls == []


class _Response(object):
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body


class _Upstream(object):
    def __init__(self, computing_release_id, fail_at, hang_at, reject_status):
        self.computing_release_id = computing_release_id
        self.fail_at = fail_at
        self.hang_at = hang_at
        self.reject_status = reject_status
        self.model_ids = [FIXTURE["configuration"]["model_id"]]
        self.calls = []
        self._scores = 0


def _mock_handler(upstream):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def _handle(self, method):
            path = self.path.split("?", 1)[0]
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b""
            idempotency = self.headers.get("Idempotency-Key")
            body = json.loads(raw.decode("utf-8")) if raw else None
            without_model = None
            if isinstance(body, dict):
                without_model = {
                    key: value for key, value in body.items() if key != "model_id"
                }
            upstream.calls.append(
                {
                    "method": method,
                    "path": path,
                    "api_key": self.headers.get("X-Kavara-Key"),
                    "idempotency_key": idempotency,
                    "body_without_model": without_model,
                }
            )
            if self.headers.get("X-Kavara-Key") != API_KEY:
                self._send(401, {"error": "invalid_api_key"})
                return
            if path == "/v1/models" and method == "GET":
                if idempotency is not None:
                    self._send(400, {"error": "invalid_headers"})
                    return
                self._send(
                    200,
                    {
                        "result": {
                            "models": [
                                {"model_id": model_id}
                                for model_id in upstream.model_ids
                            ]
                        }
                    },
                )
                return
            if path == "/v1/score-book" and method == "POST":
                if idempotency is None or _IDEMPOTENCY.fullmatch(idempotency) is None:
                    self._send(400, {"error": "invalid_idempotency_key"})
                    return
                index = upstream._scores
                upstream._scores += 1
                if upstream.reject_status is not None and index == 0:
                    self._send(upstream.reject_status, {"error": "rejected"})
                    return
                if upstream.fail_at is not None and index == upstream.fail_at:
                    self._send(503, {"error": "origin_unavailable"})
                    return
                if upstream.hang_at is not None and index == upstream.hang_at:
                    self._stall()
                    return
                self._send(
                    200,
                    {
                        "result": {
                            "release_id": upstream.computing_release_id,
                            "output": FIXTURE["outputs"][index],
                        }
                    },
                )
                return
            self._send(404, {"error": "route_not_found"})

        def _stall(self):
            raw = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            time.sleep(1.5)
            try:
                self.wfile.write(raw)
            except Exception:
                return

        def _send(self, status, payload):
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    return Handler


def _serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class _Case(object):
    def __init__(self, upstream, app_url, servers):
        self.upstream = upstream
        self.app_url = app_url
        self._servers = servers

    def request(self, method, path, payload=None):
        return _request(self.app_url, method, path, payload)

    def close(self):
        for server, thread in self._servers:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def _build_case(computing_release_id, fail_at, hang_at, reject_status, timeout):
    upstream = _Upstream(computing_release_id, fail_at, hang_at, reject_status)
    mock_server, mock_thread = _serve(_mock_handler(upstream))
    host, port = mock_server.server_address
    scorer = ApiScorer(API_KEY, base_url="http://%s:%s" % (host, port), timeout=timeout)
    app_server, app_thread = _serve(handler_for(RunService(scorer)))
    app_host, app_port = app_server.server_address
    return _Case(
        upstream,
        "http://%s:%s" % (app_host, app_port),
        [(mock_server, mock_thread), (app_server, app_thread)],
    )


@pytest.fixture
def case_factory():
    cases = []

    def make(
        computing_release_id=None,
        fail_at=None,
        hang_at=None,
        reject_status=None,
        timeout=5,
    ):
        case = _build_case(
            computing_release_id or FIXTURE["release_id"],
            fail_at,
            hang_at,
            reject_status,
            timeout,
        )
        cases.append(case)
        return case

    yield make
    for case in cases:
        case.close()


def _request(base, method, path, payload):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(data))
    request = urllib.request.Request(
        base + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
            status = response.status
            headers = dict(response.headers)
    except urllib.error.HTTPError as error:
        raw = error.read()
        status = error.code
        headers = dict(error.headers)
    return _Response(status, headers, json.loads(raw.decode("utf-8")))


def _score_calls(case):
    return len(
        [call for call in case.upstream.calls if call["path"] == "/v1/score-book"]
    )


def _submission():
    return {
        "release_id": FIXTURE["release_id"],
        "configuration": dict(FIXTURE["configuration"]),
        "inputs": list(FIXTURE["inputs"]),
    }


def _assert_binding(body, complete, status):
    assert body["contract_version"] == "v1"
    assert body["complete"] is complete
    assert body["status"] == status
    assert set(body["binding"]) == _BINDING_KEYS
    assert body["binding"]["release_id"] == FIXTURE["release_id"]
    assert body["binding"]["configuration"] == FIXTURE["configuration"]
    assert body["binding"]["inputs_digest"] == _recorded_digest()


def _assert_succeeded(body):
    _assert_binding(body, complete=True, status="succeeded")
    alignment = body["binding"]["output_alignment"]
    assert len(alignment) == len(FIXTURE["inputs"])
    for index, entry in enumerate(alignment):
        assert entry == {
            "input_index": index,
            "output_index": index,
            "value": FIXTURE["outputs"][index],
        }
