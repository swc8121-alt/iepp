"""Minimal HTTP adapter for the IEPP A3 single-registry experiment."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import parse_qs, urlparse

from a3_registry import A3RegistryEngine


MAX_BODY_BYTES = 64 * 1024


class A3HTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], engine: A3RegistryEngine):
        super().__init__(address, A3RequestHandler)
        self.engine = engine


class A3RequestHandler(BaseHTTPRequestHandler):
    server: A3HTTPServer

    def log_message(self, _format: str, *args) -> None:
        return

    def _write(self, status: int, value: dict) -> None:
        body = json.dumps(value, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self) -> dict:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("invalid-content-length") from error
        if size < 1 or size > MAX_BODY_BYTES:
            raise ValueError("body-size-out-of-range")
        value = json.loads(self.rfile.read(size))
        if not isinstance(value, dict):
            raise ValueError("object-required")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._write(200, self.server.engine.health())
            return
        if parsed.path == "/v1/head":
            sid = parse_qs(parsed.query).get("sid", [""])[0]
            status, value = self.server.engine.head(sid)
            self._write(status, value)
            return
        self._write(404, {"ok": False, "reason": "NOT_FOUND"})

    def do_POST(self) -> None:
        try:
            value = self._json_body()
        except (ValueError, json.JSONDecodeError) as error:
            self._write(400, {"ok": False, "reason": "MALFORMED_JSON", "detail": str(error)})
            return
        if self.path == "/v1/challenge":
            try:
                status, response = self.server.engine.issue_challenge(
                    str(value["sid"]), str(value["domain"]), int(value.get("ttl", 30))
                )
            except (KeyError, TypeError, ValueError) as error:
                self._write(400, {"ok": False, "reason": "MALFORMED_REQUEST", "detail": str(error)})
                return
            self._write(status, response)
            return
        if self.path == "/v1/transition":
            status, response = self.server.engine.verify_and_advance(value)
            self._write(status, response)
            return
        self._write(404, {"ok": False, "reason": "NOT_FOUND"})


def create_server(database: str, enrollment: str, bind: str = "127.0.0.1", port: int = 0,
                  event_log: str | None = None) -> A3HTTPServer:
    engine = A3RegistryEngine(database, enrollment, event_log)
    return A3HTTPServer((bind, port), engine)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--enrollment", required=True)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8043)
    parser.add_argument("--event-log")
    args = parser.parse_args()
    server = create_server(args.database, args.enrollment, args.bind, args.port, args.event_log)
    host, port = server.server_address
    print(json.dumps({"ready": True, "url": f"http://{host}:{port}",
                      "scope": "L1 single online registry"}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
