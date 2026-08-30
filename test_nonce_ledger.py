"""Behaviour tests for the nonce ledger on the timelord surface.

First tests this repo has ever had. The paid-flow test runs the REAL /time
handler (pure local computation, no LLM) through the real payment middleware
with only the two facilitator seams mocked -- proving the wrapper records what
the payer received without touching what they received.
"""
import json
import types

import pytest
from starlette.testclient import TestClient

from x402.http.utils import encode_payment_response_header
from x402.http.x402_http_server import x402HTTPResourceServer
from x402.schemas import SettleResponse

NONCE = "0x" + "cd" * 32
PAYER = "0x17d5b4177a66eb11fe7fdce6c12b06bc2c6a34cc"
TX = "0x" + "5a" * 32


@pytest.fixture
def harness(monkeypatch, tmp_path):
    import ledger, main
    monkeypatch.setattr(ledger, "_LEDGER_DIR", str(tmp_path / "ledger"))
    monkeypatch.setattr(x402HTTPResourceServer, "initialize", lambda self: None)

    payload = types.SimpleNamespace(payload={
        "authorization": {"from": PAYER, "to": "0xus", "value": "1000", "nonce": NONCE},
        "signature": "0xsig"})
    verified = types.SimpleNamespace(
        type="payment-verified", payment_payload=payload, payment_requirements=None,
        cancellation_dispatcher=None, declared_extensions=None)

    async def fake_verify(self, context, paywall_config=None):
        return verified
    monkeypatch.setattr(x402HTTPResourceServer, "process_http_request", fake_verify)

    settle_header = encode_payment_response_header(SettleResponse(
        success=True, transaction=TX, network="eip155:8453", payer=PAYER))
    settled = types.SimpleNamespace(success=True,
                                    headers={"PAYMENT-RESPONSE": settle_header},
                                    response=None)

    async def fake_settle(self, *a, **kw):
        return settled
    monkeypatch.setattr(x402HTTPResourceServer, "process_settlement", fake_settle)

    ledger_file = tmp_path / "ledger" / "ledger.jsonl"
    return types.SimpleNamespace(
        client=TestClient(main.app), ledger_file=ledger_file,
        rows=lambda: [json.loads(l) for l in
                      ledger_file.read_text(encoding="utf-8").splitlines()])


def test_paid_time_call_writes_full_row(harness):
    r = harness.client.post("/time", json={"tz": "America/New_York"})
    assert r.status_code == 200
    assert "systems" in r.json() or "timezone" in r.json()   # real handler ran
    rows = harness.rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["nonce"] == NONCE
    assert row["endpoint"] == "/time"
    assert row["price_advertised"] == 0.001
    assert row["http_status"] == 200
    assert row["bytes_out"] == len(r.content)
    assert row["settle_tx"] == TX


def test_health_stays_free_and_unrowed(harness):
    r = harness.client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "operational"
    assert not harness.ledger_file.exists()


def test_price_fn_reads_the_routes_table():
    import main
    assert main._ledger_price("/time", b"") == 0.001
    assert main._ledger_price("/timezone", b"") == 0.001
    assert main._ledger_price("/summary", b"") == 0.05
    assert main._ledger_price("/ask", b"") == 0.05
    assert main._ledger_price("/health", b"") is None
