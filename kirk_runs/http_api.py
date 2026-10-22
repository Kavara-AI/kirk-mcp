"""HTTP adapter for the v1 run routes."""

import json
import re
from http.server import BaseHTTPRequestHandler

from kirk_runs.contract import CONTRACT_VERSION, MAX_BODY_BYTES
from kirk_runs.errors import RunsError

_RUN_ID = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
_RUN_PATH = re.compile(r"^/v1/runs/(" + _RUN_ID + r")(?:/(execution|stamp))?$")


def handler_for(service):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def __init__(self, *args, **kwargs):
            self.service = service
            BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def _dispatch(self, method):
            try:
                self._route(method)
            except RunsError as exc:
                payload = exc.view if exc.view is not None else _bare_error(exc)
                self._send(exc.http_status, payload)
            except Exception:
                self._send(
                    500,
                    _bare_error(RunsError("origin_unavailable", 500)),
                )

        def _route(self, method):
            path, _, query = self.path.partition("?")
            if query or not path.startswith("/v1/"):
                raise RunsError("route_not_versioned", 404)
            if method == "POST" and path == "/v1/runs":
                self._send(201, self.service.submit(self._json_body(required=True)))
                return
            match = _RUN_PATH.fullmatch(path)
            if match is None:
                raise RunsError("route_not_versioned", 404)
            run_id, action = match.group(1), match.group(2)
            if action is None and method == "GET":
                self._send(200, self.service.retrieve(run_id))
                return
            if action == "execution" and method == "POST":
                self._send(200, self.service.execute(run_id))
                return
            if action == "stamp" and method == "POST":
                body = self._json_body(required=False)
                self._send(200, self.service.stamp(run_id, body))
                return
            raise RunsError("method_not_allowed", 405)

        def _json_body(self, required):
            raw = self._read_body()
            if not raw:
                if required:
                    raise RunsError("invalid_json", 400)
                return {}
            try:
                body = json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                raise RunsError("invalid_json", 400)
            if not isinstance(body, dict):
                raise RunsError("invalid_request", 400)
            return body

        def _read_body(self):
            header = self.headers.get("Content-Length")
            if header is None:
                return b""
            try:
                length = int(header)
            except ValueError:
                raise RunsError("invalid_json", 400)
            if length < 0 or length > MAX_BODY_BYTES:
                self._drain(length)
                raise RunsError("request_too_large", 413)
            return self.rfile.read(length)

        def _drain(self, length):
            remaining = min(length, MAX_BODY_BYTES + 65536)
            while remaining > 0:
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)

        def _send(self, status, payload):
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Contract-Version", CONTRACT_VERSION)
            self.end_headers()
            self.wfile.write(raw)

    return Handler


def _bare_error(exc):
    return {
        "complete": False,
        "contract_version": CONTRACT_VERSION,
        "error": exc.public_error(),
    }
