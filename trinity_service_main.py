from __future__ import annotations
import argparse
import logging
import os
import json
import signal
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from trinity_os.logging import configure_root_logger, ActionLogger, new_request_id, set_request_id, get_request_id
from trinity_os.tracing import configure_tracing, instrument_http_handler
from trinity_os.auth import authorize_bearer, RateLimiter, load_secret

# Muscle endpoints come from the installed package
from trinity_os.api_muscle import handle_POST as handle_muscle_post

# Events endpoints are local to this service folder
from trinity_comm_http import handle_events_GET, handle_events_POST

LOG = logging.getLogger("trinity.master")

class TrinityKernel:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self._load_config(config_file)
        self.ready = True
        self.api_server = None
        self._action_log = ActionLogger(logging.getLogger("trinity.action"))

    def _load_config(self, path: str):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    # ---- Ops verbs ----
    def handle_reload(self, actor: str, config_path: str | None = None):
        rid = new_request_id(); set_request_id(rid)
        finish = self._action_log.run(actor=actor, verb="system.reload", target="config", rid=rid)
        try:
            cfg_file = config_path or self.config_file
            with open(cfg_file, "r", encoding="utf-8") as fh:
                new_cfg = json.load(fh)
            # atomic replace in same directory
            tmp = f"{cfg_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(new_cfg, fh, indent=2)
            os.replace(tmp, cfg_file)
            self.config = new_cfg
            finish("ok", changed=list(new_cfg.keys()))
            return {"success": True, "message": "config reloaded", "rid": rid}
        except Exception as e:
            logging.getLogger("trinity.core").error("reload.fail", extra={"error": str(e), "rid": rid}, exc_info=True)
            finish("fail", error=str(e))
            return {"success": False, "error": str(e), "rid": rid}

    def handle_drain(self, actor: str, enable: bool):
        rid = new_request_id(); set_request_id(rid)
        finish = self._action_log.run(actor=actor, verb="system.drain", target="instance", rid=rid)
        try:
            # enable=True -> drain enabled -> not-ready
            self.ready = not enable
            if getattr(self, "api_server", None) is not None:
                setattr(self.api_server, "ready", self.ready)
            finish("ok", ready=self.ready)
            return {"success": True, "message": "drain enabled" if enable else "drain cleared", "ready": self.ready, "rid": rid}
        except Exception as e:
            logging.getLogger("trinity.core").error("drain.fail", extra={"error": str(e), "rid": rid}, exc_info=True)
            finish("fail", error=str(e))
            return {"success": False, "error": str(e), "rid": rid}

# ---- Auth bootstrap ----
JWT_SECRET = load_secret(default_file="secrets/jwt_secret.txt")
JWT_ISS = "trinity-os"
JWT_AUD = "trinity-cli"
RL = RateLimiter(capacity=20, refill_per_sec=10.0)

class APIHandler(BaseHTTPRequestHandler):
    server_version = "TrinitySecured/1.0"

    # ---- helpers ----
    def _json(self, obj, code=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except BrokenPipeError:
            LOG.debug("client disconnected while sending JSON reply")

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(n).decode("utf-8") if n > 0 else "{}"
            return json.loads(raw or "{}")
        except Exception:
            return {}

    # ---- GET ----
    def do_GET(self):
        with instrument_http_handler(self, method=self.command):
            # health
            if self.path == "/healthz":
                ok = bool(getattr(self.server, "kernel", None))
                self.send_response(HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"ok\n" if ok else b"unhealthy\n")
                return
            # readiness
            if self.path == "/readyz":
                ready = bool(getattr(self.server, "ready", True))
                self.send_response(HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"ready\n" if ready else b"not-ready\n")
                return
            # events
            if handle_events_GET(self): return
            # default
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    # ---- POST ----
    def do_POST(self):
        with instrument_http_handler(self, method=self.command):
            # mount muscle memory routes
            if self.path.startswith("/muscle/"):
                if handle_muscle_post(self): return

            # mount event routes
            if self.path.startswith("/events/"):
                if handle_events_POST(self): return

            # secured system ops
            scopes = self._scopes_for_path(self.path)
            if scopes is not None:
                ok, sub, claims = authorize_bearer(self.headers.get("Authorization"),
                                                   required_scopes=scopes,
                                                   limiter=RL, secret=JWT_SECRET, issuer=JWT_ISS, audience=JWT_AUD)
                if not ok:
                    LOG.warning("auth.denied: %s path=%s rid=%s", sub, self.path, get_request_id())
                    return self._json({"success": False, "error": sub}, code=HTTPStatus.FORBIDDEN)

                body = self._body()
                kernel = getattr(self.server, "kernel", None)
                if kernel is None:
                    return self._json({"success": False, "error": "kernel unavailable"}, code=HTTPStatus.SERVICE_UNAVAILABLE)

                if self.path == "/system/reload":
                    res = kernel.handle_reload(actor=sub, config_path=body.get("config_path"))
                    return self._json(res, code=(HTTPStatus.OK if res.get("success") else HTTPStatus.INTERNAL_SERVER_ERROR))
                if self.path == "/system/drain":
                    res = kernel.handle_drain(actor=sub, enable=True)
                    return self._json(res, code=(HTTPStatus.OK if res.get("success") else HTTPStatus.INTERNAL_SERVER_ERROR))
                if self.path == "/system/undrain":
                    res = kernel.handle_drain(actor=sub, enable=False)
                    return self._json(res, code=(HTTPStatus.OK if res.get("success") else HTTPStatus.INTERNAL_SERVER_ERROR))

            # unknown
            return self._json({"success": False, "error": "unknown endpoint"}, code=HTTPStatus.NOT_FOUND)

    def _scopes_for_path(self, path: str):
        if path == "/system/reload": return ["system:reload"]
        if path in ("/system/drain", "/system/undrain"): return ["system:drain"]
        return None

def main(argv=None):
    ap = argparse.ArgumentParser(description="Trinity Secured Service")
    ap.add_argument("--config", default="trinity_config.json")
    ap.add_argument("--log-level", default="INFO")
    ap.add_argument("--trace-enable", action="store_true")
    ap.add_argument("--trace-endpoint", default=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""))
    args = ap.parse_args(argv)

    level = getattr(logging, args.log_level.upper(), logging.INFO)
    configure_root_logger(level=level)
    tracing_on = configure_tracing(service_name="trinity-secured", enable=args.trace_enable, endpoint=args.trace_endpoint or None)
    LOG.info("tracing.%s", "enabled" if tracing_on else "disabled")

    kernel = TrinityKernel(args.config)
    host = kernel.config.get("api_host") or kernel.config.get("host", "127.0.0.1")
    port = int(kernel.config.get("api_port") or kernel.config.get("port", 8099))

    # Ensure we allow quick restarts to reuse address where possible
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), APIHandler)
    setattr(server, "kernel", kernel)
    setattr(server, "ready", True)
    kernel.api_server = server

    LOG.info("Trinity Secured Service on http://%s:%d", host, port)

    def _grace(sig, frame):
        LOG.info("signal.received %s", str(sig))
        try:
            server.shutdown()
            try:
                server.server_close()
            except Exception:
                LOG.exception("server_close raised during graceful shutdown")
        finally:
            # Note: allow main to exit normally after cleanup
            sys.exit(0)

    signal.signal(signal.SIGINT, _grace)
    signal.signal(signal.SIGTERM, _grace)
    server.serve_forever()

if __name__ == "__main__":
    raise SystemExit(main())