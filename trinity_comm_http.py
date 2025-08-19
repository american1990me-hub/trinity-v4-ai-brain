from __future__ import annotations
import json
import logging
import time
from http import HTTPStatus
from urllib.parse import urlsplit

from trinity_os.auth import authorize_bearer, RateLimiter, load_secret
from trinity_os.tracing import instrument_http_handler

from trinity_comm_lib import Broker

LOG = logging.getLogger("trinity.comm.http")

JWT_SECRET = load_secret(default_file="secrets/jwt_secret.txt")
JWT_ISS = "trinity-os"
JWT_AUD = "trinity-cli"
RL_PROD = RateLimiter(capacity=50, refill_per_sec=20.0)
RL_CONS = RateLimiter(capacity=200, refill_per_sec=50.0)

# Broker singleton
try:
    BROKER = Broker()
except Exception as e:
    # Keep a placeholder broker-like object that will raise on use, but do not crash import.
    LOG.exception("Broker initialization failed; handlers will return 503: %s", e)
    class _DeadBroker:
        def publish(self, *args, **kwargs):
            raise RuntimeError("broker unavailable")
        def ack(self, *args, **kwargs):
            raise RuntimeError("broker unavailable")
        def subscribe(self, *args, **kwargs):
            raise RuntimeError("broker unavailable")
    BROKER = _DeadBroker()

def _json(handler, obj, code=200):
    try:
        data = json.dumps(obj).encode("utf-8")
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)
    except BrokenPipeError:
        LOG.debug("client disconnected before JSON response could be sent")
    except Exception:
        LOG.exception("failed to write JSON response")

def _read_body(handler):
    """Robust Content-Length read. Returns dict (possibly empty)."""
    try:
        length = int(handler.headers.get("Content-Length", "0") or 0)
    except Exception:
        length = 0
    if length <= 0:
        return {}
    try:
        raw = handler.rfile.read(length)
        if not raw:
            return {}
        text = raw.decode("utf-8", errors="replace")
        return json.loads(text or "{}")
    except Exception:
        LOG.exception("failed to parse request body")
        return {}

def _norm_path(path: str) -> str:
    # strip query string and fragment
    return urlsplit(path).path

def handle_events_POST(handler) -> bool:
    if not handler.path.startswith("/events/"):
        return False
    with instrument_http_handler(handler, method=handler.command):
        path = _norm_path(handler.path)
        if path == "/events/produce":
            scopes = ["events:produce"]; limiter = RL_PROD
        elif path == "/events/ack":
            scopes = ["events:consume"]; limiter = RL_CONS
        else:
            _json(handler, {"success": False, "error": "unknown endpoint"}, HTTPStatus.NOT_FOUND)
            return True

        ok, sub, _ = authorize_bearer(handler.headers.get("Authorization"),
                                      required_scopes=scopes,
                                      limiter=limiter, secret=JWT_SECRET, issuer=JWT_ISS, audience=JWT_AUD)
        if not ok:
            LOG.warning("auth denied for POST %s: %s", path, sub)
            _json(handler, {"success": False, "error": sub}, HTTPStatus.FORBIDDEN)
            return True

        body = _read_body(handler)

        if path == "/events/produce":
            topic = body.get("topic", "")
            payload = body.get("payload")
            key = body.get("key", "")
            idk = body.get("idempotency_key")
            if not topic:
                _json(handler, {"success": False, "error": "topic required"}, HTTPStatus.BAD_REQUEST)
                return True
            try:
                msg = BROKER.publish(topic, payload, key=key, headers={"sub": sub}, idempotency_key=idk)
            except Exception as e:
                LOG.exception("broker.publish failed for topic=%s", topic)
                _json(handler, {"success": False, "error": "broker error", "detail": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return True
            _json(handler, {"success": True, "id": getattr(msg, "id", None), "ts": getattr(msg, "ts", None)})
            return True

        if path == "/events/ack":
            topic = body.get("topic", "")
            group = body.get("group", "")
            mid = body.get("id", "")
            if not (topic and group and mid):
                _json(handler, {"success": False, "error": "topic/group/id required"}, HTTPStatus.BAD_REQUEST)
                return True
            try:
                ok2 = BROKER.ack(topic, group, mid)
            except Exception:
                LOG.exception("broker.ack error for topic=%s group=%s id=%s", topic, group, mid)
                _json(handler, {"success": False, "error": "broker error"}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return True
            _json(handler, {"success": bool(ok2)})
            return True

        _json(handler, {"success": False, "error": "not handled"}, HTTPStatus.NOT_FOUND)
        return True

def handle_events_GET(handler) -> bool:
    if not handler.path.startswith("/events/"):
        return False
    with instrument_http_handler(handler, method=handler.command):
        path = _norm_path(handler.path)
        if path not in ("/events/consume", "/events/poll"):
            handler.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return True

        ok, sub, _ = authorize_bearer(handler.headers.get("Authorization"),
                                      required_scopes=["events:consume"],
                                      limiter=RL_CONS, secret=JWT_SECRET, issuer=JWT_ISS, audience=JWT_AUD)
        if not ok:
            LOG.warning("auth denied for GET %s: %s", path, sub)
            _json(handler, {"success": False, "error": sub}, HTTPStatus.FORBIDDEN)
            return True

        topic = handler.headers.get("X-Topic", "")
        group = handler.headers.get("X-Group", sub)
        try:
            timeout = float(handler.headers.get("X-Timeout", "25") or 25.0)
        except Exception:
            timeout = 25.0
        if not topic:
            _json(handler, {"success": False, "error": "X-Topic required"}, HTTPStatus.BAD_REQUEST)
            return True

        try:
            subc = BROKER.subscribe(topic, group)
        except Exception as e:
            LOG.exception("broker.subscribe failed for topic=%s group=%s", topic, group)
            _json(handler, {"success": False, "error": "broker unavailable", "detail": str(e)}, HTTPStatus.SERVICE_UNAVAILABLE)
            return True

        # /events/poll: single-shot JSON poll
        if path == "/events/poll":
            try:
                msg = subc.poll(timeout=timeout)
            except Exception:
                LOG.exception("subscription.poll failed")
                msg = None
            finally:
                # best-effort cleanup
                if hasattr(subc, "close"):
                    try: subc.close()
                    except Exception: LOG.debug("subscription.close raised")
            if msg is None:
                _json(handler, {"success": True, "message": None})
                return True
            out = {"success": True, "message": {"id": msg.id, "topic": msg.topic, "ts": msg.ts,
                                                "headers": msg.headers, "payload": msg.payload}}
            _json(handler, out)
            return True

        # /events/consume: SSE long-poll stream
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "keep-alive")
        handler.end_headers()
        start = time.time()
        try:
            while time.time() - start < timeout:
                try:
                    msg = subc.poll(timeout=1.0)
                except Exception:
                    LOG.exception("subscription.poll raised")
                    break
                if msg is None:
                    # send a small comment ping to keep connection alive? skip for now
                    continue
                try:
                    blob = json.dumps({"id": msg.id, "topic": msg.topic, "ts": msg.ts,
                                       "headers": msg.headers, "payload": msg.payload})
                    # write event header and payload as bytes
                    handler.wfile.write(b"event: message\n")
                    handler.wfile.write(f"data: {blob}\n\n".encode("utf-8"))
                    try:
                        handler.wfile.flush()
                    except Exception:
                        # some handlers may not support flush; ignore
                        pass
                except (BrokenPipeError, ConnectionResetError):
                    LOG.info("client disconnected while streaming SSE for topic=%s group=%s", topic, group)
                    break
                except Exception:
                    LOG.exception("failed to write SSE message")
                    break
        finally:
            # best-effort cleanup of subscription
            try:
                if hasattr(subc, "close"):
                    subc.close()
                elif hasattr(subc, "unsubscribe"):
                    subc.unsubscribe()
            except Exception:
                LOG.debug("failed to cleanup subscription object")
        return True