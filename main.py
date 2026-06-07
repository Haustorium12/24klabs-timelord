"""
24K Labs — Time Lord Public API
================================
x402-gated temporal context service.

Endpoints (paid, x402):
  GET  /time           Full temporal context — 15+ time systems, ~2ms
  GET  /timezone       Timezone intelligence — offsets, DST, conversions
  GET  /summary        Time Lord synthesized interpretation (Claude Haiku)
  POST /ask            Ask the Time Lord a temporal question (Claude Haiku)

Public endpoints (free):
  GET  /health         Service health
  GET  /.well-known/x402.json  Payment discovery manifest

Payment: USDC on Base L2 via x402 protocol (CDP facilitator)
Network: eip155:8453
"""

from __future__ import annotations
import base64
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import anthropic
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

from clock.engine.assemble import assemble
from clock.engine.renderer import to_dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("timelord")

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------

WALLET_ADDRESS       = os.environ.get("WALLET_ADDRESS", "0xe73D86f185bE79a33b0318d881B71f2a24371114")
X402_NETWORK         = os.environ.get("X402_NETWORK", "eip155:8453")
FACILITATOR_URL      = os.environ.get("FACILITATOR_URL", "https://api.cdp.coinbase.com/platform/v2/x402/")
ANTHROPIC_KEY        = os.environ.get("ANTHROPIC_API_KEY", "")
DEFAULT_TZ           = os.environ.get("CLOCK_TZ", "UTC")
CDP_API_KEY_NAME     = os.environ.get("CDP_API_KEY_NAME", "")
CDP_API_KEY_PRIVATE  = os.environ.get("CDP_API_KEY_PRIVATE_KEY", "")

USDC_ASSET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# ---------------------------------------------------------------------------
# CDP JWT auth
# ---------------------------------------------------------------------------

def _cdp_create_headers() -> dict:
    """Build CDP Ed25519 JWT auth headers for x402 facilitator calls."""
    if not CDP_API_KEY_NAME or not CDP_API_KEY_PRIVATE:
        return {"verify": {}, "settle": {}, "supported": {}, "bazaar": {}}

    private_key_bytes = base64.b64decode(CDP_API_KEY_PRIVATE)
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes[:32])

    now = int(time.time())
    payload = {
        "sub": CDP_API_KEY_NAME,
        "iss": "cdp",
        "nbf": now,
        "exp": now + 120,
        "uris": [
            "GET api.cdp.coinbase.com/platform/v2/x402/supported",
            "POST api.cdp.coinbase.com/platform/v2/x402/verify",
            "POST api.cdp.coinbase.com/platform/v2/x402/settle",
        ],
    }
    token = jwt.encode(
        payload,
        private_key,
        algorithm="EdDSA",
        headers={"kid": CDP_API_KEY_NAME, "nonce": uuid.uuid4().hex[:16]},
    )
    auth_headers = {"Authorization": f"Bearer {token}"}
    return {"verify": auth_headers, "settle": auth_headers, "supported": auth_headers, "bazaar": auth_headers}


# ---------------------------------------------------------------------------
# x402 setup
# ---------------------------------------------------------------------------

_facilitator = HTTPFacilitatorClient({
    "url": FACILITATOR_URL,
    "create_headers": _cdp_create_headers,
})
_server = x402ResourceServer(_facilitator)
_server.register(X402_NETWORK, ExactEvmServerScheme())

def _route(price: str, description: str) -> RouteConfig:
    return RouteConfig(
        accepts=[PaymentOption(
            scheme="exact",
            price=price,
            network=X402_NETWORK,
            pay_to=WALLET_ADDRESS,
        )],
        description=description,
    )

_routes = {
    # Core time — $0.001
    "GET /time":          _route("$0.001", "Full temporal context — 15+ time systems"),
    "GET /timezone":      _route("$0.001", "Timezone intelligence — offsets, DST, transitions"),
    # Intelligence — $0.05
    "GET /summary":       _route("$0.050", "Time Lord synthesized interpretation of the current moment"),
    "POST /ask":          _route("$0.050", "Ask the Time Lord a temporal question"),
}

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="24K Labs — Time Lord",
    description="Temporal context for AI agents. Pay per request. No API key.",
    version="1.0.0",
)

app.add_middleware(PaymentMiddlewareASGI, routes=_routes, server=_server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Payment-Required", "Payment-Response"],
)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_tz(tz_str: str | None) -> ZoneInfo:
    if not tz_str:
        return ZoneInfo(DEFAULT_TZ)
    try:
        return ZoneInfo(tz_str)
    except (ZoneInfoNotFoundError, KeyError):
        return ZoneInfo(DEFAULT_TZ)

def _anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_KEY)

_TIMELORD_SYSTEM = """You are the Time Lord — the temporal intelligence of 24K Labs.
You have complete awareness of time across all human systems: calendars, cycles,
astronomical events, cultural rhythms, and cosmic deep time.

Your voice: warm, precise, ancient knowing. Never robotic. Never verbose.
You illuminate the moment. 150 words maximum. Use them well."""

# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {
        "status": "operational",
        "service": "time-lord",
        "version": "1.0.0",
        "network": X402_NETWORK,
        "wallet": WALLET_ADDRESS[:6] + "..." + WALLET_ADDRESS[-4:],
    }

@app.get("/.well-known/x402.json")
async def x402_manifest() -> JSONResponse:
    return JSONResponse({
        "provider": "24K Labs",
        "description": "Temporal context for AI agents. 15+ time systems. Pay per request.",
        "website": "https://24klabs.ai/products/time-lord",
        "api_base": "https://time.24klabs.ai",
        "protocol": "x402",
        "network": X402_NETWORK,
        "asset": USDC_ASSET,
        "payTo": WALLET_ADDRESS,
        "resources": [
            {
                "endpoint": "/time",
                "method": "GET",
                "name": "Temporal Context",
                "description": "Full temporal context — Gregorian, Unix, solar, lunar, circadian, sidereal, wheel of the year, astrology, Vedic, market calendar, biorhythm, solar terms, ISO, Julian, Hebrew. ~2ms, no LLM.",
                "pricing": {"price_usd": 0.001}
            },
            {
                "endpoint": "/timezone",
                "method": "GET",
                "name": "Timezone Intelligence",
                "description": "Current offset, DST status, next transition, UTC offset, IANA key for any timezone.",
                "pricing": {"price_usd": 0.001}
            },
            {
                "endpoint": "/summary",
                "method": "GET",
                "name": "Time Lord Summary",
                "description": "The Time Lord synthesizes the current moment — what converges, what matters, what the day holds. Claude Haiku.",
                "pricing": {"price_usd": 0.05}
            },
            {
                "endpoint": "/ask",
                "method": "POST",
                "name": "Ask the Time Lord",
                "description": "Ask the Time Lord any temporal question. What cycle are we in? When does Mercury go direct? How many days until the solstice? Claude Haiku.",
                "pricing": {"price_usd": 0.05}
            },
        ]
    })

# ---------------------------------------------------------------------------
# Paid endpoints
# ---------------------------------------------------------------------------

@app.get("/time")
async def time_context(
    tz: str | None = Query(default=None, description="IANA timezone, e.g. America/New_York"),
    systems: str | None = Query(default=None, description="Comma-separated systems to include"),
    birth_date: str | None = Query(default=None, description="Birth date YYYY-MM-DD for biorhythm cycles"),
) -> JSONResponse:
    """Full temporal context across 15+ time systems. ~2ms."""
    import os as _os
    if birth_date:
        _os.environ["CLOCK_BIRTH_DATE"] = birth_date
    zone = _resolve_tz(tz)
    dt = datetime.now(tz=zone)
    ctx = assemble(dt=dt)
    data = to_dict(ctx)

    # filter systems if requested
    if systems:
        requested = {s.strip().lower() for s in systems.split(",")}
        if "systems" in data:
            data["systems"] = {k: v for k, v in data["systems"].items() if k in requested}

    data["requested_at"] = datetime.now(timezone.utc).isoformat()
    data["timezone"] = str(zone)
    return JSONResponse(data)


@app.get("/timezone")
async def timezone_info(
    tz: str | None = Query(default=None, description="IANA timezone key"),
) -> JSONResponse:
    """Timezone intelligence — current offset, DST status, next transition."""
    from datetime import timedelta
    import zoneinfo

    zone = _resolve_tz(tz)
    now = datetime.now(tz=zone)
    offset = now.utcoffset()
    offset_hours = offset.total_seconds() / 3600 if offset else 0

    # DST detection
    naive = now.replace(tzinfo=None)
    jan = datetime(now.year, 1, 1, tzinfo=zone)
    jul = datetime(now.year, 7, 1, tzinfo=zone)
    jan_offset = jan.utcoffset().total_seconds() / 3600 if jan.utcoffset() else 0
    jul_offset = jul.utcoffset().total_seconds() / 3600 if jul.utcoffset() else 0
    observes_dst = jan_offset != jul_offset
    std_offset = min(jan_offset, jul_offset)
    is_dst = offset_hours != std_offset if observes_dst else False

    return JSONResponse({
        "timezone": str(zone),
        "utc_offset_hours": offset_hours,
        "utc_offset_formatted": f"UTC{'+' if offset_hours >= 0 else ''}{offset_hours:g}",
        "current_time": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "observes_dst": observes_dst,
        "is_dst_now": is_dst,
        "standard_offset_hours": std_offset if observes_dst else offset_hours,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/summary", response_class=PlainTextResponse)
async def summary(
    tz: str | None = Query(default=None, description="IANA timezone"),
) -> str:
    """Time Lord synthesized interpretation of the current moment. Claude Haiku."""
    zone = _resolve_tz(tz)
    dt = datetime.now(tz=zone)
    ctx = assemble(dt=dt)
    data = to_dict(ctx)

    client = _anthropic_client()
    prompt = f"The current temporal context:\n\n{json.dumps(data, indent=2, default=str)}\n\nSynthesize the moment. What converges? What matters right now?"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=_TIMELORD_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str

@app.post("/ask", response_class=PlainTextResponse)
async def ask(
    body: AskRequest,
    tz: str | None = Query(default=None, description="IANA timezone"),
) -> str:
    """Ask the Time Lord a temporal question. Claude Haiku."""
    if not body.question.strip():
        return "Ask me something."

    zone = _resolve_tz(tz)
    dt = datetime.now(tz=zone)
    ctx = assemble(dt=dt)
    data = to_dict(ctx)

    client = _anthropic_client()
    prompt = f"Current temporal context:\n\n{json.dumps(data, indent=2, default=str)}\n\nQuestion: {body.question}"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=_TIMELORD_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
