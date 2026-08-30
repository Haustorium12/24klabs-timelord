# Nonce ledger -- append-only delivery log for x402-paid requests.
#
# Work order: devs-skills comms/nox NONCE_LEDGER_1 (2026-08-20) + NONCE_LEDGER_2
# (2026-08-30, Sean greenlit issue #25). One durable row per request that carried
# a VERIFIED payment, written after the final response is known:
#
#   ts_utc . nonce . payer . endpoint . method . price_advertised . http_status
#   . bytes_out . ua . ip_hash . settle_tx
#
# The nonce is the EIP-3009 authorization nonce -- the same value the chain emits
# in AuthorizationUsed -- so any settlement can be joined back to the exact
# request that earned it. settle_tx is the settlement transaction hash decoded
# from the outgoing PAYMENT-RESPONSE header when settlement succeeded.
#
# Design rules (from the work order):
#   - OBSERVER ONLY. Sits outside the payment middleware; every failure in here
#     is swallowed. The money path never waits on, or breaks because of, this file.
#   - APPEND-ONLY flat file (JSONL) + one mirrored stdout log line per row, so
#     Railway's log retention holds a copy that survives ephemeral-filesystem
#     deploys.
#   - Never log the signature or the authorization payload -- only the nonce
#     (and the payer address, which is public on-chain the moment it settles).
#   - IPs are salted-hashed, never stored. Set NONCE_LEDGER_SALT in the service
#     env; without it a per-process salt keeps callers distinguishable but not
#     stable across restarts (a warning says so at startup).
#
# This file is deliberately identical in 24klabs-api and 24klabs-timelord.

import hashlib
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone

log = logging.getLogger("nonce-ledger")

_LEDGER_DIR = os.environ.get("NONCE_LEDGER_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data")
_SALT = os.environ.get("NONCE_LEDGER_SALT") or ""
if not _SALT:
    _SALT = "ephemeral-" + uuid.uuid4().hex
    log.warning("NONCE_LEDGER_SALT not set -- using per-process salt; "
                "ip_hash will not be stable across restarts")
_LOCK = threading.Lock()


def _ledger_path():
    return os.path.join(_LEDGER_DIR, "ledger.jsonl")


def ip_hash(ip):
    return hashlib.sha256((_SALT + "|" + (ip or "")).encode("utf-8")).hexdigest()[:24]


def _client_ip(headers, scope):
    ip = headers.get("cf-connecting-ip")
    if not ip:
        ip = (headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if not ip:
        client = scope.get("client") or ("", 0)
        ip = client[0]
    return ip


def _settle_tx(header_value):
    if not header_value:
        return None
    try:
        from x402.http.utils import decode_payment_response_header
        sr = decode_payment_response_header(header_value)
        return getattr(sr, "transaction", None) or None
    except Exception:
        return "undecoded"  # header was present; keep that fact even if the shape moved


class NonceLedgerASGI:
    """ASGI wrapper OUTSIDE PaymentMiddlewareASGI. The middleware stores the
    verified payload in request.state (scope["state"]); settlement happens
    inside it, so the status/bytes seen out here are what the payer actually
    received -- including the 402 it substitutes when settlement fails."""

    def __init__(self, app, price_fn=None):
        self.app = app
        self.price_fn = price_fn  # (path, raw_query_bytes) -> advertised USD price or None

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        # Guarantee request.state is backed by a dict we hold a reference to.
        scope.setdefault("state", {})
        meta = {"status": None, "bytes": 0, "settle_hdr": None}

        async def send_wrap(message):
            try:
                if message["type"] == "http.response.start":
                    meta["status"] = message.get("status")
                    for k, v in message.get("headers") or []:
                        if k.decode("latin-1").lower() in ("payment-response", "x-payment-response"):
                            meta["settle_hdr"] = v.decode("latin-1")
                elif message["type"] == "http.response.body":
                    meta["bytes"] += len(message.get("body") or b"")
            except Exception:
                log.exception("ledger response inspection failed")
            await send(message)

        try:
            await self.app(scope, receive, send_wrap)
        finally:
            try:
                self._record(scope, meta)
            except Exception:
                log.exception("nonce ledger write failed (request unaffected)")

    def _record(self, scope, meta):
        payload = (scope.get("state") or {}).get("payment_payload")
        if payload is None:
            return  # no verified payment on this request -> not our row
        nonce = payer = None
        try:
            scheme_payload = getattr(payload, "payload", None) or {}
            auth = scheme_payload.get("authorization") or {}
            nonce = auth.get("nonce") or None
            payer = auth.get("from") or None
        except Exception:
            log.exception("payment payload shape unexpected (row kept, nonce lost)")
        headers = {}
        try:
            headers = {k.decode("latin-1").lower(): v.decode("latin-1")
                       for k, v in scope.get("headers") or []}
        except Exception:
            pass
        price = None
        if self.price_fn is not None:
            try:
                price = self.price_fn(scope.get("path") or "", scope.get("query_string") or b"")
            except Exception:
                pass
        row = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "nonce": nonce,
            "payer": payer,
            "endpoint": scope.get("path"),
            "method": scope.get("method"),
            "price_advertised": price,
            "http_status": meta["status"],
            "bytes_out": meta["bytes"],
            "ua": headers.get("user-agent"),
            "ip_hash": ip_hash(_client_ip(headers, scope)),
            "settle_tx": _settle_tx(meta["settle_hdr"]),
        }
        line = json.dumps(row, separators=(",", ":"))
        log.info("NONCE-LEDGER %s", line)  # stdout mirror -- survives redeploys in platform logs
        with _LOCK:
            os.makedirs(_LEDGER_DIR, exist_ok=True)
            with open(_ledger_path(), "a", encoding="utf-8") as f:
                f.write(line + "\n")
